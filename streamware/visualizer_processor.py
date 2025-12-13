"""
Real-time Frame Processor

Processes frames in real-time and generates SVG overlays.
Extracted from realtime_visualizer.py for modularity.
"""

import base64
import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class FrameData:
    """Data for single frame - optimized for minimal JSON size."""
    frame_num: int
    timestamp: float
    jpeg_base64: str = ""
    svg_overlay: str = ""
    dsl_text: str = ""
    motion_percent: float = 0.0
    objects: List[Dict] = None
    events: List[str] = None
    
    def to_json(self) -> str:
        import json
        data = {
            "f": self.frame_num,
            "t": self.timestamp,
            "m": round(self.motion_percent, 1),
        }
        if self.jpeg_base64:
            data["img"] = self.jpeg_base64
        if self.svg_overlay:
            data["svg"] = self.svg_overlay
        if self.dsl_text:
            data["dsl"] = self.dsl_text
        if self.objects:
            data["obj"] = self.objects
        return json.dumps(data, separators=(',', ':'))


class RealtimeProcessor:
    """
    Processes frames in real-time and generates SVG overlays.
    Optimized for speed - uses lightweight OpenCV operations only.
    """
    
    def __init__(self, width: int = 640, height: int = 480, lite_mode: bool = True):
        self.width = width
        self.height = height
        self.lite_mode = lite_mode
        
        self._analyzer = None
        self._dsl_generator = None
        self._prev_gray = None
        self._bg_subtractor = None
        
        self._frame_count = 0
        self._blobs = []
        self._next_blob_id = 1
        self._prev_blobs = {}
        
        self._last_jpeg_b64 = ""
        self._no_motion_count = 0
        self._timing_stats = []
    
    def _ensure_initialized(self):
        """Lazy initialize components."""
        if self._bg_subtractor is None:
            try:
                import cv2
                self._bg_subtractor = cv2.createBackgroundSubtractorMOG2(
                    history=30,
                    varThreshold=25,
                    detectShadows=False
                )
            except ImportError:
                pass
        
        if self._analyzer is None and not self.lite_mode:
            from .frame_diff_dsl import FrameDiffAnalyzer, DSLGenerator
            self._analyzer = FrameDiffAnalyzer()
            self._dsl_generator = DSLGenerator()
    
    def process_frame(self, frame) -> FrameData:
        """Process single frame - ULTRA FAST."""
        self._ensure_initialized()
        self._frame_count += 1
        
        t0 = time.time()
        t_bg_ms = 0.0
        t_svg_ms = 0.0
        t_jpeg_ms = 0.0
        
        try:
            import cv2
            import numpy as np
            
            if isinstance(frame, bytes):
                nparr = np.frombuffer(frame, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None or not isinstance(frame, np.ndarray):
                return self._empty_frame_data(None)
            
            h, w = frame.shape[:2]
            
            motion_percent = 0.0
            blobs = []
            
            if self._bg_subtractor is not None:
                t_bg_start = time.time()
                mask = self._bg_subtractor.apply(frame)
                motion_percent = (cv2.countNonZero(mask) / (h * w)) * 100
                
                if motion_percent > 1.0:
                    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
                    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
                    
                    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:3]
                    
                    for contour in contours:
                        area = cv2.contourArea(contour)
                        if area < 100:
                            continue
                        
                        x, y, bw, bh = cv2.boundingRect(contour)
                        blobs.append({
                            "id": len(blobs) + 1,
                            "x": round((x + bw/2) / w, 3),
                            "y": round((y + bh/2) / h, 3),
                            "w": round(bw / w, 3),
                            "h": round(bh / h, 3),
                        })
                t_bg_ms = (time.time() - t_bg_start) * 1000.0
            
            t_svg_start = time.time()
            svg = self._generate_fast_svg(blobs, motion_percent)
            dsl_text = self._generate_fast_dsl(blobs, motion_percent)
            t_svg_ms = (time.time() - t_svg_start) * 1000.0
            
            if motion_percent > 1.0 or self._no_motion_count >= 5 or not self._last_jpeg_b64:
                t_jpeg_start = time.time()
                _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 20])
                self._last_jpeg_b64 = base64.b64encode(jpeg.tobytes()).decode()
                self._no_motion_count = 0
                t_jpeg_ms = (time.time() - t_jpeg_start) * 1000.0
            else:
                self._no_motion_count += 1
                t_jpeg_ms = 0.0
            
            t_total_ms = (time.time() - t0) * 1000.0
            
            self._timing_stats.append({
                "bg": t_bg_ms, "svg": t_svg_ms, "jpeg": t_jpeg_ms,
                "total": t_total_ms, "blobs": len(blobs), "motion": motion_percent,
            })
            
            if len(self._timing_stats) >= 50:
                samples = self._timing_stats
                n = len(samples)
                avg_total = sum(s["total"] for s in samples) / n
                avg_motion = sum(s["motion"] for s in samples) / n
                print(f"🧮 Proc: avg={avg_total:.1f}ms motion={avg_motion:.1f}%")
                self._timing_stats.clear()
            
            return FrameData(
                frame_num=self._frame_count,
                timestamp=time.time(),
                jpeg_base64=self._last_jpeg_b64,
                svg_overlay=svg,
                dsl_text=dsl_text,
                motion_percent=motion_percent,
                objects=blobs,
                events=[],
            )
            
        except Exception as e:
            logger.debug(f"Frame processing error: {e}")
            return self._empty_frame_data(None)
    
    def _empty_frame_data(self, frame=None) -> FrameData:
        """Return empty frame data."""
        return FrameData(
            frame_num=self._frame_count,
            timestamp=time.time(),
            jpeg_base64=self._last_jpeg_b64 or "",
            svg_overlay="",
            dsl_text="",
            motion_percent=0.0,
            objects=[],
            events=[],
        )
    
    def _generate_fast_svg(self, blobs: list, motion_percent: float) -> str:
        """Generate simple SVG overlay - optimized for speed."""
        colors = ["#ff6b6b", "#4ecdc4", "#45b7d1", "#96ceb4", "#ffeaa7"]
        
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.width} {self.height}" style="position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;">'
        
        bar_width = min(200, motion_percent * 4)
        svg += f'<rect x="10" y="10" width="{bar_width:.0f}" height="6" fill="#00ff00" rx="3"/>'
        svg += f'<text x="10" y="30" fill="white" font-size="11" font-family="monospace">Motion: {motion_percent:.1f}%</text>'
        
        for i, blob in enumerate(blobs):
            color = colors[i % len(colors)]
            x = (blob["x"] - blob["w"]/2) * self.width
            y = (blob["y"] - blob["h"]/2) * self.height
            w = blob["w"] * self.width
            h = blob["h"] * self.height
            
            svg += f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" stroke="{color}" stroke-width="2" fill="none"/>'
            svg += f'<circle cx="{blob["x"] * self.width:.0f}" cy="{blob["y"] * self.height:.0f}" r="4" fill="{color}"/>'
            svg += f'<text x="{x:.0f}" y="{y - 5:.0f}" fill="{color}" font-size="11">#{blob["id"]}</text>'
        
        svg += '</svg>'
        return svg
    
    def _generate_fast_dsl(self, blobs: list, motion_percent: float) -> str:
        """Generate detailed DSL text with timestamp."""
        now = time.time()
        ts_full = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))
        ts_ms = f".{int((now % 1) * 1000):03d}"
        
        lines = [f"FRAME {self._frame_count} @ {ts_full}{ts_ms}"]
        lines.append(f"  UNIX_TS: {now:.3f}")
        lines.append(f"  MOTION: {motion_percent:.2f}%")
        lines.append(f"  BLOBS: {len(blobs)}")
        
        if motion_percent > 5.0:
            level = 'HIGH' if motion_percent > 20 else 'MEDIUM' if motion_percent > 10 else 'LOW'
            lines.append(f"  EVENT: MOTION_DETECTED level={level}")
        
        for blob in blobs:
            cx_px = int(blob['x'] * self.width)
            cy_px = int(blob['y'] * self.height)
            w_px = int(blob['w'] * self.width)
            h_px = int(blob['h'] * self.height)
            
            quadrant = "TOP" if blob['y'] < 0.33 else "BOTTOM" if blob['y'] > 0.66 else "CENTER"
            quadrant += "-LEFT" if blob['x'] < 0.33 else "-RIGHT" if blob['x'] > 0.66 else "-CENTER"
            
            lines.append(f"  BLOB #{blob['id']}:")
            lines.append(f"    pos: ({blob['x']:.3f}, {blob['y']:.3f}) -> ({cx_px}px, {cy_px}px)")
            lines.append(f"    size: {w_px}x{h_px}px")
            lines.append(f"    region: {quadrant}")
        
        return "\n".join(lines)
    
    def reset(self):
        """Reset processor."""
        if self._analyzer:
            self._analyzer.reset()
        if self._dsl_generator:
            self._dsl_generator.reset()
        self._frame_count = 0
