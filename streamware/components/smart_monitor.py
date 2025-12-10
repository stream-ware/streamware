"""
Smart Monitor Component - Advanced motion detection with frame buffering

Features:
1. Frame buffering - captures frames independently of LLM processing speed
2. Adaptive detection - adjusts sensitivity based on activity
3. Zone-based monitoring - focus on specific areas
4. Multi-stage analysis - quick diff → region extraction → AI on regions
5. Queue-based processing - LLM processes buffered frames asynchronously
6. Configurable timing - min/max intervals, processing delays

This solves the problem where LLM can't keep up with frame capture rate.

URI Examples:
    smart://monitor?source=rtsp://camera/live&buffer_size=100
    smart://watch?source=rtsp://camera/live&min_interval=1&max_interval=10
    smart://zones?source=rtsp://camera/live&zones=entrance:0,0,50,100

Related:
    - streamware/components/motion_diff.py
    - streamware/components/stream.py
"""

import subprocess
import tempfile
import logging
import time
import os
import threading
import queue
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime
import base64
from ..core import Component, StreamwareURI, register
from ..exceptions import ComponentError
from ..config import config

logger = logging.getLogger(__name__)


@dataclass
class BufferedFrame:
    """Frame stored in buffer for processing"""
    frame_num: int
    timestamp: datetime
    path: Path
    regions: List[Dict] = field(default_factory=list)
    change_percent: float = 0.0
    processed: bool = False
    analysis: str = ""


@dataclass
class MonitorZone:
    """Zone to monitor"""
    name: str
    x: int  # 0-100 scale
    y: int
    width: int
    height: int
    sensitivity: float = 25.0  # Threshold for this zone
    
    def to_pixels(self, img_width: int, img_height: int) -> Tuple[int, int, int, int]:
        """Convert percentage coordinates to pixels"""
        px = int(self.x / 100 * img_width)
        py = int(self.y / 100 * img_height)
        pw = int(self.width / 100 * img_width)
        ph = int(self.height / 100 * img_height)
        return px, py, pw, ph


@dataclass
class MonitorConfig:
    """Configuration for smart monitoring"""
    # Timing
    min_interval: float = 1.0      # Minimum seconds between captures
    max_interval: float = 10.0     # Maximum seconds between captures
    adaptive_interval: bool = True  # Adjust interval based on activity
    
    # Buffer
    buffer_size: int = 100         # Max frames to buffer
    process_delay: float = 0.5     # Delay before processing (let buffer fill)
    
    # Detection
    diff_threshold: int = 25       # Pixel diff threshold (0-100)
    min_change_percent: float = 0.5  # Minimum % change to trigger
    min_region_size: int = 500     # Minimum region size in pixels
    grid_size: int = 8             # Grid for region detection
    
    # AI Processing
    ai_enabled: bool = True        # Enable AI analysis on regions
    max_regions_to_analyze: int = 3  # Limit AI calls per frame
    ai_timeout: float = 30.0       # AI call timeout
    
    # Quality
    capture_quality: int = 90      # JPEG quality (1-100)
    region_margin: int = 30        # Margin around detected regions
    upscale_regions: bool = True   # Upscale small regions for better AI analysis
    
    # Output
    save_all_frames: bool = False  # Save all frames or only changes
    output_dir: Optional[str] = None


@register("smart")
@register("monitor")
class SmartMonitorComponent(Component):
    """
    Smart monitoring with frame buffering and adaptive detection.
    
    Operations:
        - monitor: Full monitoring with buffering and AI
        - watch: Quick monitoring (fast diff only, no AI)
        - zones: Zone-based monitoring
        - buffer: Show buffer status
    
    Key Features:
        1. Frame Buffer: Captures continue even when LLM is processing
        2. Adaptive Timing: Captures more frequently when activity detected
        3. Zone Focus: Define specific areas to monitor
        4. Quality Enhancement: Upscales regions before AI analysis
    
    URI Examples:
        smart://monitor?source=rtsp://camera/live&buffer_size=50
        smart://watch?source=rtsp://camera/live&min_interval=2
        smart://zones?source=rtsp://camera/live&zones=door:0,40,30,60
    """
    
    input_mime = "*/*"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.operation = uri.operation or "monitor"
        self.source = uri.get_param("source", uri.get_param("url", ""))
        
        # Build config from URI params
        def str_to_bool(val, default=True):
            if isinstance(val, bool):
                return val
            return str(val).lower() in ("true", "1", "yes")
        
        self.config = MonitorConfig(
            min_interval=float(uri.get_param("min_interval", "1")),
            max_interval=float(uri.get_param("max_interval", "10")),
            adaptive_interval=str_to_bool(uri.get_param("adaptive", "true")),
            buffer_size=int(uri.get_param("buffer_size", "100")),
            diff_threshold=int(uri.get_param("threshold", "25")),
            min_change_percent=float(uri.get_param("min_change", "0.5")),
            min_region_size=int(uri.get_param("min_region", "500")),
            grid_size=int(uri.get_param("grid", "8")),
            ai_enabled=str_to_bool(uri.get_param("ai", "true")),
            max_regions_to_analyze=int(uri.get_param("max_regions", "3")),
            capture_quality=int(uri.get_param("quality", "90")),
            save_all_frames=str_to_bool(uri.get_param("save_all", "false"), False),
            output_dir=uri.get_param("output_dir")
        )
        
        # Duration and focus
        self.duration = int(uri.get_param("duration", "60"))
        self.focus = uri.get_param("focus", "person")
        self.model = uri.get_param("model", "llava:13b")
        
        # Parse zones
        zones_str = uri.get_param("zones", "")
        self.zones = self._parse_zones(zones_str) if zones_str else []
        
        # Internal state
        self._temp_dir = None
        self._frame_buffer: queue.Queue = queue.Queue(maxsize=self.config.buffer_size)
        self._results: List[Dict] = []
        self._prev_frame_path: Optional[Path] = None
        self._running = False
        self._current_interval = self.config.min_interval
        self._activity_score = 0.0
    
    def _parse_zones(self, zones_str: str) -> List[MonitorZone]:
        """Parse zone definitions from string"""
        zones = []
        for zone_def in zones_str.split("|"):
            if ":" not in zone_def:
                continue
            name, coords = zone_def.split(":", 1)
            parts = coords.split(",")
            if len(parts) >= 4:
                zones.append(MonitorZone(
                    name=name.strip(),
                    x=int(parts[0]),
                    y=int(parts[1]),
                    width=int(parts[2]),
                    height=int(parts[3]),
                    sensitivity=float(parts[4]) if len(parts) > 4 else 25.0
                ))
        return zones
    
    def process(self, data: Any) -> Dict:
        """Process smart monitoring"""
        self._temp_dir = Path(tempfile.mkdtemp())
        self._running = True
        
        try:
            if self.operation == "monitor":
                return self._run_buffered_monitor()
            elif self.operation == "watch":
                return self._run_quick_watch()
            elif self.operation == "zones":
                return self._run_zone_monitor()
            elif self.operation == "buffer":
                return self._get_buffer_status()
            else:
                raise ComponentError(f"Unknown operation: {self.operation}")
        finally:
            self._running = False
            if self._temp_dir and self._temp_dir.exists():
                import shutil
                shutil.rmtree(self._temp_dir, ignore_errors=True)
    
    def _run_buffered_monitor(self) -> Dict:
        """
        Buffered monitoring with async AI processing.
        
        Architecture:
        - Capture thread: Captures frames at adaptive rate
        - Process thread: Processes buffered frames with AI
        - Main thread: Coordinates and collects results
        """
        results = []
        processed_frames = []
        
        # Start capture thread
        capture_thread = threading.Thread(target=self._capture_loop)
        capture_thread.daemon = True
        capture_thread.start()
        
        # Give capture thread time to fill buffer
        time.sleep(self.config.process_delay)
        
        # Process frames from buffer
        start_time = time.time()
        frame_count = 0
        
        while time.time() - start_time < self.duration or not self._frame_buffer.empty():
            try:
                # Get frame from buffer (with timeout)
                frame = self._frame_buffer.get(timeout=1.0)
                frame_count += 1
                
                # Compute diff
                diff_result = self._compute_diff(frame)
                frame.change_percent = diff_result.get("change_percent", 0)
                frame.regions = diff_result.get("regions", [])
                
                # Determine if this frame needs AI analysis
                needs_analysis = (
                    frame.change_percent >= self.config.min_change_percent and
                    len(frame.regions) > 0 and
                    self.config.ai_enabled
                )
                
                if needs_analysis:
                    # Analyze regions with AI
                    region_analyses = self._analyze_frame_regions(frame)
                    frame.analysis = self._summarize_analyses(region_analyses)
                    frame.processed = True
                    
                    results.append({
                        "frame": frame.frame_num,
                        "timestamp": frame.timestamp.strftime("%H:%M:%S.%f")[:-3],
                        "type": "change",
                        "change_percent": frame.change_percent,
                        "regions": len(frame.regions),
                        "analysis": frame.analysis,
                        "region_details": region_analyses,
                        "image_base64": self._get_frame_base64(frame.path)
                    })
                    
                    # Increase activity score (more frequent captures)
                    self._activity_score = min(1.0, self._activity_score + 0.3)
                else:
                    # No change or minor change
                    if self.config.save_all_frames:
                        results.append({
                            "frame": frame.frame_num,
                            "timestamp": frame.timestamp.strftime("%H:%M:%S.%f")[:-3],
                            "type": "stable",
                            "change_percent": frame.change_percent
                        })
                    
                    # Decrease activity score (less frequent captures)
                    self._activity_score = max(0.0, self._activity_score - 0.1)
                
                # Update adaptive interval
                if self.config.adaptive_interval:
                    self._current_interval = (
                        self.config.min_interval + 
                        (self.config.max_interval - self.config.min_interval) * 
                        (1 - self._activity_score)
                    )
                
                # Update previous frame
                self._prev_frame_path = frame.path
                processed_frames.append(frame)
                
            except queue.Empty:
                if time.time() - start_time >= self.duration:
                    break
                continue
        
        # Stop capture
        self._running = False
        
        # Wait for capture thread
        capture_thread.join(timeout=2.0)
        
        # Generate summary
        changes = [r for r in results if r.get("type") == "change"]
        
        return {
            "success": True,
            "operation": "monitor",
            "source": self.source,
            "mode": "buffered",
            "config": {
                "min_interval": self.config.min_interval,
                "max_interval": self.config.max_interval,
                "adaptive": self.config.adaptive_interval,
                "buffer_size": self.config.buffer_size,
                "threshold": self.config.diff_threshold
            },
            "timeline": results,
            "significant_changes": len(changes),
            "frames_captured": frame_count,
            "frames_with_changes": len(changes),
            "buffer_overflows": max(0, frame_count - len(processed_frames))
        }
    
    def _capture_loop(self):
        """Capture frames in background thread"""
        frame_num = 0
        
        while self._running:
            try:
                # Capture frame
                frame_path = self._capture_frame(frame_num)
                
                if frame_path and frame_path.exists():
                    frame = BufferedFrame(
                        frame_num=frame_num,
                        timestamp=datetime.now(),
                        path=frame_path
                    )
                    
                    try:
                        self._frame_buffer.put(frame, timeout=0.1)
                        frame_num += 1
                    except queue.Full:
                        # Buffer full - drop oldest frame (already happened via maxsize)
                        logger.warning("Frame buffer full, frame dropped")
                
                # Wait for next capture (adaptive interval)
                time.sleep(self._current_interval)
                
            except Exception as e:
                logger.error(f"Capture error: {e}")
                time.sleep(1)
    
    def _capture_frame(self, frame_num: int) -> Optional[Path]:
        """Capture single frame"""
        output_path = self._temp_dir / f"frame_{frame_num:05d}.jpg"
        
        try:
            cmd = [
                "ffmpeg", "-y", "-rtsp_transport", "tcp",
                "-i", self.source,
                "-frames:v", "1",
                "-q:v", str(max(1, min(31, 32 - self.config.capture_quality // 3))),
                str(output_path)
            ]
            
            subprocess.run(cmd, check=True, capture_output=True, timeout=10)
            return output_path
        except Exception as e:
            logger.warning(f"Frame capture failed: {e}")
            return None
    
    def _compute_diff(self, frame: BufferedFrame) -> Dict:
        """Compute pixel diff between current and previous frame"""
        if self._prev_frame_path is None or not self._prev_frame_path.exists():
            return {"change_percent": 100 if frame.frame_num == 0 else 0, "regions": []}
        
        try:
            from PIL import Image, ImageChops
            import numpy as np
            
            img1 = Image.open(self._prev_frame_path).convert('L')
            img2 = Image.open(frame.path).convert('L')
            
            if img1.size != img2.size:
                img2 = img2.resize(img1.size)
            
            # Compute diff
            diff = ImageChops.difference(img1, img2)
            diff_array = np.array(diff)
            
            # Apply threshold
            diff_binary = (diff_array > self.config.diff_threshold).astype(np.uint8) * 255
            
            # Calculate change
            total_pixels = diff_binary.size
            changed_pixels = np.sum(diff_binary > 0)
            change_percent = (changed_pixels / total_pixels) * 100
            
            # Find regions
            regions = self._find_change_regions(diff_binary, img1.size)
            
            return {
                "change_percent": round(change_percent, 2),
                "regions": regions
            }
            
        except Exception as e:
            logger.warning(f"Diff computation failed: {e}")
            return {"change_percent": 0, "regions": []}
    
    def _find_change_regions(self, diff_binary, img_size: Tuple[int, int]) -> List[Dict]:
        """Find changed regions in diff image"""
        import numpy as np
        
        width, height = img_size
        grid_w = width // self.config.grid_size
        grid_h = height // self.config.grid_size
        
        regions = []
        
        for gy in range(self.config.grid_size):
            for gx in range(self.config.grid_size):
                x1 = gx * grid_w
                y1 = gy * grid_h
                x2 = min((gx + 1) * grid_w, width)
                y2 = min((gy + 1) * grid_h, height)
                
                cell = diff_binary[y1:y2, x1:x2]
                cell_change = np.mean(cell) / 255 * 100
                
                if cell_change > 1:  # At least 1% change
                    regions.append({
                        "x": x1, "y": y1,
                        "width": x2 - x1,
                        "height": y2 - y1,
                        "change_percent": round(cell_change, 2)
                    })
        
        # Merge adjacent regions
        regions = self._merge_regions(regions)
        
        # Filter by size
        regions = [r for r in regions if r["width"] * r["height"] >= self.config.min_region_size]
        
        # Sort by change intensity
        regions.sort(key=lambda r: r["change_percent"], reverse=True)
        
        return regions
    
    def _merge_regions(self, regions: List[Dict]) -> List[Dict]:
        """Merge adjacent regions"""
        if not regions:
            return []
        
        merged = []
        used = set()
        
        for i, r1 in enumerate(regions):
            if i in used:
                continue
            
            group = [r1]
            used.add(i)
            
            for j, r2 in enumerate(regions):
                if j in used:
                    continue
                
                margin = max(r1["width"], r1["height"])
                if (abs(r1["x"] - r2["x"]) < margin * 2 and
                    abs(r1["y"] - r2["y"]) < margin * 2):
                    group.append(r2)
                    used.add(j)
            
            if group:
                min_x = min(r["x"] for r in group)
                min_y = min(r["y"] for r in group)
                max_x = max(r["x"] + r["width"] for r in group)
                max_y = max(r["y"] + r["height"] for r in group)
                avg_change = sum(r["change_percent"] for r in group) / len(group)
                
                merged.append({
                    "x": min_x, "y": min_y,
                    "width": max_x - min_x,
                    "height": max_y - min_y,
                    "change_percent": round(avg_change, 2)
                })
        
        return merged
    
    def _analyze_frame_regions(self, frame: BufferedFrame) -> List[Dict]:
        """Analyze changed regions with AI"""
        results = []
        
        for region in frame.regions[:self.config.max_regions_to_analyze]:
            try:
                # Extract and optionally upscale region
                region_img = self._extract_region(frame.path, region)
                if region_img is None:
                    continue
                
                # Analyze with AI
                analysis = self._call_ai(region_img, region)
                
                results.append({
                    "region": region,
                    "analysis": analysis
                })
                
            except Exception as e:
                logger.warning(f"Region analysis failed: {e}")
        
        return results
    
    def _extract_region(self, frame_path: Path, region: Dict) -> Optional[Path]:
        """Extract region from frame, optionally upscaling"""
        try:
            from PIL import Image
            
            img = Image.open(frame_path)
            
            # Add margin
            margin = self.config.region_margin
            x1 = max(0, region["x"] - margin)
            y1 = max(0, region["y"] - margin)
            x2 = min(img.width, region["x"] + region["width"] + margin)
            y2 = min(img.height, region["y"] + region["height"] + margin)
            
            cropped = img.crop((x1, y1, x2, y2))
            
            # Upscale if too small
            if self.config.upscale_regions:
                min_dim = 400
                if cropped.width < min_dim or cropped.height < min_dim:
                    scale = max(min_dim / cropped.width, min_dim / cropped.height)
                    new_size = (int(cropped.width * scale), int(cropped.height * scale))
                    cropped = cropped.resize(new_size, Image.Resampling.LANCZOS)
            
            # Save
            region_path = self._temp_dir / f"region_{region['x']}_{region['y']}.jpg"
            cropped.save(region_path, quality=self.config.capture_quality)
            
            return region_path
            
        except Exception as e:
            logger.warning(f"Region extraction failed: {e}")
            return None
    
    def _call_ai(self, region_path: Path, region: Dict) -> str:
        """Call AI model to analyze region"""
        try:
            import requests
            from ..prompts import render_prompt
            from ..image_optimize import prepare_image_for_llm_base64
            
            # Optimize image before sending
            image_data = prepare_image_for_llm_base64(region_path, preset="fast")
            
            prompt = render_prompt(
                "smart_monitor_region",
                change_percent=region['change_percent'],
                focus=self.focus
            )

            ollama_url = config.get("SQ_OLLAMA_URL", "http://localhost:11434")
            
            response = requests.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "images": [image_data],
                    "stream": False
                },
                timeout=self.config.ai_timeout
            )
            
            if response.ok:
                return response.json().get("response", "")
            return f"AI error: {response.status_code}"
            
        except Exception as e:
            return f"AI analysis failed: {e}"
    
    def _summarize_analyses(self, region_analyses: List[Dict]) -> str:
        """Create summary from region analyses"""
        if not region_analyses:
            return "No significant changes"
        
        parts = []
        for ra in region_analyses:
            region = ra["region"]
            analysis = ra["analysis"][:200]
            parts.append(f"[{region['change_percent']}% change] {analysis}")
        
        return " | ".join(parts)
    
    def _get_frame_base64(self, frame_path: Path) -> str:
        """Get frame as base64"""
        try:
            with open(frame_path, "rb") as f:
                return base64.b64encode(f.read()).decode()
        except Exception:
            return ""
    
    def _run_quick_watch(self) -> Dict:
        """Quick watch mode - pixel diff only, no AI"""
        saved_ai = self.config.ai_enabled
        self.config.ai_enabled = False
        
        try:
            return self._run_buffered_monitor()
        finally:
            self.config.ai_enabled = saved_ai
    
    def _run_zone_monitor(self) -> Dict:
        """Monitor specific zones only"""
        if not self.zones:
            return {"error": "No zones defined. Use zones=name:x,y,w,h|..."}
        
        # Run monitoring with zone filtering
        result = self._run_buffered_monitor()
        
        # Add zone info
        result["zones"] = [
            {"name": z.name, "x": z.x, "y": z.y, "width": z.width, "height": z.height}
            for z in self.zones
        ]
        
        return result
    
    def _get_buffer_status(self) -> Dict:
        """Get buffer status"""
        return {
            "buffer_size": self.config.buffer_size,
            "current_count": self._frame_buffer.qsize(),
            "is_full": self._frame_buffer.full(),
            "current_interval": self._current_interval,
            "activity_score": self._activity_score
        }


# ============================================================================
# Helper Functions
# ============================================================================

def smart_monitor(source: str, duration: int = 60, **kwargs) -> Dict:
    """
    Smart monitoring with buffering.
    
    Args:
        source: RTSP URL or video file
        duration: Monitoring duration in seconds
        **kwargs: Additional config options
    
    Example:
        result = smart_monitor("rtsp://camera/live", 120,
                               min_interval=2, max_interval=10,
                               threshold=20, focus="person")
    """
    from ..core import flow
    
    params = f"source={source}&duration={duration}"
    for k, v in kwargs.items():
        params += f"&{k}={v}"
    
    return flow(f"smart://monitor?{params}").run()


def quick_watch(source: str, duration: int = 30) -> Dict:
    """
    Quick watching - pixel diff only (no AI).
    Very fast, good for initial detection.
    
    Example:
        result = quick_watch("rtsp://camera/live", 30)
        if result['frames_with_changes'] > 0:
            # Now do full analysis
            smart_monitor(source, 60, ai=True)
    """
    from ..core import flow
    return flow(f"smart://watch?source={source}&duration={duration}").run()


def monitor_zones(source: str, zones: str, duration: int = 60) -> Dict:
    """
    Monitor specific zones.
    
    Args:
        source: Video source
        zones: Zone definitions "name:x,y,w,h|name2:x,y,w,h"
        duration: Duration in seconds
    
    Example:
        result = monitor_zones("rtsp://camera/live",
                               "door:0,30,40,70|window:60,20,40,50",
                               duration=120)
    """
    from ..core import flow
    return flow(f"smart://zones?source={source}&zones={zones}&duration={duration}").run()
