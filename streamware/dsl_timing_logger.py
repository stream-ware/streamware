"""
DSL Timing Logger

CSV-based performance logging for motion analysis pipeline.
Tracks timing of each step for performance analysis.

Usage:
    from streamware.dsl_timing_logger import DSLTimingLogger
    
    logger = DSLTimingLogger("dsl_timing.csv")
    logger.start_frame(1)
    logger.log_step("capture", 50.2)
    logger.log_step("analyze", 23.5)
    logger.end_frame()
"""

import csv
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class FrameTiming:
    """Timing data for a single frame."""
    frame_num: int
    timestamp: str
    total_ms: float = 0.0
    steps: Dict[str, float] = field(default_factory=dict)
    blobs_detected: int = 0
    motion_percent: float = 0.0
    events_count: int = 0


class DSLTimingLogger:
    """
    CSV-based timing logger for DSL motion analysis.
    
    Generates detailed timing logs for performance analysis.
    """
    
    CSV_HEADERS = [
        "frame_num",
        "timestamp",
        "total_ms",
        "capture_ms",
        "grayscale_ms",
        "blur_ms",
        "diff_ms",
        "threshold_ms",
        "contours_ms",
        "tracking_ms",
        "thumbnail_ms",
        "stream_ms",
        "blobs",
        "motion_pct",
        "events",
    ]
    
    def __init__(
        self,
        log_file: str = "dsl_timing.csv",
        print_realtime: bool = True,
        print_interval: int = 1,  # Print every N frames
    ):
        self.log_file = Path(log_file)
        self.print_realtime = print_realtime
        self.print_interval = print_interval
        
        self._current_frame: Optional[FrameTiming] = None
        self._frame_start: float = 0
        self._step_start: float = 0
        self._frames: List[FrameTiming] = []
        self._file_handle = None
        self._csv_writer = None
        
        # Initialize CSV file
        self._init_csv()
    
    def _init_csv(self):
        """Initialize CSV file with headers."""
        self._file_handle = open(self.log_file, 'w', newline='')
        self._csv_writer = csv.DictWriter(self._file_handle, fieldnames=self.CSV_HEADERS)
        self._csv_writer.writeheader()
        self._file_handle.flush()
    
    def start_frame(self, frame_num: int):
        """Start timing a new frame."""
        self._frame_start = time.perf_counter()
        self._current_frame = FrameTiming(
            frame_num=frame_num,
            timestamp=datetime.now().strftime("%H:%M:%S.%f")[:-3],
        )
    
    def start_step(self, step_name: str):
        """Start timing a step within the frame."""
        self._step_start = time.perf_counter()
    
    def end_step(self, step_name: str):
        """End timing a step and record duration."""
        if self._current_frame:
            duration_ms = (time.perf_counter() - self._step_start) * 1000
            self._current_frame.steps[step_name] = duration_ms
    
    def log_step(self, step_name: str, duration_ms: float):
        """Log a step with explicit duration."""
        if self._current_frame:
            self._current_frame.steps[step_name] = duration_ms
    
    def set_metrics(self, blobs: int = 0, motion_pct: float = 0.0, events: int = 0):
        """Set frame metrics."""
        if self._current_frame:
            self._current_frame.blobs_detected = blobs
            self._current_frame.motion_percent = motion_pct
            self._current_frame.events_count = events
    
    def end_frame(self):
        """End frame timing and write to CSV."""
        if not self._current_frame:
            return
        
        self._current_frame.total_ms = (time.perf_counter() - self._frame_start) * 1000
        self._frames.append(self._current_frame)
        
        # Write to CSV
        row = {
            "frame_num": self._current_frame.frame_num,
            "timestamp": self._current_frame.timestamp,
            "total_ms": f"{self._current_frame.total_ms:.1f}",
            "capture_ms": f"{self._current_frame.steps.get('capture', 0):.1f}",
            "grayscale_ms": f"{self._current_frame.steps.get('grayscale', 0):.1f}",
            "blur_ms": f"{self._current_frame.steps.get('blur', 0):.1f}",
            "diff_ms": f"{self._current_frame.steps.get('diff', 0):.1f}",
            "threshold_ms": f"{self._current_frame.steps.get('threshold', 0):.1f}",
            "contours_ms": f"{self._current_frame.steps.get('contours', 0):.1f}",
            "tracking_ms": f"{self._current_frame.steps.get('tracking', 0):.1f}",
            "thumbnail_ms": f"{self._current_frame.steps.get('thumbnail', 0):.1f}",
            "stream_ms": f"{self._current_frame.steps.get('stream', 0):.1f}",
            "blobs": self._current_frame.blobs_detected,
            "motion_pct": f"{self._current_frame.motion_percent:.2f}",
            "events": self._current_frame.events_count,
        }
        self._csv_writer.writerow(row)
        self._file_handle.flush()
        
        # Print realtime if enabled
        if self.print_realtime and self._current_frame.frame_num % self.print_interval == 0:
            self._print_frame_summary()
        
        self._current_frame = None
    
    def _print_frame_summary(self):
        """Print frame timing summary."""
        f = self._current_frame
        if not f:
            return
        
        # Build step breakdown
        steps_str = " | ".join([
            f"{k}:{v:.0f}ms" for k, v in sorted(f.steps.items())
            if v > 0.1  # Only show steps > 0.1ms
        ])
        
        print(
            f"⏱️ F{f.frame_num}: {f.total_ms:.0f}ms total | "
            f"{f.blobs_detected} blobs | {f.motion_percent:.1f}% motion | "
            f"{steps_str}",
            flush=True
        )
    
    def get_summary(self) -> Dict:
        """Get summary statistics."""
        if not self._frames:
            return {}
        
        total_times = [f.total_ms for f in self._frames]
        
        return {
            "frames": len(self._frames),
            "avg_ms": sum(total_times) / len(total_times),
            "min_ms": min(total_times),
            "max_ms": max(total_times),
            "fps": 1000 / (sum(total_times) / len(total_times)) if total_times else 0,
            "log_file": str(self.log_file),
        }
    
    def print_summary(self):
        """Print final summary."""
        s = self.get_summary()
        if not s:
            return
        
        print(f"\n📊 DSL Timing Summary ({s['frames']} frames):")
        print(f"   Avg: {s['avg_ms']:.1f}ms | Min: {s['min_ms']:.1f}ms | Max: {s['max_ms']:.1f}ms")
        print(f"   Effective FPS: {s['fps']:.2f}")
        print(f"   Log file: {s['log_file']}")
    
    def close(self):
        """Close CSV file."""
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None


# Global instance
_dsl_logger: Optional[DSLTimingLogger] = None


def get_dsl_logger(log_file: str = None) -> DSLTimingLogger:
    """Get or create global DSL timing logger."""
    global _dsl_logger
    
    if _dsl_logger is None:
        file = log_file or f"dsl_timing_{int(time.time())}.csv"
        _dsl_logger = DSLTimingLogger(log_file=file)
    
    return _dsl_logger


def close_dsl_logger():
    """Close global logger."""
    global _dsl_logger
    if _dsl_logger:
        _dsl_logger.print_summary()
        _dsl_logger.close()
        _dsl_logger = None
