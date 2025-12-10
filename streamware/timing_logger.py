"""
Timing Logger for Streamware

Logs chronological events with timing information for performance analysis.
Outputs to both Markdown and CSV for easy analysis.

Usage:
    from streamware.timing_logger import TimingLogger, get_logger

    logger = get_logger("logs.md")  # Also creates logs.csv
    logger.start("frame_capture")
    # ... do work ...
    logger.end("frame_capture")
    
    # Or use context manager
    with logger.timed("llm_call"):
        result = call_llm(...)
"""

import csv
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional


@dataclass
class TimingEvent:
    """Single timing event."""
    name: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    details: str = ""
    timestamp: str = ""  # ISO timestamp
    
    def complete(self, end_time: float = None):
        self.end_time = end_time or time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.timestamp = datetime.now().isoformat(timespec='milliseconds')


@dataclass
class FrameLog:
    """Log for a single frame analysis."""
    frame_num: int
    timestamp: datetime
    events: List[TimingEvent] = field(default_factory=list)
    total_ms: float = 0
    result: str = ""
    
    def add_event(self, event: TimingEvent):
        self.events.append(event)
        if event.duration_ms:
            self.total_ms += event.duration_ms


def run_benchmark() -> dict:
    """Run quick performance benchmark to estimate system capabilities.
    
    Returns:
        dict with benchmark results and recommended settings
    """
    import time
    import platform
    import os
    
    results = {
        "system": platform.system(),
        "cpu_count": os.cpu_count(),
        "recommendations": {},
    }
    
    # Test 1: CPU speed (simple loop)
    start = time.perf_counter()
    total = 0
    for i in range(1000000):
        total += i
    cpu_time = time.perf_counter() - start
    results["cpu_benchmark_ms"] = cpu_time * 1000
    
    # Test 2: OpenCV availability and speed
    try:
        import cv2
        import numpy as np
        
        # Create test image
        img = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        start = time.perf_counter()
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        _ = cv2.Canny(blur, 50, 150)
        cv_time = time.perf_counter() - start
        
        results["opencv_available"] = True
        results["opencv_benchmark_ms"] = cv_time * 1000
    except ImportError:
        results["opencv_available"] = False
        results["opencv_benchmark_ms"] = None
    
    # Recommendations based on benchmarks
    if cpu_time < 0.05:  # Fast CPU
        results["recommendations"]["interval"] = 3
        results["recommendations"]["use_hog"] = True
        results["recommendations"]["vision_model"] = "llava:7b"
    elif cpu_time < 0.1:  # Medium CPU
        results["recommendations"]["interval"] = 5
        results["recommendations"]["use_hog"] = True
        results["recommendations"]["vision_model"] = "moondream"
    else:  # Slow CPU
        results["recommendations"]["interval"] = 8
        results["recommendations"]["use_hog"] = False
        results["recommendations"]["vision_model"] = "moondream"
    
    return results


class TimingLogger:
    """Logger that tracks timing of operations."""
    
    _instance: Optional["TimingLogger"] = None
    _lock = Lock()
    
    def __init__(self, log_file: Optional[str] = None, verbose: bool = False):
        self.log_file = Path(log_file) if log_file else None
        self.verbose = verbose
        self.csv_file = None
        self.decisions_file = None  # New: detailed decisions log
        
        # Live statistics
        self._stats: Dict[str, List[float]] = {}
        self._total_frames = 0
        self._skipped_frames = 0
        self._last_stats_time = time.time()
        self._stats_interval = 10.0  # Show stats every 10 seconds in verbose mode
        
        # Decision tracking
        self._decisions: List[dict] = []
        
        if self.log_file:
            # Create CSV and TXT files based on log_file
            log_path = Path(self.log_file)
            if log_path.suffix.lower() == '.csv':
                self.csv_file = log_path
                self.log_file = log_path.with_suffix('.txt')
            else:
                self.csv_file = log_path.with_suffix('.csv')
                # Keep log_file as-is for TXT
        # Note: We no longer auto-create log files. If you want logging,
        # use --log-file or set_log_file() explicitly.
        
        self.frames: List[FrameLog] = []
        self.current_frame: Optional[FrameLog] = None
        self.active_events: Dict[str, TimingEvent] = {}
        self.enabled = log_file is not None or self.verbose  # Enable if log_file OR verbose
        self._file_lock = Lock()
        self._csv_writer = None
        self._csv_handle = None
        
        if self.log_file:
            self._init_file()
            self._init_csv()
    
    def _init_file(self):
        """Initialize log file with header."""
        if not self.log_file:
            return
        with self._file_lock:
            with open(self.log_file, "w") as f:
                f.write("# Streamware Timing Log\n\n")
                f.write(f"Started: {datetime.now().isoformat()}\n\n")
                f.write("---\n\n")
    
    def _init_csv(self):
        """Initialize CSV file with header."""
        self._csv_handle = open(self.csv_file, "w", newline='')
        self._csv_writer = csv.writer(self._csv_handle)
        self._csv_writer.writerow([
            "timestamp", "frame", "step", "duration_ms", "details", "result"
        ])
        self._csv_handle.flush()
    
    def start_frame(self, frame_num: int):
        """Start logging a new frame."""
        if not self.enabled:
            return
        
        self.current_frame = FrameLog(
            frame_num=frame_num,
            timestamp=datetime.now()
        )
    
    def end_frame(self, result: str = ""):
        """End current frame logging."""
        if not self.enabled or not self.current_frame:
            return
        
        self.current_frame.result = result
        self.frames.append(self.current_frame)
        self._write_frame(self.current_frame)
        self.current_frame = None
    
    def start(self, name: str, details: str = ""):
        """Start timing an operation."""
        if not self.enabled:
            return
        
        event = TimingEvent(
            name=name,
            start_time=time.time(),
            details=details
        )
        self.active_events[name] = event
    
    def end(self, name: str, details: str = ""):
        """End timing an operation."""
        if not self.enabled:
            return
        
        if name in self.active_events:
            event = self.active_events.pop(name)
            event.complete()
            if details:
                event.details = details
            
            # Print to console in verbose mode
            if self.verbose:
                frame_num = self.current_frame.frame_num if self.current_frame else 0
                ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                
                # Color code based on duration
                duration = event.duration_ms
                if duration > 5000:
                    indicator = "🔴"  # Slow
                elif duration > 2000:
                    indicator = "🟡"  # Medium
                elif duration > 500:
                    indicator = "🟢"  # Fast
                else:
                    indicator = "⚡"  # Very fast
                
                print(f"  {indicator} [{ts}] F{frame_num} {name}: {duration:.0f}ms {details}", flush=True)
            
            # Track statistics
            if name not in self._stats:
                self._stats[name] = []
            self._stats[name].append(event.duration_ms)
            # Keep only last 50 samples
            if len(self._stats[name]) > 50:
                self._stats[name] = self._stats[name][-50:]
            
            # Show periodic stats in verbose mode
            if self.verbose and time.time() - self._last_stats_time > self._stats_interval:
                self._show_live_stats()
                self._last_stats_time = time.time()
            
            if self.current_frame:
                self.current_frame.add_event(event)
            else:
                # Standalone event
                self._write_event(event)
    
    def get_log_paths(self) -> dict:
        """Get paths to log files."""
        return {
            "csv": str(self.csv_file) if self.csv_file else None,
            "txt": str(self.log_file) if self.log_file else None,
        }
    
    def print_log_summary(self):
        """Print summary of log locations."""
        if self.csv_file and self.csv_file.exists():
            size_kb = self.csv_file.stat().st_size / 1024
            print(f"\n📊 Logs saved:", flush=True)
            print(f"   CSV: {self.csv_file} ({size_kb:.1f} KB)", flush=True)
            if self.log_file and self.log_file.exists():
                txt_size = self.log_file.stat().st_size / 1024
                print(f"   TXT: {self.log_file} ({txt_size:.1f} KB)", flush=True)
            print(f"   Frames: {self._total_frames}, Decisions: {len(self._decisions)}", flush=True)
    
    def _show_live_stats(self):
        """Show live performance statistics."""
        if not self._stats:
            return
        
        print("\n" + "─" * 60, flush=True)
        print("📊 LIVE STATS (last 50 samples)", flush=True)
        print("─" * 60, flush=True)
        
        total_avg = 0
        for name in ["capture", "smart_detect", "vision_llm", "guarder_llm"]:
            if name in self._stats and self._stats[name]:
                times = self._stats[name]
                avg = sum(times) / len(times)
                min_t = min(times)
                max_t = max(times)
                total_avg += avg
                
                # Bar visualization
                bar_len = min(20, int(avg / 500))
                bar = "█" * bar_len + "░" * (20 - bar_len)
                
                print(f"  {name:15} │ {bar} │ avg:{avg:5.0f}ms min:{min_t:4.0f}ms max:{max_t:5.0f}ms", flush=True)
        
        # Calculate throughput
        if self._total_frames > 0:
            skip_rate = self._skipped_frames / self._total_frames * 100
            fps = 1000 / total_avg if total_avg > 0 else 0
            print(f"\n  Frames: {self._total_frames} total, {self._skipped_frames} skipped ({skip_rate:.0f}%)", flush=True)
            print(f"  Throughput: {fps:.2f} FPS (theoretical max)", flush=True)
            print(f"  Avg cycle: {total_avg:.0f}ms", flush=True)
        
        print("─" * 60 + "\n", flush=True)
    
    def increment_frame_count(self, skipped: bool = False):
        """Increment frame counter."""
        self._total_frames += 1
        if skipped:
            self._skipped_frames += 1
    
    def log_decision(self, frame_num: int, decision_type: str, result: str, 
                     details: str = "", data: dict = None):
        """Log a processing decision for transparency.
        
        Args:
            frame_num: Frame number
            decision_type: Type of decision (detection, filter, tts, llm, etc.)
            result: Result (accepted, rejected, filtered, skipped, etc.)
            details: Human-readable details
            data: Additional structured data
        """
        decision = {
            "timestamp": datetime.now().isoformat(),
            "frame": frame_num,
            "type": decision_type,
            "result": result,
            "details": details,
            "data": data or {}
        }
        self._decisions.append(decision)
        
        # Write to CSV immediately
        if self.csv_file:
            with self._file_lock:
                try:
                    # Append to decisions section of CSV
                    with open(self.csv_file, "a") as f:
                        # Format: timestamp,frame,type,result,details,data
                        data_str = str(data) if data else ""
                        f.write(f"{decision['timestamp']},{frame_num},DECISION:{decision_type},{result},{details[:50]},{data_str[:100]}\n")
                except Exception:
                    pass
        
        # Print in verbose mode
        if self.verbose:
            indicator = "✅" if result in ("accepted", "processed", "spoken") else "❌" if result in ("rejected", "filtered") else "⚪"
            print(f"  {indicator} [{decision_type}] {result}: {details[:60]}", flush=True)
    
    @contextmanager
    def timed(self, name: str, details: str = ""):
        """Context manager for timing."""
        self.start(name, details)
        try:
            yield
        finally:
            self.end(name)
    
    def log(self, message: str):
        """Log a simple message."""
        if not self.enabled or not self.log_file:
            return
        
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        with self._file_lock:
            with open(self.log_file, "a") as f:
                f.write(f"[{ts}] {message}\n")
    
    def _write_frame(self, frame: FrameLog):
        """Write frame log to file."""
        if not self.log_file:
            return  # No log file configured, skip writing
        
        with self._file_lock:
            # Write to Markdown
            with open(self.log_file, "a") as f:
                f.write(f"## Frame {frame.frame_num}\n\n")
                f.write(f"**Time:** {frame.timestamp.strftime('%H:%M:%S.%f')[:-3]}\n")
                f.write(f"**Total:** {frame.total_ms:.0f}ms\n\n")
                
                if frame.events:
                    f.write("| Timestamp | Step | Duration | Details |\n")
                    f.write("|-----------|------|----------|----------|\n")
                    for event in frame.events:
                        ts = event.timestamp if event.timestamp else "-"
                        duration = f"{event.duration_ms:.0f}ms" if event.duration_ms else "-"
                        details = event.details[:50] if event.details else "-"
                        f.write(f"| {ts} | {event.name} | {duration} | {details} |\n")
                    f.write("\n")
                
                if frame.result:
                    f.write(f"**Result:** {frame.result}\n\n")
                
                f.write("---\n\n")
            
            # Write to CSV
            if self._csv_writer:
                for event in frame.events:
                    self._csv_writer.writerow([
                        event.timestamp or frame.timestamp.isoformat(),
                        frame.frame_num,
                        event.name,
                        f"{event.duration_ms:.1f}" if event.duration_ms else "",
                        event.details,
                        frame.result if event == frame.events[-1] else ""
                    ])
                self._csv_handle.flush()
    
    def _write_event(self, event: TimingEvent):
        """Write standalone event to file."""
        if not self.log_file:
            return
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        with self._file_lock:
            with open(self.log_file, "a") as f:
                duration = f"{event.duration_ms:.0f}ms" if event.duration_ms else "-"
                f.write(f"[{ts}] **{event.name}**: {duration}")
                if event.details:
                    f.write(f" - {event.details}")
                f.write("\n")
    
    def write_summary(self):
        """Write summary statistics."""
        if not self.enabled or not self.frames:
            return
        
        if not self.log_file:
            return  # No log file configured
        
        total_frames = len(self.frames)
        avg_time = sum(f.total_ms for f in self.frames) / total_frames if total_frames else 0
        
        # Aggregate by step
        step_times: Dict[str, List[float]] = {}
        for frame in self.frames:
            for event in frame.events:
                if event.duration_ms:
                    if event.name not in step_times:
                        step_times[event.name] = []
                    step_times[event.name].append(event.duration_ms)
        
        with self._file_lock:
            with open(self.log_file, "a") as f:
                f.write("# Summary\n\n")
                f.write(f"**Total Frames:** {total_frames}\n")
                f.write(f"**Avg Frame Time:** {avg_time:.0f}ms\n\n")
                
                if step_times:
                    f.write("## Step Breakdown\n\n")
                    f.write("| Step | Avg | Min | Max | Count |\n")
                    f.write("|------|-----|-----|-----|-------|\n")
                    
                    for step, times in sorted(step_times.items()):
                        avg = sum(times) / len(times)
                        min_t = min(times)
                        max_t = max(times)
                        f.write(f"| {step} | {avg:.0f}ms | {min_t:.0f}ms | {max_t:.0f}ms | {len(times)} |\n")
                    f.write("\n")
                
                f.write(f"\nEnded: {datetime.now().isoformat()}\n")
    
    def export_json(self, output_path: Path = None) -> str:
        """Export logs to JSON format."""
        import json
        
        data = {
            "metadata": {
                "started": self.frames[0].timestamp.isoformat() if self.frames else None,
                "ended": datetime.now().isoformat(),
                "total_frames": self._total_frames,
                "skipped_frames": self._skipped_frames,
                "decisions": len(self._decisions),
            },
            "stats": {},
            "frames": [],
            "decisions": self._decisions,
        }
        
        # Add stats
        for name, times in self._stats.items():
            if times:
                data["stats"][name] = {
                    "avg_ms": sum(times) / len(times),
                    "min_ms": min(times),
                    "max_ms": max(times),
                    "count": len(times),
                }
        
        # Add frames
        for frame in self.frames:
            frame_data = {
                "frame_num": frame.frame_num,
                "timestamp": frame.timestamp.isoformat(),
                "total_ms": frame.total_ms,
                "result": frame.result,
                "events": [
                    {
                        "name": e.name,
                        "duration_ms": e.duration_ms,
                        "details": e.details,
                    }
                    for e in frame.events
                ],
            }
            data["frames"].append(frame_data)
        
        json_str = json.dumps(data, indent=2, default=str)
        
        if output_path:
            output_path = Path(output_path)
            output_path.write_text(json_str)
        
        return json_str
    
    def export_yaml(self, output_path: Path = None) -> str:
        """Export logs to YAML format."""
        try:
            import yaml
        except ImportError:
            # Fallback to simple YAML-like format
            return self._export_simple_yaml(output_path)
        
        data = {
            "metadata": {
                "started": self.frames[0].timestamp.isoformat() if self.frames else None,
                "ended": datetime.now().isoformat(),
                "total_frames": self._total_frames,
                "skipped_frames": self._skipped_frames,
                "decisions": len(self._decisions),
            },
            "stats": {},
            "frames": [],
            "decisions": self._decisions,
        }
        
        # Add stats
        for name, times in self._stats.items():
            if times:
                data["stats"][name] = {
                    "avg_ms": round(sum(times) / len(times), 1),
                    "min_ms": round(min(times), 1),
                    "max_ms": round(max(times), 1),
                    "count": len(times),
                }
        
        # Add frames (summarized)
        for frame in self.frames:
            frame_data = {
                "frame": frame.frame_num,
                "time": frame.timestamp.strftime("%H:%M:%S"),
                "total_ms": round(frame.total_ms, 0),
                "result": frame.result,
            }
            data["frames"].append(frame_data)
        
        yaml_str = yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        if output_path:
            output_path = Path(output_path)
            output_path.write_text(yaml_str)
        
        return yaml_str
    
    def _export_simple_yaml(self, output_path: Path = None) -> str:
        """Simple YAML export without PyYAML dependency."""
        lines = [
            "metadata:",
            f"  started: {self.frames[0].timestamp.isoformat() if self.frames else 'null'}",
            f"  ended: {datetime.now().isoformat()}",
            f"  total_frames: {self._total_frames}",
            f"  skipped_frames: {self._skipped_frames}",
            f"  decisions: {len(self._decisions)}",
            "",
            "stats:",
        ]
        
        for name, times in self._stats.items():
            if times:
                lines.append(f"  {name}:")
                lines.append(f"    avg_ms: {sum(times) / len(times):.1f}")
                lines.append(f"    min_ms: {min(times):.1f}")
                lines.append(f"    max_ms: {max(times):.1f}")
                lines.append(f"    count: {len(times)}")
        
        lines.extend(["", "frames:"])
        for frame in self.frames:
            lines.append(f"  - frame: {frame.frame_num}")
            lines.append(f"    time: {frame.timestamp.strftime('%H:%M:%S')}")
            lines.append(f"    total_ms: {frame.total_ms:.0f}")
            if frame.result:
                lines.append(f"    result: {frame.result}")
        
        yaml_str = "\n".join(lines)
        
        if output_path:
            output_path = Path(output_path)
            output_path.write_text(yaml_str)
        
        return yaml_str
    
    def export_markdown(self, output_path: Path = None) -> str:
        """Export logs to Markdown format."""
        lines = [
            "# Timing Log Report",
            "",
            f"**Started:** {self.frames[0].timestamp.isoformat() if self.frames else 'N/A'}",
            f"**Ended:** {datetime.now().isoformat()}",
            "",
            "## Summary",
            "",
            f"- **Total Frames:** {self._total_frames}",
            f"- **Skipped Frames:** {self._skipped_frames}",
            f"- **Decisions:** {len(self._decisions)}",
            "",
            "## Performance Stats",
            "",
            "| Step | Avg (ms) | Min (ms) | Max (ms) | Count |",
            "|------|----------|----------|----------|-------|",
        ]
        
        for name, times in sorted(self._stats.items()):
            if times:
                avg = sum(times) / len(times)
                lines.append(f"| {name} | {avg:.1f} | {min(times):.1f} | {max(times):.1f} | {len(times)} |")
        
        lines.extend([
            "",
            "## Frame Details",
            "",
        ])
        
        for frame in self.frames[:50]:  # Limit to first 50 frames
            lines.append(f"### Frame {frame.frame_num} ({frame.timestamp.strftime('%H:%M:%S')})")
            lines.append("")
            for event in frame.events:
                duration = f"{event.duration_ms:.0f}ms" if event.duration_ms else "-"
                detail = f" - {event.details}" if event.details else ""
                lines.append(f"- **{event.name}:** {duration}{detail}")
            if frame.result:
                lines.append(f"- **Result:** {frame.result}")
            lines.append("")
        
        if len(self.frames) > 50:
            lines.append(f"*... and {len(self.frames) - 50} more frames*")
        
        md_str = "\n".join(lines)
        
        if output_path:
            output_path = Path(output_path)
            output_path.write_text(md_str)
        
        return md_str
    
    def export_all(self, base_path: str):
        """Export to all formats (CSV, TXT, JSON, YAML, MD)."""
        base = Path(base_path).with_suffix('')
        
        # CSV is already written during logging
        
        # Export other formats
        self.export_json(base.with_suffix('.json'))
        self.export_yaml(base.with_suffix('.yaml'))
        self.export_markdown(base.with_suffix('.md'))
        
        print(f"\n📊 Logs exported:", flush=True)
        print(f"   CSV:  {base.with_suffix('.csv')}", flush=True)
        print(f"   JSON: {base.with_suffix('.json')}", flush=True)
        print(f"   YAML: {base.with_suffix('.yaml')}", flush=True)
        print(f"   MD:   {base.with_suffix('.md')}", flush=True)


# Global logger instance
_logger: Optional[TimingLogger] = None


def get_logger(log_file: Optional[str] = None, verbose: bool = False) -> TimingLogger:
    """Get or create timing logger.
    
    If a logger already exists, reuse it but update verbose flag if requested.
    Does NOT create auto-log if csv_file is already set.
    """
    global _logger
    
    if _logger is not None:
        # Logger already exists - just update verbose flag if needed
        if verbose:
            _logger.verbose = True
            _logger.enabled = True
        # Return existing logger - DON'T create new one
        return _logger
    
    # No logger exists - create new one
    if log_file or verbose:
        _logger = TimingLogger(log_file, verbose=verbose)
    else:
        _logger = TimingLogger(None)  # Disabled logger
    
    return _logger


def set_log_file(log_file: str, verbose: bool = False):
    """Set log file for global logger. 
    
    This should be called BEFORE get_logger() to set the output file.
    """
    global _logger
    # Create new logger with the specified file
    _logger = TimingLogger(log_file, verbose=verbose)
    return _logger


def reset_logger():
    """Reset global logger (for testing)."""
    global _logger
    _logger = None
