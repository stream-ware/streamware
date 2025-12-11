"""
Real-time Visualizer Service

Web-based service that shows:
1. Live RTSP video stream
2. Real-time SVG overlay with tracking
3. DSL metadata stream
4. Interactive controls

Usage:
    from streamware.realtime_visualizer import start_visualizer
    start_visualizer("rtsp://camera/stream", port=8080)
    
    # Then open http://localhost:8080 in browser
"""

import asyncio
import base64
import json
import logging
import queue
import threading
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
import tempfile

logger = logging.getLogger(__name__)


# ============================================================================
# Data Structures
# ============================================================================

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
        # Minimal JSON - skip empty fields
        data = {
            "f": self.frame_num,  # Shorter keys
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
        return json.dumps(data, separators=(',', ':'))  # No whitespace


# ============================================================================
# Frame Processor
# ============================================================================

class RealtimeProcessor:
    """
    Processes frames in real-time and generates SVG overlays.
    
    Optimized for speed - uses lightweight OpenCV operations only.
    """
    
    def __init__(self, width: int = 640, height: int = 480, lite_mode: bool = True):
        self.width = width
        self.height = height
        self.lite_mode = lite_mode  # Skip heavy analysis
        
        # Lazy imports
        self._analyzer = None
        self._dsl_generator = None
        self._prev_gray = None
        self._bg_subtractor = None
        
        self._frame_count = 0
        self._blobs = []  # Current blobs
        self._next_blob_id = 1
        self._prev_blobs = {}
        
        # Delta mode - cache last image if no motion
        self._last_jpeg_b64 = ""
        self._no_motion_count = 0
        # Timing stats for detailed logging
        self._timing_stats = []  # list of dicts with per-stage timings
    
    def _ensure_initialized(self):
        """Lazy initialize components."""
        if self._bg_subtractor is None:
            try:
                import cv2
                # Faster background subtractor with smaller history
                self._bg_subtractor = cv2.createBackgroundSubtractorMOG2(
                    history=30,  # Reduced from 100
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
        """
        Process single frame - ULTRA FAST.
        
        NOW ACCEPTS: numpy array directly (no JPEG decode!)
        
        Optimized pipeline:
        - BG subtraction: ~8ms  
        - Contour (if motion): ~3ms
        - JPEG encode (only 1x!): ~5ms
        - Base64: ~1ms
        TOTAL: ~17ms (can do 60 FPS)
        """
        self._ensure_initialized()
        self._frame_count += 1
        
        # Per-stage timing
        t0 = time.time()
        t_bg_ms = 0.0
        t_svg_ms = 0.0
        t_jpeg_ms = 0.0
        
        try:
            import cv2
            import numpy as np
            
            # Handle both numpy array and JPEG bytes (backwards compat)
            if isinstance(frame, bytes):
                nparr = np.frombuffer(frame, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None or not isinstance(frame, np.ndarray):
                return self._empty_frame_data(None)
            
            h, w = frame.shape[:2]
            
            # Fast motion detection on original frame (already small from capture)
            motion_percent = 0.0
            blobs = []
            
            # Background subtraction + motion metrics
            if self._bg_subtractor is not None:
                t_bg_start = time.time()
                mask = self._bg_subtractor.apply(frame)
                motion_percent = (cv2.countNonZero(mask) / (h * w)) * 100
                
                # Find contours only if significant motion
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
            
            # Generate minimal SVG + DSL
            t_svg_start = time.time()
            svg = self._generate_fast_svg(blobs, motion_percent)
            dsl_text = self._generate_fast_dsl(blobs, motion_percent)
            t_svg_ms = (time.time() - t_svg_start) * 1000.0
            
            # DELTA MODE: Only encode JPEG if motion or every N frames
            encoded_new_jpeg = False
            if motion_percent > 1.0 or self._no_motion_count >= 5 or not self._last_jpeg_b64:
                t_jpeg_start = time.time()
                # Single JPEG encode (quality 20 is enough for monitoring)
                _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 20])
                self._last_jpeg_b64 = base64.b64encode(jpeg.tobytes()).decode()
                self._no_motion_count = 0
                t_jpeg_ms = (time.time() - t_jpeg_start) * 1000.0
                encoded_new_jpeg = True
            else:
                self._no_motion_count += 1
                t_jpeg_ms = 0.0
            
            # Total time for this frame
            t_total_ms = (time.time() - t0) * 1000.0
            
            # Store timing sample for aggregated logging
            self._timing_stats.append({
                "bg": t_bg_ms,
                "svg": t_svg_ms,
                "jpeg": t_jpeg_ms,
                "total": t_total_ms,
                "blobs": len(blobs),
                "motion": motion_percent,
            })
            
            # Every 50 frames print detailed averages
            if len(self._timing_stats) >= 50:
                samples = self._timing_stats
                n = len(samples)
                avg_bg = sum(s["bg"] for s in samples) / n
                avg_svg = sum(s["svg"] for s in samples) / n
                avg_jpeg = sum(s["jpeg"] for s in samples) / n
                avg_total = sum(s["total"] for s in samples) / n
                avg_blobs = sum(s["blobs"] for s in samples) / n
                avg_motion = sum(s["motion"] for s in samples) / n
                max_total = max(s["total"] for s in samples)
                max_jpeg = max(s["jpeg"] for s in samples)
                
                print(
                    f"🧮 Proc timings (last {n} frames): "
                    f"bg={avg_bg:.1f}ms svg={avg_svg:.1f}ms jpeg={avg_jpeg:.1f}ms total={avg_total:.1f}ms "
                    f"| max_total={max_total:.1f}ms max_jpeg={max_jpeg:.1f}ms "
                    f"| blobs={avg_blobs:.1f} motion={avg_motion:.1f}%"
                )
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
        
        # Motion bar
        bar_width = min(200, motion_percent * 4)
        svg += f'<rect x="10" y="10" width="{bar_width:.0f}" height="6" fill="#00ff00" rx="3"/>'
        svg += f'<text x="10" y="30" fill="white" font-size="11" font-family="monospace">Motion: {motion_percent:.1f}%</text>'
        
        # Blobs
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
            lines.append(f"  EVENT: MOTION_DETECTED level={'HIGH' if motion_percent > 20 else 'MEDIUM' if motion_percent > 10 else 'LOW'}")
        
        for blob in blobs:
            cx_px = int(blob['x'] * self.width)
            cy_px = int(blob['y'] * self.height)
            w_px = int(blob['w'] * self.width)
            h_px = int(blob['h'] * self.height)
            area_px = w_px * h_px
            
            # Determine position quadrant
            quadrant = ""
            if blob['y'] < 0.33:
                quadrant = "TOP"
            elif blob['y'] > 0.66:
                quadrant = "BOTTOM"
            else:
                quadrant = "CENTER"
            if blob['x'] < 0.33:
                quadrant += "-LEFT"
            elif blob['x'] > 0.66:
                quadrant += "-RIGHT"
            else:
                quadrant += "-CENTER"
            
            lines.append(f"  BLOB #{blob['id']}:")
            lines.append(f"    pos: ({blob['x']:.3f}, {blob['y']:.3f}) -> ({cx_px}px, {cy_px}px)")
            lines.append(f"    size: ({blob['w']:.3f}, {blob['h']:.3f}) -> {w_px}x{h_px}px = {area_px}px²")
            lines.append(f"    region: {quadrant}")
        
        return "\n".join(lines)
    
    def _generate_svg_overlay(self, delta) -> str:
        """Generate SVG overlay for frame."""
        from .frame_diff_dsl import EventType
        
        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.width} {self.height}" '
            f'style="position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;">'
        ]
        
        # Colors
        colors = ["#ff6b6b", "#4ecdc4", "#45b7d1", "#96ceb4", "#ffeaa7", "#fd79a8"]
        
        # Draw blobs
        for blob in delta.blobs:
            color = colors[blob.id % len(colors)]
            
            # Bounding box
            x = (blob.center.x - blob.size.x/2) * self.width
            y = (blob.center.y - blob.size.y/2) * self.height
            w = blob.size.x * self.width
            h = blob.size.y * self.height
            
            svg_parts.append(
                f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" '
                f'stroke="{color}" stroke-width="2" fill="none" rx="4"/>'
            )
            
            # Center dot
            cx = blob.center.x * self.width
            cy = blob.center.y * self.height
            svg_parts.append(
                f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="4" fill="{color}"/>'
            )
            
            # Label
            label = f"#{blob.id}"
            if blob.classification != "UNKNOWN":
                label = blob.classification
            svg_parts.append(
                f'<text x="{x:.0f}" y="{y - 5:.0f}" fill="{color}" '
                f'font-size="12" font-family="monospace">{label}</text>'
            )
            
            # Velocity arrow
            if blob.velocity.magnitude() > 0.01:
                vx = blob.velocity.x * self.width * 5
                vy = blob.velocity.y * self.height * 5
                svg_parts.append(
                    f'<line x1="{cx:.0f}" y1="{cy:.0f}" '
                    f'x2="{cx + vx:.0f}" y2="{cy + vy:.0f}" '
                    f'stroke="#ffff00" stroke-width="2" marker-end="url(#arrow)"/>'
                )
        
        # Motion indicator
        motion_width = delta.motion_percent * 2  # Scale to pixels
        svg_parts.append(
            f'<rect x="10" y="10" width="{motion_width:.0f}" height="6" '
            f'fill="#00ff00" rx="3"/>'
        )
        svg_parts.append(
            f'<text x="10" y="30" fill="white" font-size="11" '
            f'font-family="monospace">Motion: {delta.motion_percent:.1f}%</text>'
        )
        
        # Event badges
        y_offset = 50
        for event in delta.events[:3]:
            color = "#00ff88" if event.type == EventType.ENTER else "#ff6b6b"
            svg_parts.append(
                f'<text x="10" y="{y_offset}" fill="{color}" font-size="10" '
                f'font-family="monospace">● {event.type.value} {event.direction.value}</text>'
            )
            y_offset += 15
        
        svg_parts.append('</svg>')
        return '\n'.join(svg_parts)
    
    def reset(self):
        """Reset processor."""
        if self._analyzer:
            self._analyzer.reset()
        if self._dsl_generator:
            self._dsl_generator.reset()
        if self._context_builder:
            self._context_builder.reset()
        self._frame_count = 0


# ============================================================================
# RTSP Capture Thread
# ============================================================================

class RTSPCapture:
    """
    Captures frames from RTSP stream in background thread.
    
    Args:
        rtsp_url: RTSP stream URL
        fps: Target frames per second
        width: Frame width
        height: Frame height
        transport: 'tcp' (stable) or 'udp' (lower latency)
        backend: 'opencv' (default), 'gstreamer' (faster), 'pyav' (direct API)
    """
    
    def __init__(
        self,
        rtsp_url: str,
        fps: float = 2.0,
        width: int = 640,
        height: int = 480,
        transport: str = "tcp",
        backend: str = "opencv",  # 'opencv', 'gstreamer', 'pyav'
    ):
        self.rtsp_url = rtsp_url
        self.fps = fps
        self.width = width
        self.height = height
        self.transport = transport.lower()
        self.backend = backend.lower()
        
        self._running = False
        self._thread = None
        # Keep only the most recent frame to avoid lag / backlog
        self._frame_queue = queue.Queue(maxsize=1)
        self._capture = None
        self._av_container = None  # For PyAV backend
        # For stderr suppression (H.264 errors)
        self._stderr_fd = None
        self._devnull_fd = None
    
    def start(self):
        """Start capture thread."""
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Stop capture thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        if self._capture:
            self._capture.release()
    
    def get_frame(self, timeout: float = 1.0) -> Optional[bytes]:
        """Get next frame (JPEG bytes)."""
        try:
            return self._frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def _restore_stderr(self):
        """Restore stderr after suppressing H.264 errors."""
        import os
        try:
            if self._stderr_fd is not None:
                os.dup2(self._stderr_fd, 2)
                os.close(self._stderr_fd)
                self._stderr_fd = None
            if self._devnull_fd is not None:
                os.close(self._devnull_fd)
                self._devnull_fd = None
        except OSError:
            pass
    
    def _suppress_stderr(self):
        """Suppress stderr to hide H.264 decode errors."""
        import os
        try:
            if self._stderr_fd is None:
                self._stderr_fd = os.dup(2)
                self._devnull_fd = os.open(os.devnull, os.O_WRONLY)
                os.dup2(self._devnull_fd, 2)
        except OSError:
            pass
    
    def _capture_loop(self):
        """Background capture loop - supports multiple backends."""
        import os
        
        if self.backend == "pyav":
            self._capture_loop_pyav()
        elif self.backend == "gstreamer":
            self._capture_loop_gstreamer()
        else:
            self._capture_loop_opencv()
    
    def _capture_loop_pyav(self):
        """PyAV backend - OPTIMIZED with hardware decoding and threading."""
        try:
            import av
            import numpy as np
        except ImportError:
            print("❌ PyAV backend requires 'av' library.")
            print("   Install with: pip install av")
            print("   Falling back to OpenCV...")
            self._capture_loop_opencv()
            return
        
        # ULTRA LOW LATENCY options
        options = {
            'rtsp_transport': self.transport,
            'fflags': 'nobuffer+discardcorrupt',
            'flags': 'low_delay',
            'max_delay': '0',
            'analyzeduration': '0',      # Don't analyze stream (faster start)
            'probesize': '32768',        # Minimal probe size
            'sync': 'ext',               # External sync
        }
        
        if self.transport == 'udp':
            options['buffer_size'] = '16384'  # Tiny buffer for UDP
            options['reorder_queue_size'] = '0'
        else:
            options['buffer_size'] = '32768'
        
        transport_label = "UDP" if self.transport == "udp" else "TCP"
        print(f"🎬 Opening RTSP with PyAV [{transport_label}]...")
        
        # Try hardware decoder first (NVIDIA CUVID)
        hw_decoder = None
        try:
            # Check for NVIDIA hardware decoder
            test_codec = av.codec.Codec('h264_cuvid', 'r')
            hw_decoder = 'h264_cuvid'
            print("🚀 NVIDIA CUVID hardware decoder available")
        except Exception:
            pass
        
        try:
            self._av_container = av.open(self.rtsp_url, options=options)
            stream = self._av_container.streams.video[0]
            
            # THREADING: Use all CPU cores for decoding
            stream.thread_type = 'AUTO'  # AUTO, FRAME, or SLICE
            stream.thread_count = 0       # 0 = auto (use all cores)
            
            # Get stream info
            codec_name = stream.codec_context.codec.name
            width = stream.codec_context.width
            height = stream.codec_context.height
            
            print(f"✅ PyAV connected [{transport_label}]")
            print(f"   Codec: {codec_name} | Size: {width}x{height}")
            print(f"   Threading: {stream.thread_type} ({stream.thread_count} threads)")
            if hw_decoder:
                print(f"   Hardware: {hw_decoder}")
            
        except Exception as e:
            print(f"❌ PyAV failed to open stream: {e}")
            print("   Falling back to OpenCV...")
            self._capture_loop_opencv()
            return
        
        # Pre-create reusable reformatter for faster conversion
        import av.video.reformatter
        reformatter = None
        
        # Pre-import cv2 for resize
        try:
            import cv2
            has_cv2 = True
        except ImportError:
            has_cv2 = False
        
        # Capture loop - OPTIMIZED
        capture_fps = max(1.0, float(self.fps))
        interval = 1.0 / capture_fps
        print(f"🎥 Capture FPS target: {capture_fps:.2f}")
        
        last_capture = 0
        frame_count = 0
        skip_count = 0
        decode_times = []
        
        try:
            for packet in self._av_container.demux(video=0):
                if not self._running:
                    break
                
                # Decode packet
                t0 = time.time()
                frames = packet.decode()
                
                for frame in frames:
                    if not self._running:
                        break
                    
                    now = time.time()
                    
                    # Rate limiting - skip frames if too fast
                    if now - last_capture < interval:
                        skip_count += 1
                        continue
                    
                    # Convert to numpy - OPTIMIZED
                    # Use bgr24 for OpenCV compatibility
                    img = frame.to_ndarray(format='bgr24')
                    
                    decode_time = (time.time() - t0) * 1000
                    decode_times.append(decode_time)
                    
                    # Resize if needed (use fastest interpolation)
                    h, w = img.shape[:2]
                    if has_cv2 and (w != self.width or h != self.height):
                        img = cv2.resize(img, (self.width, self.height), interpolation=cv2.INTER_NEAREST)
                    
                    # Put in queue (non-blocking)
                    try:
                        self._frame_queue.put_nowait(img)
                    except queue.Full:
                        try:
                            self._frame_queue.get_nowait()
                            self._frame_queue.put_nowait(img)
                        except Exception:
                            pass
                    
                    last_capture = now
                    frame_count += 1
                    
                    # Stats every 30 frames
                    if frame_count % 30 == 0:
                        ts = time.strftime("%H:%M:%S", time.localtime())
                        avg_decode = sum(decode_times[-30:]) / min(30, len(decode_times))
                        actual_fps = 30 / (now - (last_capture - 30 * interval)) if frame_count > 30 else 0
                        print(f"📷 [{ts}] PyAV F#{frame_count} | decode={avg_decode:.1f}ms | skip={skip_count} | q={self._frame_queue.qsize()}")
                        skip_count = 0
                        
        except av.error.EOFError:
            print("⚠️ Stream ended")
        except Exception as e:
            print(f"⚠️ PyAV capture error: {e}")
        finally:
            if self._av_container:
                self._av_container.close()
            print("🛑 PyAV capture stopped")
    
    def _capture_loop_gstreamer(self):
        """GStreamer backend via OpenCV - lower latency than ffmpeg."""
        try:
            import cv2
            import numpy as np
        except ImportError:
            logger.error("OpenCV not available")
            return
        
        # Build GStreamer pipeline for RTSP
        # This bypasses ffmpeg entirely and uses GStreamer's RTSP handling
        transport_opt = "protocols=tcp" if self.transport == "tcp" else "protocols=udp"
        
        gst_pipeline = (
            f"rtspsrc location={self.rtsp_url} latency=0 {transport_opt} ! "
            f"rtph264depay ! h264parse ! avdec_h264 ! "
            f"videoconvert ! videoscale ! "
            f"video/x-raw,format=BGR,width={self.width},height={self.height} ! "
            f"appsink drop=true max-buffers=1 sync=false"
        )
        
        transport_label = "UDP" if self.transport == "udp" else "TCP"
        print(f"🎬 Opening RTSP with GStreamer [{transport_label}]...")
        print(f"   Pipeline: {gst_pipeline[:80]}...")
        
        self._capture = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
        
        if not self._capture.isOpened():
            print("❌ GStreamer pipeline failed to open")
            print("   Make sure OpenCV is built with GStreamer support")
            print("   Falling back to OpenCV/ffmpeg...")
            self._capture_loop_opencv()
            return
        
        print(f"✅ GStreamer connected [{transport_label}] - native pipeline, no ffmpeg")
        
        # Capture loop (same as OpenCV but without ffmpeg overhead)
        capture_fps = max(1.0, float(self.fps))
        interval = 1.0 / capture_fps
        print(f"🎥 Capture FPS target: {capture_fps:.2f}")
        
        last_capture = 0
        frame_count = 0
        
        while self._running:
            now = time.time()
            if now - last_capture < interval:
                time.sleep(0.002)
                continue
            
            ret, frame = self._capture.read()
            if not ret:
                time.sleep(0.01)
                continue
            
            # Put in queue
            try:
                self._frame_queue.put_nowait(frame.copy())
            except queue.Full:
                try:
                    self._frame_queue.get_nowait()
                    self._frame_queue.put_nowait(frame.copy())
                except Exception:
                    pass
            
            last_capture = now
            frame_count += 1
            
            if frame_count % 30 == 0:
                ts = time.strftime("%H:%M:%S", time.localtime())
                print(f"📷 [{ts}] GStreamer captured {frame_count} frames")
        
        self._capture.release()
        print("🛑 GStreamer capture stopped")
    
    def _capture_loop_opencv(self):
        """OpenCV/ffmpeg backend - default, most compatible."""
        try:
            import cv2
            import numpy as np
        except ImportError:
            logger.error("OpenCV not available")
            return
        
        import os
        
        # MINIMAL BUFFERING for lowest latency
        if self.transport == "udp":
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
                "rtsp_transport;udp|"
                "buffer_size;32768|"
                "max_delay;0|"
                "reorder_queue_size;0|"
                "fflags;+nobuffer+discardcorrupt|"
                "flags;low_delay"
            )
        else:
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
                "rtsp_transport;tcp|"
                "buffer_size;65536|"
                "max_delay;0|"
                "fflags;+nobuffer+discardcorrupt|"
                "flags;low_delay"
            )
        os.environ["OPENCV_LOG_LEVEL"] = "SILENT"
        
        # Redirect stderr to suppress H.264 errors
        self._suppress_stderr()
        
        self._capture = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
        self._capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        
        if not self._capture.isOpened():
            self._restore_stderr()
            print(f"❌ Failed to open RTSP stream: {self.rtsp_url}")
            return
        
        self._restore_stderr()
        transport_label = "UDP" if self.transport == "udp" else "TCP"
        print(f"✅ OpenCV/ffmpeg connected [{transport_label}]")
        
        # Flush buffer
        print("🔄 Flushing RTSP buffer...")
        self._suppress_stderr()
        for _ in range(30):
            self._capture.grab()
        self._restore_stderr()
        print("✅ Buffer flushed")
        
        capture_fps = max(1.0, float(self.fps))
        interval = 1.0 / capture_fps
        print(f"🎥 Capture FPS target: {capture_fps:.2f}")
        
        self._suppress_stderr()
        last_capture = 0
        frame_count = 0
        reconnect_attempts = 0
        
        while self._running:
            now = time.time()
            if now - last_capture < interval:
                time.sleep(0.002)
                continue
            
            ret, frame = self._capture.read()
            
            if not ret:
                reconnect_attempts += 1
                if reconnect_attempts > 3:
                    self._restore_stderr()
                    print("⚠️ RTSP reconnecting...")
                    self._suppress_stderr()
                    time.sleep(0.5)
                    self._capture.release()
                    self._capture = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
                    self._capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    reconnect_attempts = 0
                continue
            
            reconnect_attempts = 0
            
            h, w = frame.shape[:2]
            if w != self.width or h != self.height:
                frame = cv2.resize(frame, (self.width, self.height), interpolation=cv2.INTER_NEAREST)
            
            # Put RAW numpy array in queue (NO JPEG encoding here!)
            # This saves ~5-10ms per frame
            try:
                self._frame_queue.put_nowait(frame.copy())
            except queue.Full:
                try:
                    self._frame_queue.get_nowait()
                    self._frame_queue.put_nowait(frame.copy())
                except Exception:
                    pass
            
            last_capture = now
            frame_count += 1
            
            if frame_count % 30 == 0:
                qsize = self._frame_queue.qsize()
                cap_ts = time.time()
                cap_iso = time.strftime("%H:%M:%S", time.localtime(cap_ts)) + f".{int((cap_ts % 1) * 1000):03d}"
                self._restore_stderr()
                print(f"📷 [{cap_iso}] Captured {frame_count} frames, queue={qsize}")
                if qsize > 2:
                    print("⚠️ Queue backing up! Consumer too slow.")
                self._suppress_stderr()
        
        self._restore_stderr()
        self._capture.release()
        print("🛑 Capture stopped")


# ============================================================================
# Web Server
# ============================================================================

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Real-time Motion Analysis</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Consolas', monospace; background: #0a0a1a; color: #eee; overflow: hidden; }
        .container { display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 150px; height: 100vh; gap: 6px; padding: 6px; }
        .panel { background: #111; border-radius: 6px; overflow: hidden; }
        .panel-header { background: #1a1a2e; padding: 5px 10px; font-size: 10px; color: #00d9ff; text-transform: uppercase; display: flex; justify-content: space-between; align-items: center; }
        .video-panel { position: relative; }
        #video-container { width: 100%; height: calc(100% - 26px); position: relative; background: #000; }
        #video-frame { width: 100%; height: 100%; object-fit: contain; image-rendering: pixelated; }
        #svg-overlay { position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; }
        .svg-panel { display: flex; flex-direction: column; }
        #svg-standalone { flex: 1; background: #1a1a2e; }
        #svg-standalone svg { width: 100%; height: 100%; }
        .dsl-panel { grid-column: span 2; }
        #dsl-output { height: calc(100% - 26px); overflow-y: auto; padding: 6px; font-size: 9px; line-height: 1.2; white-space: pre-wrap; color: #888; }
        #dsl-output .frame-header { color: #00d9ff; font-weight: bold; }
        #dsl-output .event { color: #00ff88; }
        #dsl-output .blob { color: #4ecdc4; }
        .stats { display: flex; gap: 12px; font-size: 9px; }
        .stat { color: #888; }
        .stat-value { color: #00ff88; margin-left: 3px; }
        .stat-value.warn { color: #ff0; }
        .stat-value.error { color: #f00; }
        .status-dot { width: 6px; height: 6px; border-radius: 50%; background: #f00; }
        .status-dot.connected { background: #0f0; }
        .controls { display: flex; gap: 4px; align-items: center; }
        button { background: #333; border: none; color: #fff; padding: 3px 6px; border-radius: 3px; cursor: pointer; font-size: 9px; }
        button:hover { background: #555; }
        button.copied { background: #0a0; }
        button.active { background: #a00; }
        #motion-bar { width: 60px; height: 4px; background: #333; border-radius: 2px; overflow: hidden; }
        #motion-fill { height: 100%; background: linear-gradient(90deg, #0f0, #ff0, #f00); width: 0%; }
        .diag { font-size: 8px; color: #555; margin-left: 6px; }
        .diag-panel { position: fixed; bottom: 6px; right: 6px; background: #111; border: 1px solid #333; border-radius: 4px; padding: 8px; font-size: 9px; max-width: 320px; display: none; z-index: 100; }
        .diag-panel.show { display: block; }
        .diag-panel h4 { color: #00d9ff; margin-bottom: 6px; font-size: 10px; }
        .diag-row { display: flex; justify-content: space-between; margin: 2px 0; }
        .diag-label { color: #888; }
        .diag-value { color: #0f0; font-family: monospace; }
        .diag-value.warn { color: #ff0; }
        .diag-value.error { color: #f00; }
    </style>
</head>
<body>
    <div class="container">
        <div class="panel video-panel">
            <div class="panel-header">
                <span>📹 Live Video</span>
                <div class="controls">
                    <div class="status-dot" id="status-dot"></div>
                    <span id="fps-counter">0 FPS</span>
                    <span class="diag" id="latency">render: 0ms</span>
                    <span class="diag" id="msg-size">0KB</span>
                </div>
            </div>
            <div id="video-container">
                <img id="video-frame" alt="">
                <div id="svg-overlay"></div>
            </div>
        </div>
        
        <div class="panel svg-panel">
            <div class="panel-header">
                <span>🎯 Analysis</span>
                <div class="stats">
                    <span class="stat">M:<span class="stat-value" id="motion-value">0%</span></span>
                    <span class="stat">O:<span class="stat-value" id="objects-value">0</span></span>
                    <span class="stat">F:<span class="stat-value" id="frame-value">0</span></span>
                    <span class="stat">Q:<span class="stat-value" id="queue-value">-</span></span>
                </div>
            </div>
            <div id="svg-standalone"></div>
        </div>
        
        <div class="panel dsl-panel">
            <div class="panel-header">
                <span>📝 DSL Stream</span>
                <div class="controls">
                    <div id="motion-bar"><div id="motion-fill"></div></div>
                    <button onclick="clearDSL()">Clear</button>
                    <button onclick="togglePause()" id="pause-btn">Pause</button>
                    <button onclick="copyLogs()" id="copy-btn">Copy</button>
                    <button onclick="copyDiagnostics()" id="diag-btn">📊 Diag</button>
                    <button onclick="downloadDSL()">Save</button>
                </div>
            </div>
            <div id="dsl-output"></div>
        </div>
    </div>
    
    <div class="diag-panel" id="diag-panel">
        <h4>📊 Diagnostics (last 60s)</h4>
        <div class="diag-row"><span class="diag-label">Frames received:</span><span class="diag-value" id="d-frames">0</span></div>
        <div class="diag-row"><span class="diag-label">Avg FPS:</span><span class="diag-value" id="d-fps">0</span></div>
        <div class="diag-row"><span class="diag-label">Avg render (ms):</span><span class="diag-value" id="d-render">0</span></div>
        <div class="diag-row"><span class="diag-label">Max render (ms):</span><span class="diag-value" id="d-render-max">0</span></div>
        <div class="diag-row"><span class="diag-label">Avg msg size (KB):</span><span class="diag-value" id="d-size">0</span></div>
        <div class="diag-row"><span class="diag-label">Total data (MB):</span><span class="diag-value" id="d-total">0</span></div>
        <div class="diag-row"><span class="diag-label">Dropped frames:</span><span class="diag-value" id="d-dropped">0</span></div>
        <div class="diag-row"><span class="diag-label">WS reconnects:</span><span class="diag-value" id="d-reconnects">0</span></div>
        <div class="diag-row"><span class="diag-label">Avg motion %:</span><span class="diag-value" id="d-motion">0</span></div>
        <div class="diag-row"><span class="diag-label">Max motion %:</span><span class="diag-value" id="d-motion-max">0</span></div>
        <div class="diag-row"><span class="diag-label">Avg objects:</span><span class="diag-value" id="d-objects">0</span></div>
        <div class="diag-row"><span class="diag-label">Session time:</span><span class="diag-value" id="d-session">0s</span></div>
        <div style="margin-top:8px;"><button onclick="copyDiagnosticsJSON()">Copy JSON</button> <button onclick="toggleDiag()">Close</button></div>
    </div>
    
    <script>
        const videoFrame = document.getElementById('video-frame');
        const svgOverlay = document.getElementById('svg-overlay');
        const svgStandalone = document.getElementById('svg-standalone');
        const dslOutput = document.getElementById('dsl-output');
        const statusDot = document.getElementById('status-dot');
        const motionValue = document.getElementById('motion-value');
        const objectsValue = document.getElementById('objects-value');
        const frameValue = document.getElementById('frame-value');
        const motionFill = document.getElementById('motion-fill');
        const fpsCounter = document.getElementById('fps-counter');
        const latencyEl = document.getElementById('latency');
        const pauseBtn = document.getElementById('pause-btn');
        const copyBtn = document.getElementById('copy-btn');
        
        let paused = false;
        let lastFpsTime = Date.now();
        let fpsFrames = 0;
        let allDSL = [];
        let lastSvg = '';
        let wsReconnects = 0;
        const sessionStart = Date.now();
        
        // Diagnostics data
        const diag = {
            frames: 0,
            renderTimes: [],
            msgSizes: [],
            motions: [],
            objects: [],
            dropped: 0,
            lastFrameNum: 0,
            totalBytes: 0,
        };
        
        const msgSizeEl = document.getElementById('msg-size');
        const queueValue = document.getElementById('queue-value');
        const diagPanel = document.getElementById('diag-panel');
        
        // Preload image for faster rendering
        const imgBuffer = new Image();
        imgBuffer.onload = () => { videoFrame.src = imgBuffer.src; };
        
        // WebSocket connection
        let ws;
        function connectWS() {
            ws = new WebSocket(`ws://${window.location.host}/ws`);
            
            ws.onopen = () => {
                statusDot.classList.add('connected');
                console.log('[WS] Connected');
            };
            
            ws.onclose = () => {
                statusDot.classList.remove('connected');
                console.log('[WS] Disconnected, reconnecting in 2s...');
                wsReconnects++;
                setTimeout(connectWS, 2000);
            };
            
            ws.onerror = (e) => {
                console.error('[WS] Error:', e);
            };
            
            ws.onmessage = handleMessage;
        }
        connectWS();
        
        function handleMessage(event) {
            if (paused) { diag.dropped++; return; }
            const t0 = performance.now();
            const msgSize = event.data.length;
            
            const data = JSON.parse(event.data);
            
            // Handle both formats
            const img = data.img || data.jpeg_base64;
            const svg = data.svg || data.svg_overlay;
            const dsl = data.dsl || data.dsl_text;
            const frameNum = data.f || data.frame_num || 0;
            const motion = data.m || data.motion_percent || 0;
            const objects = data.obj || data.objects || [];
            const serverQueue = data.q || data.queue || null;
            
            // Detect dropped frames
            if (diag.lastFrameNum > 0 && frameNum > diag.lastFrameNum + 1) {
                diag.dropped += frameNum - diag.lastFrameNum - 1;
            }
            diag.lastFrameNum = frameNum;
            
            // Update video (use buffer for smoother rendering)
            if (img) {
                imgBuffer.src = 'data:image/jpeg;base64,' + img;
            }
            
            // Update SVG only if changed
            if (svg && svg !== lastSvg) {
                svgOverlay.innerHTML = svg;
                svgStandalone.innerHTML = svg;
                lastSvg = svg;
            }
            
            // Update DSL (batch updates)
            if (dsl) {
                allDSL.push(dsl);
                if (allDSL.length % 3 === 0 || dsl.includes('EVENT')) {
                    const recent = allDSL.slice(-20).reverse();
                    dslOutput.innerHTML = recent.map(formatDSL).join('');
                }
            }
            
            // Update stats
            motionValue.textContent = motion.toFixed(1) + '%';
            objectsValue.textContent = objects.length;
            frameValue.textContent = frameNum;
            motionFill.style.width = Math.min(100, motion * 2) + '%';
            if (serverQueue !== null) queueValue.textContent = serverQueue;
            
            // FPS counter
            fpsFrames++;
            diag.frames++;
            const now = Date.now();
            if (now - lastFpsTime >= 1000) {
                fpsCounter.textContent = fpsFrames + ' FPS';
                fpsFrames = 0;
                lastFpsTime = now;
            }
            
            // Diagnostics
            const renderMs = performance.now() - t0;
            diag.renderTimes.push(renderMs);
            diag.msgSizes.push(msgSize);
            diag.motions.push(motion);
            diag.objects.push(objects.length);
            diag.totalBytes += msgSize;
            
            // Keep last 60s of data (assuming ~2-10 FPS)
            const maxSamples = 600;
            if (diag.renderTimes.length > maxSamples) {
                diag.renderTimes.shift();
                diag.msgSizes.shift();
                diag.motions.shift();
                diag.objects.shift();
            }
            
            // Update UI diagnostics
            latencyEl.textContent = 'render: ' + renderMs.toFixed(0) + 'ms';
            msgSizeEl.textContent = (msgSize / 1024).toFixed(1) + 'KB';
            
            // Color code latency
            latencyEl.style.color = renderMs > 50 ? '#f00' : renderMs > 20 ? '#ff0' : '#555';
        }
        
        function formatDSL(text) {
            return '<div>' + text
                .replace(/(FRAME \\d+ @ [\\d:.]+)/g, '<span class="frame-header">$1</span>')
                .replace(/(EVENT [^\\n]+)/g, '<span class="event">$1</span>')
                .replace(/(BLOB [^\\n]+)/g, '<span class="blob">$1</span>')
                + '</div>';
        }
        
        function clearDSL() {
            dslOutput.innerHTML = '';
            allDSL = [];
        }
        
        function togglePause() {
            paused = !paused;
            pauseBtn.textContent = paused ? 'Resume' : 'Pause';
            pauseBtn.style.background = paused ? '#a00' : '#333';
        }
        
        function copyLogs() {
            const text = allDSL.join('\\n\\n');
            navigator.clipboard.writeText(text).then(() => {
                copyBtn.textContent = 'Copied!';
                copyBtn.classList.add('copied');
                setTimeout(() => {
                    copyBtn.textContent = 'Copy';
                    copyBtn.classList.remove('copied');
                }, 1500);
            }).catch(err => {
                console.error('Copy failed:', err);
                // Fallback
                const ta = document.createElement('textarea');
                ta.value = text;
                document.body.appendChild(ta);
                ta.select();
                document.execCommand('copy');
                document.body.removeChild(ta);
                copyBtn.textContent = 'Copied!';
                setTimeout(() => copyBtn.textContent = 'Copy', 1500);
            });
        }
        
        function downloadDSL() {
            const blob = new Blob([allDSL.join('\\n\\n')], {type: 'text/plain'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'motion_analysis.dsl';
            a.click();
            URL.revokeObjectURL(url);
        }
        
        // Diagnostics functions
        function avg(arr) { return arr.length ? arr.reduce((a,b) => a+b, 0) / arr.length : 0; }
        function maxVal(arr) { return arr.length ? Math.max(...arr) : 0; }
        
        function getDiagnostics() {
            const sessionSec = (Date.now() - sessionStart) / 1000;
            return {
                timestamp: new Date().toISOString(),
                session_seconds: sessionSec.toFixed(1),
                frames_received: diag.frames,
                avg_fps: (diag.frames / Math.max(1, sessionSec)).toFixed(2),
                avg_render_ms: avg(diag.renderTimes).toFixed(2),
                max_render_ms: maxVal(diag.renderTimes).toFixed(2),
                avg_msg_size_kb: (avg(diag.msgSizes) / 1024).toFixed(2),
                total_data_mb: (diag.totalBytes / 1024 / 1024).toFixed(2),
                dropped_frames: diag.dropped,
                ws_reconnects: wsReconnects,
                avg_motion_percent: avg(diag.motions).toFixed(2),
                max_motion_percent: maxVal(diag.motions).toFixed(2),
                avg_objects: avg(diag.objects).toFixed(2),
                dsl_entries: allDSL.length,
                user_agent: navigator.userAgent,
                screen: screen.width + 'x' + screen.height,
                url: window.location.href,
            };
        }
        
        function updateDiagPanel() {
            const d = getDiagnostics();
            document.getElementById('d-frames').textContent = d.frames_received;
            document.getElementById('d-fps').textContent = d.avg_fps;
            document.getElementById('d-render').textContent = d.avg_render_ms;
            document.getElementById('d-render-max').textContent = d.max_render_ms;
            document.getElementById('d-size').textContent = d.avg_msg_size_kb;
            document.getElementById('d-total').textContent = d.total_data_mb;
            document.getElementById('d-dropped').textContent = d.dropped_frames;
            document.getElementById('d-reconnects').textContent = d.ws_reconnects;
            document.getElementById('d-motion').textContent = d.avg_motion_percent;
            document.getElementById('d-motion-max').textContent = d.max_motion_percent;
            document.getElementById('d-objects').textContent = d.avg_objects;
            document.getElementById('d-session').textContent = d.session_seconds + 's';
            
            // Color code warnings
            const renderEl = document.getElementById('d-render');
            renderEl.className = 'diag-value' + (parseFloat(d.avg_render_ms) > 30 ? ' error' : parseFloat(d.avg_render_ms) > 15 ? ' warn' : '');
            
            const droppedEl = document.getElementById('d-dropped');
            droppedEl.className = 'diag-value' + (d.dropped_frames > 10 ? ' error' : d.dropped_frames > 0 ? ' warn' : '');
        }
        
        function toggleDiag() {
            diagPanel.classList.toggle('show');
            if (diagPanel.classList.contains('show')) updateDiagPanel();
        }
        
        function copyDiagnostics() { toggleDiag(); }
        
        function copyDiagnosticsJSON() {
            const d = getDiagnostics();
            const json = JSON.stringify(d, null, 2);
            navigator.clipboard.writeText(json).then(() => {
                alert('Diagnostics copied to clipboard!');
            }).catch(() => {
                const ta = document.createElement('textarea');
                ta.value = json;
                document.body.appendChild(ta);
                ta.select();
                document.execCommand('copy');
                document.body.removeChild(ta);
                alert('Diagnostics copied!');
            });
        }
        
        // Update diagnostics panel every second when visible
        setInterval(() => { if (diagPanel.classList.contains('show')) updateDiagPanel(); }, 1000);
        
        // Log diagnostics to console every 30s
        setInterval(() => { console.log('[DIAG]', getDiagnostics()); }, 30000);
    </script>
</body>
</html>'''


class RealtimeVisualizerServer:
    """
    Web server for real-time visualization.
    """
    
    def __init__(
        self,
        rtsp_url: str,
        host: str = "0.0.0.0",
        port: int = 8080,
        fps: float = 2.0,
        width: int = 640,
        height: int = 480,
        transport: str = "tcp",
        backend: str = "opencv",
    ):
        self.rtsp_url = rtsp_url
        self.host = host
        self.port = port
        self.fps = fps
        self.width = width
        self.height = height
        self.transport = transport
        self.backend = backend
        
        self._capture = None
        self._processor = None
        self._executor = None
        self._running = False
        self._clients = set()
    
    def start(self):
        """Start the visualization server."""
        try:
            import asyncio
            import concurrent.futures
            from aiohttp import web
        except ImportError:
            logger.error("aiohttp required: pip install aiohttp")
            return
        
        # Initialize components
        self._capture = RTSPCapture(
            self.rtsp_url,
            transport=self.transport,
            backend=self.backend,
            fps=self.fps,
            width=self.width,
            height=self.height,
        )
        self._processor = RealtimeProcessor(
            width=self.width,
            height=self.height,
        )
        # Thread pool for CV2 operations (releases GIL)
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        
        # Start capture
        self._capture.start()
        self._running = True
        
        # Create web app
        app = web.Application()
        app.router.add_get('/', self._handle_index)
        app.router.add_get('/ws', self._handle_websocket)
        
        print(f"🚀 Real-time Visualizer starting at http://{self.host}:{self.port}")
        print(f"📹 RTSP: {self.rtsp_url}")
        print(f"⚡ FPS: {self.fps}")
        print(f"📐 Size: {self.width}x{self.height}")
        print("\nOpen in browser to view live analysis!")
        
        # Run server with reuse_address=True
        web.run_app(app, host=self.host, port=self.port, print=None, reuse_address=True)
    
    async def _handle_index(self, request):
        """Serve main HTML page."""
        from aiohttp import web
        return web.Response(text=HTML_TEMPLATE, content_type='text/html')
    
    async def _handle_websocket(self, request):
        """Handle WebSocket connections."""
        from aiohttp import web
        import asyncio
        
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self._clients.add(ws)
        print(f"Client connected ({len(self._clients)} total)")
        
        frame_interval = 1.0 / max(0.5, self.fps)
        last_frame_time = 0
        
        frame_times = []
        
        try:
            while self._running and not ws.closed:
                try:
                    # Rate limit
                    now = time.time()
                    if now - last_frame_time < frame_interval:
                        await asyncio.sleep(0.01)
                        continue
                    
                    t0 = time.time()
                    
                    # Get frame
                    frame_jpeg = self._capture.get_frame(timeout=0.3)
                    t1 = time.time()
                    
                    if frame_jpeg is None:
                        await asyncio.sleep(0.02)
                        continue
                    
                    # Process frame in thread pool (non-blocking!)
                    loop = asyncio.get_event_loop()
                    frame_data = await loop.run_in_executor(
                        self._executor, 
                        self._processor.process_frame, 
                        frame_jpeg
                    )
                    t2 = time.time()
                    
                    # Send to client (add queue size for diagnostics)
                    json_data = json.loads(frame_data.to_json())
                    json_data["q"] = self._capture._frame_queue.qsize()
                    json_str = json.dumps(json_data, separators=(',', ':'))
                    t3 = time.time()
                    
                    try:
                        await asyncio.wait_for(ws.send_str(json_str), timeout=0.5)
                        last_frame_time = now
                        t4 = time.time()
                        
                        # Log timing every 10 frames
                        frame_times.append({
                            'capture': (t1-t0)*1000,
                            'process': (t2-t1)*1000,
                            'json': (t3-t2)*1000,
                            'send': (t4-t3)*1000,
                            'total': (t4-t0)*1000,
                            'size_kb': len(json_str)/1024,
                        })
                        
                        if len(frame_times) >= 10:
                            avg = {k: sum(f[k] for f in frame_times)/len(frame_times) for k in frame_times[0]}
                            max_vals = {k: max(f[k] for f in frame_times) for k in frame_times[0]}
                            
                            # Identify bottleneck
                            bottleneck = max(avg, key=lambda k: avg[k] if k != 'total' and k != 'size_kb' else 0)
                            
                            print(f"⏱️ Avg: cap={avg['capture']:.0f}ms proc={avg['process']:.0f}ms json={avg['json']:.0f}ms send={avg['send']:.0f}ms | total={avg['total']:.0f}ms | {avg['size_kb']:.0f}KB")
                            
                            # Warn if bottleneck detected
                            if max_vals['capture'] > 100:
                                print(f"   ⚠️ BOTTLENECK: capture (max={max_vals['capture']:.0f}ms) - RTSP stream slow or network issue")
                            if max_vals['process'] > 50:
                                print(f"   ⚠️ BOTTLENECK: process (max={max_vals['process']:.0f}ms) - CPU overloaded")
                            if max_vals['send'] > 50:
                                print(f"   ⚠️ BOTTLENECK: send (max={max_vals['send']:.0f}ms) - WebSocket/network slow")
                            
                            frame_times.clear()
                            
                    except asyncio.TimeoutError:
                        print("⚠️ WebSocket send timeout")
                        break
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.debug(f"Frame error: {e}")
                    await asyncio.sleep(0.05)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"WebSocket error: {e}")
        finally:
            self._clients.discard(ws)
            print(f"Client disconnected ({len(self._clients)} remaining)")
        
        return ws
    
    def stop(self):
        """Stop the server."""
        self._running = False
        if self._capture:
            self._capture.stop()


# ============================================================================
# Simple HTTP Server (fallback without aiohttp)
# ============================================================================

class SimpleVisualizerServer:
    """
    Simple HTTP server using only standard library.
    Uses Server-Sent Events instead of WebSocket.
    """
    
    def __init__(
        self,
        rtsp_url: str,
        host: str = "0.0.0.0",
        port: int = 8080,
        fps: float = 2.0,
    ):
        self.rtsp_url = rtsp_url
        self.host = host
        self.port = port
        self.fps = fps
        
        self._capture = None
        self._processor = None
        self._running = False
    
    def start(self):
        """Start simple HTTP server."""
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import urllib.parse
        
        capture = RTSPCapture(self.rtsp_url, fps=self.fps)
        processor = RealtimeProcessor()
        capture.start()
        
        parent = self
        
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/':
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html')
                    self.end_headers()
                    # Modify HTML to use SSE instead of WebSocket
                    html = HTML_TEMPLATE.replace(
                        "new WebSocket(`ws://${window.location.host}/ws`)",
                        "new EventSource('/stream')"
                    ).replace(
                        "ws.onmessage = (event)",
                        "ws.onmessage = (event)"
                    )
                    self.wfile.write(html.encode())
                    
                elif self.path == '/stream':
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/event-stream')
                    self.send_header('Cache-Control', 'no-cache')
                    self.send_header('Connection', 'keep-alive')
                    self.end_headers()
                    
                    try:
                        while parent._running:
                            frame_jpeg = capture.get_frame(timeout=1.0)
                            if frame_jpeg:
                                frame_data = processor.process_frame(frame_jpeg)
                                self.wfile.write(f"data: {frame_data.to_json()}\n\n".encode())
                                self.wfile.flush()
                    except Exception:
                        pass
                else:
                    self.send_error(404)
            
            def log_message(self, format, *args):
                pass  # Suppress logs
        
        self._running = True
        server = HTTPServer((self.host, self.port), Handler)
        
        print(f"🚀 Simple Visualizer at http://{self.host}:{self.port}")
        print(f"📹 RTSP: {self.rtsp_url}")
        
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self._running = False
            capture.stop()


# ============================================================================
# HLS Visualizer Server (ffmpeg + WebSocket overlay)
# ============================================================================

HLS_HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>HLS Motion Analysis</title>
    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Consolas', monospace; background: #0a0a1a; color: #eee; }
        .container { display: grid; grid-template-columns: 2fr 1fr; grid-template-rows: 1fr 150px; height: 100vh; gap: 8px; padding: 8px; }
        .video-container { position: relative; background: #111; border-radius: 6px; overflow: hidden; display: flex; align-items: center; justify-content: center; }
        .video-wrapper { position: relative; max-width: 100%; max-height: 100%; }
        .video-wrapper video { display: block; max-width: 100%; max-height: 100%; }
        #svg-overlay { position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; }
        #svg-overlay svg { width: 100%; height: 100%; }
        .panel { background: #111; border-radius: 6px; padding: 12px; overflow: auto; }
        .panel-header { color: #00d9ff; font-size: 11px; text-transform: uppercase; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; }
        .stats { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px; }
        .stat { background: #1a1a2e; padding: 8px; border-radius: 4px; }
        .stat-label { font-size: 9px; color: #888; }
        .stat-value { font-size: 16px; color: #00ff88; }
        .status-dot { width: 8px; height: 8px; border-radius: 50%; background: #f44; display: inline-block; }
        .status-dot.connected { background: #0f0; }
        .status-dot.hls { background: #ff0; }
        #dsl-output { font-size: 10px; white-space: pre-wrap; max-height: 250px; overflow-y: auto; }
        .frame-header { color: #00d9ff; }
        .event { color: #ff6b6b; }
        .blob { color: #4ecdc4; }
        .controls { display: flex; gap: 6px; margin-top: 8px; flex-wrap: wrap; }
        .controls button { padding: 6px 12px; border: none; border-radius: 4px; cursor: pointer; background: #333; color: #fff; font-size: 10px; }
        .controls button:hover { background: #555; }
        .controls button.active { background: #0a0; }
        .motion-bar { height: 5px; background: #333; border-radius: 3px; margin-top: 8px; }
        .motion-fill { height: 100%; background: linear-gradient(90deg, #00ff88, #ff6b6b); border-radius: 3px; }
        .debug { font-size: 9px; color: #555; margin-top: 8px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="video-container" id="video-container">
            <div class="video-wrapper" id="video-wrapper">
                <video id="video" autoplay muted playsinline></video>
                <div id="svg-overlay"></div>
            </div>
        </div>
        <div class="panel">
            <div class="panel-header">
                <span>📊 Analysis</span>
                <span><span class="status-dot" id="status-dot"></span> <span id="fps-counter">0 FPS</span></span>
            </div>
            <div class="stats">
                <div class="stat"><div class="stat-label">Motion</div><div class="stat-value" id="motion-value">0%</div></div>
                <div class="stat"><div class="stat-label">Objects</div><div class="stat-value" id="objects-value">0</div></div>
                <div class="stat"><div class="stat-label">Frame</div><div class="stat-value" id="frame-value">0</div></div>
                <div class="stat"><div class="stat-label">Mode</div><div class="stat-value" style="color:#ff0;">HLS</div></div>
            </div>
            <div class="motion-bar"><div class="motion-fill" id="motion-fill" style="width:0%"></div></div>
            <div class="controls">
                <button onclick="toggleOverlay()" id="overlay-btn">Overlay ON</button>
                <button onclick="toggleSyncMode()" id="sync-btn">Sync: RT</button>
                <button onclick="copyLogs()">Copy Logs</button>
                <button onclick="downloadDSL()">Save DSL</button>
            </div>
            <div class="controls" style="margin-top:4px;">
                <span style="font-size:9px;color:#888;">Delay:</span>
                <input type="range" id="delay-slider" min="0" max="5000" value="0" style="width:80px;height:12px;" onchange="updateDelay(this.value)">
                <span id="delay-value" style="font-size:9px;color:#0f0;">0ms</span>
            </div>
            <div class="debug" id="debug-info">Video: -</div>
        </div>
        <div class="panel" style="grid-column: span 2;">
            <div class="panel-header">
                <span>📝 DSL Metadata Stream</span>
                <button onclick="clearDSL()" style="padding:4px 8px;font-size:9px;background:#333;border:none;color:#fff;border-radius:3px;cursor:pointer;">Clear</button>
            </div>
            <div id="dsl-output"></div>
        </div>
    </div>
    <script>
        const video = document.getElementById('video');
        const videoWrapper = document.getElementById('video-wrapper');
        const svgOverlay = document.getElementById('svg-overlay');
        const statusDot = document.getElementById('status-dot');
        const motionValue = document.getElementById('motion-value');
        const objectsValue = document.getElementById('objects-value');
        const frameValue = document.getElementById('frame-value');
        const motionFill = document.getElementById('motion-fill');
        const fpsCounter = document.getElementById('fps-counter');
        const dslOutput = document.getElementById('dsl-output');
        const debugInfo = document.getElementById('debug-info');
        const overlayBtn = document.getElementById('overlay-btn');
        
        let overlayVisible = true;
        let allDSL = [];
        let fpsFrames = 0;
        let lastFpsTime = Date.now();
        let analysisWidth = 320;
        let analysisHeight = 240;
        
        // Sync mode: 'realtime' = no delay, 'buffered' = try to sync with HLS
        let syncMode = 'realtime';  // Start with realtime - user can adjust
        let hlsDelayMs = 0;  // Will be measured
        let hlsLatencyEstimate = 0;
        
        // Overlay buffer for sync
        const overlayBuffer = [];
        let lastServerTs = 0;
        
        // Update debug info
        function updateDebugInfo() {
            const vw = video.videoWidth || 0;
            const vh = video.videoHeight || 0;
            const bufLen = overlayBuffer.length;
            const latency = hlsLatencyEstimate ? hlsLatencyEstimate.toFixed(1) + 's' : '?';
            debugInfo.textContent = 'Video: ' + vw + 'x' + vh + ' | Buf: ' + bufLen + ' | HLS lag: ' + latency + ' | Mode: ' + syncMode;
        }
        
        video.addEventListener('loadedmetadata', updateDebugInfo);
        video.addEventListener('resize', updateDebugInfo);
        
        // Sync system using HLS program_date_time markers
        let hlsProgramDateTime = null;  // From HLS segment
        let hlsVideoTime = 0;
        let measuredLatencyMs = 0;
        
        // Fetch sync info from server periodically
        async function fetchSyncInfo() {
            try {
                const resp = await fetch('/sync');
                const sync = await resp.json();
                
                // Calculate latency: server_time - video's program_date_time
                if (sync.segments && sync.segments.length > 0) {
                    const latestSeg = sync.segments[sync.segments.length - 1];
                    const segTime = new Date(latestSeg.datetime).getTime();
                    const serverTime = sync.server_time * 1000;
                    
                    // HLS latency = time since segment was created
                    const segAge = serverTime - segTime;
                    hlsLatencyEstimate = segAge / 1000;
                }
                
                return sync;
            } catch (e) {
                console.warn('Sync fetch failed:', e);
                return null;
            }
        }
        
        // Initial sync
        fetchSyncInfo();
        setInterval(fetchSyncInfo, 2000);
        
        // Use hls.js programDateTime if available
        video.addEventListener('timeupdate', () => {
            if (typeof hls !== 'undefined' && hls.playingDate) {
                hlsProgramDateTime = hls.playingDate.getTime();
                const now = Date.now();
                measuredLatencyMs = now - hlsProgramDateTime;
                hlsLatencyEstimate = measuredLatencyMs / 1000;
            }
        });
        
        // Apply overlay immediately (realtime mode) or from buffer (sync mode)
        function applyOverlay(item) {
            if (!overlayVisible) return;
            
            let svgContent = item.svg;
            if (svgContent && !svgContent.includes('viewBox')) {
                svgContent = svgContent.replace('<svg', '<svg viewBox="0 0 ' + analysisWidth + ' ' + analysisHeight + '" preserveAspectRatio="xMidYMid meet"');
            }
            if (svgContent) {
                svgOverlay.innerHTML = svgContent;
            }
            
            motionValue.textContent = item.motion.toFixed(1) + '%';
            objectsValue.textContent = item.objects;
            frameValue.textContent = item.frame + ' @ ' + item.ts_iso;
            motionFill.style.width = Math.min(100, item.motion * 2) + '%';
        }
        
        // Process buffer in sync mode
        function processOverlayBuffer() {
            if (syncMode === 'realtime' || overlayBuffer.length === 0) return;
            
            // In buffered mode, delay overlay by hlsDelayMs
            const now = Date.now();
            const targetTime = now - hlsDelayMs;
            
            while (overlayBuffer.length > 1 && overlayBuffer[0].clientTs < targetTime) {
                overlayBuffer.shift();
            }
            
            if (overlayBuffer.length > 0) {
                applyOverlay(overlayBuffer[0]);
            }
            
            updateDebugInfo();
        }
        
        setInterval(processOverlayBuffer, 50);
        
        // HLS Video - ultra low latency settings
        const hlsSrc = '/hls/index.m3u8';
        if (Hls.isSupported()) {
            const hls = new Hls({
                lowLatencyMode: true,
                liveSyncDuration: 0.5,      // Sync to 0.5s from live edge
                liveMaxLatencyDuration: 2,   // Max 2s behind live
                liveDurationInfinity: true,
                maxBufferLength: 1,          // Only 1s buffer
                maxMaxBufferLength: 2,
                maxBufferSize: 0,            // No size limit
                maxBufferHole: 0.5,
                highBufferWatchdogPeriod: 1,
                enableWorker: true,
            });
            hls.loadSource(hlsSrc);
            hls.attachMedia(video);
            hls.on(Hls.Events.MANIFEST_PARSED, () => {
                video.play();
                statusDot.classList.add('hls');
            });
            hls.on(Hls.Events.ERROR, (e, data) => {
                console.error('HLS error:', data);
                if (data.fatal) {
                    setTimeout(() => hls.loadSource(hlsSrc), 2000);
                }
            });
        } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
            video.src = hlsSrc;
            video.addEventListener('loadedmetadata', () => video.play());
            statusDot.classList.add('hls');
        }
        
        // WebSocket for overlay/metadata only
        let ws;
        function connectWS() {
            ws = new WebSocket('ws://' + window.location.host + '/ws');
            
            ws.onopen = () => {
                statusDot.classList.add('connected');
                console.log('[WS] Connected (overlay)');
            };
            
            ws.onclose = () => {
                statusDot.classList.remove('connected');
                console.log('[WS] Disconnected, reconnecting...');
                setTimeout(connectWS, 2000);
            };
            
            ws.onmessage = handleMessage;
        }
        connectWS();
        
        function handleMessage(event) {
            const clientNow = Date.now();
            const data = JSON.parse(event.data);
            
            // Get analysis dimensions from server
            if (data.w) analysisWidth = data.w;
            if (data.h) analysisHeight = data.h;
            
            const svg = data.svg || data.data?.svg;
            const dsl = data.dsl || data.data?.dsl;
            const frameNum = data.f || data.frame || 0;
            const motion = data.m || data.motion || 0;
            const objects = data.obj || data.objects || [];
            const serverTs = data.ts || 0;
            const tsIso = data.ts_iso || '';
            
            // Calculate HLS latency estimate from server timestamp
            if (serverTs) {
                const serverTsMs = serverTs * 1000;
                const drift = clientNow - serverTsMs;
                // Estimate: overlay arrives ~instantly, video is delayed by HLS
                // So if we see overlay at clientNow, video will show it at clientNow + hlsDelay
                hlsLatencyEstimate = drift / 1000;  // Convert to seconds for display
                lastServerTs = serverTs;
            }
            
            const item = {
                clientTs: clientNow,
                serverTs: serverTs,
                svg: svg,
                frame: frameNum,
                motion: motion,
                objects: Array.isArray(objects) ? objects.length : 0,
                ts_iso: tsIso,
            };
            
            // In REALTIME mode: apply overlay immediately (overlay leads video)
            // In BUFFERED mode: store in buffer for delayed playback
            if (syncMode === 'realtime') {
                applyOverlay(item);
            } else {
                overlayBuffer.push(item);
                while (overlayBuffer.length > 100) {
                    overlayBuffer.shift();
                }
            }
            
            // Update DSL immediately
            if (dsl) {
                allDSL.push(dsl);
                if (allDSL.length % 2 === 0) {
                    const recent = allDSL.slice(-12).reverse();
                    dslOutput.innerHTML = recent.map(formatDSL).join('');
                }
            }
            
            // FPS counter
            fpsFrames++;
            const now = Date.now();
            if (now - lastFpsTime >= 1000) {
                fpsCounter.textContent = fpsFrames + ' WS/s';
                fpsFrames = 0;
                lastFpsTime = now;
                updateDebugInfo();
            }
        }
        
        function formatDSL(text) {
            return '<div>' + text
                .replace(/(FRAME \\d+ @ [\\d:.]+)/g, '<span class="frame-header">$1</span>')
                .replace(/(EVENT [^\\n]+)/g, '<span class="event">$1</span>')
                .replace(/(BLOB [^\\n]+)/g, '<span class="blob">$1</span>')
                + '</div>';
        }
        
        function toggleOverlay() {
            overlayVisible = !overlayVisible;
            svgOverlay.style.display = overlayVisible ? 'block' : 'none';
            overlayBtn.textContent = overlayVisible ? 'Overlay ON' : 'Overlay OFF';
            overlayBtn.classList.toggle('active', overlayVisible);
        }
        
        const syncBtn = document.getElementById('sync-btn');
        const delaySlider = document.getElementById('delay-slider');
        const delayValue = document.getElementById('delay-value');
        
        function toggleSyncMode() {
            if (syncMode === 'realtime') {
                syncMode = 'buffered';
                // Auto-set delay based on measured latency
                const autoDelay = Math.max(0, Math.round(hlsLatencyEstimate * 1000));
                hlsDelayMs = autoDelay;
                delaySlider.value = autoDelay;
                delayValue.textContent = autoDelay + 'ms';
                syncBtn.textContent = 'Sync: BUF';
                syncBtn.style.background = '#a50';
            } else {
                syncMode = 'realtime';
                hlsDelayMs = 0;
                delaySlider.value = 0;
                delayValue.textContent = '0ms';
                syncBtn.textContent = 'Sync: RT';
                syncBtn.style.background = '#333';
            }
            updateDebugInfo();
        }
        
        function updateDelay(val) {
            hlsDelayMs = parseInt(val);
            delayValue.textContent = val + 'ms';
            if (hlsDelayMs > 0 && syncMode === 'realtime') {
                syncMode = 'buffered';
                syncBtn.textContent = 'Sync: BUF';
                syncBtn.style.background = '#a50';
            }
        }
        
        // Auto-calibrate: when HLS starts playing, measure actual latency
        let calibrated = false;
        video.addEventListener('playing', async () => {
            if (calibrated) return;
            calibrated = true;
            
            // Wait a moment for stable playback
            await new Promise(r => setTimeout(r, 1000));
            
            // Fetch sync and calculate recommended delay
            const sync = await fetchSyncInfo();
            if (sync && hlsLatencyEstimate > 0) {
                console.log('[SYNC] Measured HLS latency:', hlsLatencyEstimate.toFixed(2) + 's');
                console.log('[SYNC] Recommended delay for sync:', Math.round(hlsLatencyEstimate * 1000) + 'ms');
            }
        });
        
        function clearDSL() {
            dslOutput.innerHTML = '';
            allDSL = [];
        }
        
        function copyLogs() {
            navigator.clipboard.writeText(allDSL.join('\\n\\n')).then(() => {
                alert('Logs copied!');
            });
        }
        
        function downloadDSL() {
            const blob = new Blob([allDSL.join('\\n\\n')], {type: 'text/plain'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'motion_analysis.dsl';
            a.click();
            URL.revokeObjectURL(url);
        }
    </script>
</body>
</html>'''


class HLSVisualizerServer:
    """
    HLS-based visualizer with WebSocket overlay.
    
    Architecture:
    - ffmpeg: RTSP → HLS (index.m3u8 + .ts segments)
    - aiohttp: serves HLS files + HTML
    - WebSocket: sends only SVG/DSL metadata (no video)
    - Browser: <video> plays HLS, SVG overlay from WebSocket
    """
    
    def __init__(
        self,
        rtsp_url: str,
        host: str = "0.0.0.0",
        port: int = 8080,
        fps: float = 2.0,
        width: int = 640,
        height: int = 480,
        transport: str = "tcp",
        backend: str = "opencv",
    ):
        self.rtsp_url = rtsp_url
        self.host = host
        self.port = port
        self.fps = fps
        self.width = width
        self.height = height
        self.transport = transport
        self.backend = backend
        
        self._hls_dir = None
        self._ffmpeg_proc = None
        self._capture = None
        self._processor = None
        self._running = False
        self._clients = set()
    
    def start(self):
        """Start HLS server with WebSocket overlay."""
        import subprocess
        import shutil
        import os
        
        try:
            import asyncio
            from aiohttp import web
        except ImportError:
            print("❌ aiohttp required: pip install aiohttp")
            return
        
        # Create HLS directory
        self._hls_dir = Path(tempfile.mkdtemp(prefix=f"hls_{self.port}_"))
        print(f"📁 HLS directory: {self._hls_dir}")
        
        # Check ffmpeg
        if not shutil.which("ffmpeg"):
            print("❌ ffmpeg not found. Install with: apt install ffmpeg")
            return
        
        # Start ffmpeg for HLS with EMBEDDED TIMESTAMP for sync
        # Timestamp burned into video allows perfect overlay sync
        timestamp_filter = (
            f"scale={self.width}:{self.height}:force_original_aspect_ratio=disable,"
            f"drawtext=text='%{{pts\\:hms}}':fontsize=12:fontcolor=white@0.7:"
            f"x=5:y=h-20:box=1:boxcolor=black@0.4:boxborderw=2"
        )
        
        ffmpeg_cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "error",
            "-fflags", "+genpts+discardcorrupt+nobuffer",
            "-flags", "low_delay",
            "-rtsp_transport", "tcp",
            "-buffer_size", "512000",
            "-i", self.rtsp_url,
            "-vf", timestamp_filter,
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "zerolatency",
            "-profile:v", "baseline",
            "-level", "3.0",
            "-g", "15",
            "-keyint_min", "15",
            "-sc_threshold", "0",
            "-b:v", "300k",
            "-maxrate", "400k",
            "-bufsize", "100k",
            "-an",
            "-f", "hls",
            "-hls_time", "0.5",
            "-hls_list_size", "4",
            "-hls_flags", "delete_segments+split_by_time+program_date_time+independent_segments",
            "-hls_segment_filename", str(self._hls_dir / "seg%03d.ts"),
            str(self._hls_dir / "index.m3u8"),
        ]
        
        # Record HLS start time for sync calculation
        self._hls_start_time = time.time()
        
        print(f"🎬 Starting ffmpeg for HLS...")
        self._ffmpeg_proc = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        
        # Wait for first segment
        import time as _time
        for _ in range(30):
            if (self._hls_dir / "index.m3u8").exists():
                break
            _time.sleep(0.5)
        else:
            print("⚠️ HLS playlist not created yet, continuing anyway...")
        
        # Start RTSP capture for analysis (separate from ffmpeg)
        self._capture = RTSPCapture(
            self.rtsp_url,
            fps=self.fps,
            width=self.width,
            height=self.height,
            transport=self.transport,
            backend=self.backend,
        )
        self._processor = RealtimeProcessor(
            width=self.width,
            height=self.height,
        )
        self._capture.start()
        self._running = True
        
        # Create web app
        app = web.Application()
        app.router.add_get('/', self._handle_index)
        app.router.add_get('/ws', self._handle_websocket)
        app.router.add_get('/hls/{filename}', self._handle_hls)
        app.router.add_get('/sync', self._handle_sync)
        
        print(f"🚀 HLS Visualizer starting at http://{self.host}:{self.port}")
        print(f"📹 RTSP: {self.rtsp_url}")
        print(f"⚡ Analysis FPS: {self.fps}")
        print(f"📐 Size: {self.width}x{self.height}")
        print(f"🎥 Video: HLS (low latency)")
        print("\nOpen in browser to view live analysis!")
        
        try:
            web.run_app(app, host=self.host, port=self.port, print=None, reuse_address=True)
        finally:
            self.stop()
    
    def stop(self):
        """Stop server and cleanup."""
        self._running = False
        
        if self._capture:
            self._capture.stop()
        
        if self._ffmpeg_proc:
            self._ffmpeg_proc.terminate()
            try:
                self._ffmpeg_proc.wait(timeout=5)
            except Exception:
                self._ffmpeg_proc.kill()
        
        if self._hls_dir and self._hls_dir.exists():
            import shutil
            shutil.rmtree(self._hls_dir, ignore_errors=True)
        
        print("🛑 HLS Visualizer stopped")
    
    async def _handle_index(self, request):
        """Serve HLS HTML page."""
        from aiohttp import web
        return web.Response(text=HLS_HTML_TEMPLATE, content_type='text/html')
    
    async def _handle_hls(self, request):
        """Serve HLS files (m3u8 + ts segments)."""
        from aiohttp import web
        
        filename = request.match_info['filename']
        filepath = self._hls_dir / filename
        
        if not filepath.exists():
            return web.Response(status=404, text="Not found")
        
        content_type = 'application/vnd.apple.mpegurl' if filename.endswith('.m3u8') else 'video/mp2t'
        
        return web.FileResponse(filepath, headers={
            'Content-Type': content_type,
            'Cache-Control': 'no-cache',
            'Access-Control-Allow-Origin': '*',
        })
    
    async def _handle_sync(self, request):
        """Return sync info for HLS-overlay synchronization."""
        from aiohttp import web
        
        now = time.time()
        hls_uptime = now - self._hls_start_time if hasattr(self, '_hls_start_time') else 0
        
        # Parse m3u8 to get segment timestamps
        segments = []
        m3u8_path = self._hls_dir / "index.m3u8"
        if m3u8_path.exists():
            try:
                content = m3u8_path.read_text()
                import re
                # Extract #EXT-X-PROGRAM-DATE-TIME markers
                date_times = re.findall(r'#EXT-X-PROGRAM-DATE-TIME:(.+)', content)
                durations = re.findall(r'#EXTINF:([\d.]+)', content)
                seg_names = re.findall(r'(seg\d+\.ts)', content)
                
                for i, (dt, dur, name) in enumerate(zip(date_times, durations, seg_names)):
                    segments.append({
                        "name": name,
                        "datetime": dt,
                        "duration": float(dur),
                    })
            except Exception:
                pass
        
        sync_info = {
            "server_time": now,
            "server_time_iso": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(now)) + f".{int((now % 1) * 1000):03d}Z",
            "hls_start_time": getattr(self, '_hls_start_time', 0),
            "hls_uptime_seconds": round(hls_uptime, 2),
            "segments": segments,
            "analysis_fps": self.fps,
            "frame_count": self._processor._frame_count if self._processor else 0,
        }
        
        return web.json_response(sync_info, headers={
            'Access-Control-Allow-Origin': '*',
        })
    
    async def _handle_websocket(self, request):
        """Handle WebSocket for overlay/metadata only (no video)."""
        from aiohttp import web
        import asyncio
        
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self._clients.add(ws)
        print(f"Client connected ({len(self._clients)} total) [overlay only]")
        
        frame_interval = 1.0 / max(0.5, self.fps)
        last_frame_time = 0
        
        try:
            while self._running and not ws.closed:
                try:
                    now = time.time()
                    if now - last_frame_time < frame_interval:
                        await asyncio.sleep(0.01)
                        continue
                    
                    # Get frame for analysis
                    frame = self._capture.get_frame(timeout=0.3)
                    if frame is None:
                        await asyncio.sleep(0.02)
                        continue
                    
                    # Process frame (SVG/DSL only, no JPEG needed)
                    frame_data = self._processor.process_frame(frame)
                    
                    # Send only metadata (no img field) + dimensions + timestamp for sync
                    server_ts = time.time()
                    msg = {
                        "type": "event",
                        "event": "OverlayUpdated",
                        "f": frame_data.frame_num,
                        "ts": round(server_ts, 3),  # Unix timestamp for sync
                        "ts_iso": time.strftime("%H:%M:%S", time.localtime(server_ts)) + f".{int((server_ts % 1) * 1000):03d}",
                        "m": round(frame_data.motion_percent, 1),
                        "svg": frame_data.svg_overlay,
                        "dsl": frame_data.dsl_text,
                        "obj": frame_data.objects or [],
                        "w": self.width,
                        "h": self.height,
                    }
                    
                    await asyncio.wait_for(
                        ws.send_str(json.dumps(msg, separators=(',', ':'))),
                        timeout=0.5
                    )
                    last_frame_time = now
                    
                except asyncio.CancelledError:
                    break
                except asyncio.TimeoutError:
                    print("⚠️ WebSocket send timeout")
                    break
                except Exception as e:
                    logger.debug(f"WebSocket error: {e}")
                    await asyncio.sleep(0.05)
                    
        except asyncio.CancelledError:
            pass
        finally:
            self._clients.discard(ws)
            print(f"Client disconnected ({len(self._clients)} remaining)")
        
        return ws


# ============================================================================
# Metadata-Only Visualizer (high FPS analysis, low bandwidth)
# ============================================================================

METADATA_HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Metadata Stream Analyzer</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Consolas', monospace; background: #0a0a1a; color: #eee; padding: 10px; }
        .header { background: #1a1a2e; padding: 10px; border-radius: 6px; margin-bottom: 10px; }
        .header h1 { font-size: 14px; color: #00d9ff; }
        .header .stats { display: flex; gap: 20px; margin-top: 8px; font-size: 11px; }
        .header .stat { color: #0f0; }
        .header .stat-label { color: #888; }
        .container { display: grid; grid-template-columns: 320px 1fr; gap: 10px; height: calc(100vh - 100px); }
        .preview { background: #111; border-radius: 6px; padding: 10px; }
        .preview img { width: 100%; height: auto; border-radius: 4px; image-rendering: pixelated; }
        .preview .info { font-size: 9px; color: #888; margin-top: 5px; }
        .metadata { background: #111; border-radius: 6px; overflow: hidden; display: flex; flex-direction: column; }
        .metadata-header { background: #1a1a2e; padding: 8px 12px; font-size: 11px; color: #00d9ff; display: flex; justify-content: space-between; }
        .metadata-content { flex: 1; overflow-y: auto; padding: 10px; font-size: 10px; }
        .event { padding: 6px 8px; margin-bottom: 4px; border-radius: 4px; border-left: 3px solid #333; }
        .event.motion { border-color: #f80; background: rgba(255,136,0,0.1); }
        .event.object { border-color: #0f0; background: rgba(0,255,0,0.1); }
        .event.idle { border-color: #444; background: rgba(68,68,68,0.1); color: #666; }
        .event .time { color: #0ff; font-size: 9px; }
        .event .type { font-weight: bold; margin: 2px 0; }
        .event .data { color: #aaa; font-size: 9px; }
        .controls { margin-top: 10px; display: flex; gap: 5px; }
        .controls button { padding: 5px 10px; font-size: 10px; background: #333; border: none; color: #fff; border-radius: 3px; cursor: pointer; }
        .controls button:hover { background: #444; }
        #status { width: 8px; height: 8px; border-radius: 50%; background: #f00; display: inline-block; }
        #status.connected { background: #0f0; }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Metadata Stream Analyzer <span id="status"></span></h1>
        <div class="stats">
            <span><span class="stat-label">Analysis FPS:</span> <span class="stat" id="analysis-fps">0</span></span>
            <span><span class="stat-label">Latency:</span> <span class="stat" id="latency-ms" style="color:#ff0;">?</span></span>
            <span><span class="stat-label">Events/sec:</span> <span class="stat" id="events-sec">0</span></span>
            <span><span class="stat-label">Total Events:</span> <span class="stat" id="total-events">0</span></span>
            <span><span class="stat-label">Motion:</span> <span class="stat" id="motion-level">0%</span></span>
            <span><span class="stat-label">Objects:</span> <span class="stat" id="object-count">0</span></span>
        </div>
    </div>
    <div class="container">
        <div class="preview">
            <img id="preview-img" src="" alt="Preview (1 FPS)">
            <div class="info">Preview updates every 1 second</div>
            <div class="controls">
                <button onclick="clearEvents()">Clear Events</button>
                <button onclick="downloadEvents()">Download JSON</button>
                <button onclick="togglePause()">Pause</button>
            </div>
        </div>
        <div class="metadata">
            <div class="metadata-header">
                <span>📝 Real-time Event Stream</span>
                <span id="buffer-info">Buffer: 0</span>
            </div>
            <div class="metadata-content" id="events"></div>
        </div>
    </div>
    <script>
        const status = document.getElementById('status');
        const analysisFps = document.getElementById('analysis-fps');
        const eventsSec = document.getElementById('events-sec');
        const totalEvents = document.getElementById('total-events');
        const motionLevel = document.getElementById('motion-level');
        const objectCount = document.getElementById('object-count');
        const latencyDisplay = document.getElementById('latency-ms');
        const previewImg = document.getElementById('preview-img');
        const eventsDiv = document.getElementById('events');
        const bufferInfo = document.getElementById('buffer-info');
        
        let allEvents = [];
        let eventCount = 0;
        let frameCount = 0;
        let lastSecond = Date.now();
        let eventsThisSecond = 0;
        let paused = false;
        
        function connectWS() {
            const ws = new WebSocket('ws://' + location.host + '/ws');
            
            ws.onopen = () => {
                status.classList.add('connected');
                console.log('[META] Connected');
            };
            
            ws.onclose = () => {
                status.classList.remove('connected');
                setTimeout(connectWS, 2000);
            };
            
            ws.onmessage = (e) => {
                if (paused) return;
                
                const clientNow = Date.now();
                const data = JSON.parse(e.data);
                frameCount++;
                
                // Calculate latency
                const serverTs = data.ts || 0;
                const latencyMs = serverTs ? (clientNow - serverTs * 1000) : 0;
                
                // Update preview image (sent every ~1 second)
                if (data.img) {
                    previewImg.src = 'data:image/jpeg;base64,' + data.img;
                }
                
                // Process events
                const motion = data.m || 0;
                const objects = data.obj || [];
                const timestamp = data.ts_iso || new Date().toISOString().substr(11, 12);
                const dsl = data.dsl || '';
                
                // Update latency display (negative = clock skew, positive = actual latency)
                const absLatency = Math.abs(latencyMs);
                let color = '#0f0';
                let latencyText = latencyMs.toFixed(0) + 'ms';
                
                if (latencyMs < -1000) {
                    // Client clock is behind server - show warning
                    color = '#f0f';
                    latencyText = 'CLOCK SKEW: ' + latencyMs.toFixed(0) + 'ms';
                } else if (absLatency < 500) {
                    color = '#0f0';
                } else if (absLatency < 2000) {
                    color = '#ff0';
                } else {
                    color = '#f00';
                }
                
                latencyDisplay.textContent = latencyText;
                latencyDisplay.style.color = color;
                
                // Log latency to console
                if (frameCount % 10 === 0) {
                    console.log('[LATENCY] F#' + data.f + ' server=' + timestamp + ' latency=' + latencyMs.toFixed(0) + 'ms');
                }
                
                motionLevel.textContent = motion.toFixed(1) + '%';
                objectCount.textContent = objects.length;
                
                // Create event entry
                let eventType = 'idle';
                let eventText = 'No motion';
                
                if (motion > 5) {
                    eventType = 'motion';
                    eventText = 'Motion: ' + motion.toFixed(1) + '%';
                    if (objects.length > 0) {
                        eventType = 'object';
                        eventText = objects.length + ' object(s) detected';
                    }
                }
                
                // Only log significant events
                if (eventType !== 'idle' || frameCount % 10 === 0) {
                    const event = {
                        time: timestamp,
                        type: eventType,
                        motion: motion,
                        objects: objects.length,
                        dsl: dsl,
                    };
                    allEvents.push(event);
                    eventCount++;
                    eventsThisSecond++;
                    
                    // Add to UI
                    const div = document.createElement('div');
                    div.className = 'event ' + eventType;
                    div.innerHTML = '<div class="time">' + timestamp + '</div>' +
                        '<div class="type">' + eventText + '</div>' +
                        '<div class="data">' + (dsl ? dsl.split('\\n').slice(0,3).join(' | ') : '') + '</div>';
                    eventsDiv.insertBefore(div, eventsDiv.firstChild);
                    
                    // Limit UI events
                    while (eventsDiv.children.length > 100) {
                        eventsDiv.removeChild(eventsDiv.lastChild);
                    }
                }
                
                totalEvents.textContent = eventCount;
                bufferInfo.textContent = 'Buffer: ' + allEvents.length;
                
                // Update FPS counter
                const now = Date.now();
                if (now - lastSecond >= 1000) {
                    analysisFps.textContent = frameCount;
                    eventsSec.textContent = eventsThisSecond;
                    frameCount = 0;
                    eventsThisSecond = 0;
                    lastSecond = now;
                }
            };
        }
        connectWS();
        
        function clearEvents() {
            eventsDiv.innerHTML = '';
            allEvents = [];
            eventCount = 0;
            totalEvents.textContent = '0';
        }
        
        function downloadEvents() {
            const blob = new Blob([JSON.stringify(allEvents, null, 2)], {type: 'application/json'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'events_' + new Date().toISOString().replace(/[:.]/g, '-') + '.json';
            a.click();
        }
        
        function togglePause() {
            paused = !paused;
            event.target.textContent = paused ? 'Resume' : 'Pause';
        }
    </script>
</body>
</html>'''


class MetadataVisualizerServer:
    """
    Metadata-only visualizer with minimal bandwidth.
    
    - High FPS analysis (e.g., 10-30 FPS)
    - Only sends metadata (SVG, DSL, motion %) every frame
    - Sends JPEG preview only once per second
    - Ideal for: logging, alerting, remote monitoring over slow connections
    """
    
    def __init__(
        self,
        rtsp_url: str,
        host: str = "0.0.0.0",
        port: int = 8080,
        fps: float = 10.0,  # High FPS for analysis
        width: int = 320,
        height: int = 240,
        preview_interval: float = 1.0,  # Send preview every N seconds
        transport: str = "tcp",
        backend: str = "opencv",
    ):
        self.rtsp_url = rtsp_url
        self.host = host
        self.port = port
        self.fps = fps
        self.width = width
        self.height = height
        self.preview_interval = preview_interval
        self.transport = transport
        self.backend = backend
        
        self._running = False
        self._capture = None
        self._processor = None
        self._clients = set()
    
    def start(self):
        """Start the metadata server."""
        from aiohttp import web
        
        self._processor = RealtimeProcessor(width=self.width, height=self.height)
        self._capture = RTSPCapture(
            self.rtsp_url,
            fps=self.fps,
            width=self.width,
            height=self.height,
            transport=self.transport,
            backend=self.backend,
        )
        self._capture.start()
        self._running = True
        
        app = web.Application()
        app.router.add_get('/', self._handle_index)
        app.router.add_get('/ws', self._handle_websocket)
        app.router.add_get('/api/status', self._handle_status)
        
        print(f"\n🚀 Metadata Visualizer starting at http://{self.host}:{self.port}")
        print(f"📹 RTSP: {self.rtsp_url}")
        print(f"⚡ Analysis FPS: {self.fps}")
        print(f"📐 Size: {self.width}x{self.height}")
        print(f"🖼️ Preview: every {self.preview_interval}s")
        print(f"📊 Mode: METADATA-ONLY (low bandwidth)")
        print("\nOpen in browser to view metadata stream!")
        
        try:
            web.run_app(app, host=self.host, port=self.port, print=None)
        finally:
            self.stop()
    
    def stop(self):
        self._running = False
        if self._capture:
            self._capture.stop()
        print("🛑 Metadata Visualizer stopped")
    
    async def _handle_index(self, request):
        from aiohttp import web
        return web.Response(text=METADATA_HTML_TEMPLATE, content_type='text/html')
    
    async def _handle_status(self, request):
        from aiohttp import web
        return web.json_response({
            "running": self._running,
            "clients": len(self._clients),
            "fps": self.fps,
            "frame_count": self._processor._frame_count if self._processor else 0,
        })
    
    async def _handle_websocket(self, request):
        from aiohttp import web
        import asyncio
        
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self._clients.add(ws)
        print(f"Client connected ({len(self._clients)} total) [metadata mode]")
        
        frame_interval = 1.0 / max(1.0, self.fps)
        last_frame_time = 0
        last_preview_time = 0
        last_log_time = 0
        frames_since_log = 0
        
        try:
            while self._running and not ws.closed:
                try:
                    now = time.time()
                    if now - last_frame_time < frame_interval:
                        await asyncio.sleep(0.005)
                        continue
                    
                    t0 = time.time()
                    frame = self._capture.get_frame(timeout=0.2)
                    t1 = time.time()
                    
                    if frame is None:
                        await asyncio.sleep(0.01)
                        continue
                    
                    # Process frame
                    frame_data = self._processor.process_frame(frame)
                    t2 = time.time()
                    
                    # Build minimal message
                    server_ts = time.time()
                    ts_iso = time.strftime("%H:%M:%S", time.localtime(server_ts)) + f".{int((server_ts % 1) * 1000):03d}"
                    msg = {
                        "f": frame_data.frame_num,
                        "ts": round(server_ts, 3),
                        "ts_iso": ts_iso,
                        "m": round(frame_data.motion_percent, 2),
                        "obj": frame_data.objects or [],
                        "dsl": frame_data.dsl_text,
                    }
                    
                    # Add preview image only every preview_interval seconds
                    has_img = False
                    if now - last_preview_time >= self.preview_interval:
                        msg["img"] = frame_data.jpeg_base64
                        msg["svg"] = frame_data.svg_overlay
                        last_preview_time = now
                        has_img = True
                    
                    t3 = time.time()
                    await asyncio.wait_for(
                        ws.send_str(json.dumps(msg, separators=(',', ':'))),
                        timeout=0.3
                    )
                    t4 = time.time()
                    last_frame_time = now
                    frames_since_log += 1
                    
                    # Log to console every second
                    if now - last_log_time >= 1.0:
                        motion = frame_data.motion_percent
                        objs = len(frame_data.objects) if frame_data.objects else 0
                        cap_ms = (t1 - t0) * 1000
                        proc_ms = (t2 - t1) * 1000
                        send_ms = (t4 - t3) * 1000
                        total_ms = (t4 - t0) * 1000
                        
                        img_flag = "📷" if has_img else "  "
                        print(f"[{ts_iso}] {img_flag} F#{frame_data.frame_num:04d} | motion={motion:5.1f}% obj={objs} | cap={cap_ms:3.0f}ms proc={proc_ms:3.0f}ms send={send_ms:3.0f}ms total={total_ms:3.0f}ms | {frames_since_log} FPS")
                        
                        last_log_time = now
                        frames_since_log = 0
                    
                except asyncio.TimeoutError:
                    break
                except Exception as e:
                    logger.debug(f"WS error: {e}")
                    await asyncio.sleep(0.02)
                    
        finally:
            self._clients.discard(ws)
            print(f"Client disconnected ({len(self._clients)} remaining)")
        
        return ws


# ============================================================================
# WebRTC Visualizer (experimental, ultra-low latency)
# ============================================================================

class WebRTCVisualizerServer:
    """
    WebRTC-based visualizer for ultra-low latency.
    
    Requires: aiortc library
    
    Architecture:
    - WebRTC video track from OpenCV frames
    - WebRTC data channel for metadata
    - ~50-100ms end-to-end latency
    """
    
    def __init__(
        self,
        rtsp_url: str,
        host: str = "0.0.0.0",
        port: int = 8080,
        fps: float = 15.0,
        width: int = 640,
        height: int = 480,
        transport: str = "tcp",
        backend: str = "opencv",
    ):
        self.rtsp_url = rtsp_url
        self.host = host
        self.port = port
        self.fps = fps
        self.width = width
        self.height = height
        self.transport = transport
        self.backend = backend
        
        self._running = False
        self._capture = None
        self._processor = None
    
    def start(self):
        """Start WebRTC server."""
        try:
            from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
            from aiortc.contrib.media import MediaPlayer
        except ImportError:
            print("❌ WebRTC mode requires 'aiortc' library.")
            print("   Install with: pip install aiortc")
            print("\n   Falling back to WebSocket mode...")
            # Fallback to WS mode
            server = RealtimeVisualizerServer(
                self.rtsp_url,
                port=self.port,
                fps=self.fps,
                width=self.width,
                height=self.height,
                transport=self.transport,
                backend=self.backend,
            )
            server.start()
            return
        
        from aiohttp import web
        import asyncio
        
        self._processor = RealtimeProcessor(width=self.width, height=self.height)
        self._capture = RTSPCapture(
            self.rtsp_url,
            fps=self.fps,
            width=self.width,
            height=self.height,
            transport=self.transport,
            backend=self.backend,
        )
        self._capture.start()
        self._running = True
        
        # Store peer connections
        self._pcs = set()
        
        async def handle_index(request):
            return web.Response(text=self._get_webrtc_html(), content_type='text/html')
        
        async def handle_offer(request):
            params = await request.json()
            offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
            
            pc = RTCPeerConnection()
            self._pcs.add(pc)
            
            @pc.on("connectionstatechange")
            async def on_connectionstatechange():
                if pc.connectionState == "failed":
                    await pc.close()
                    self._pcs.discard(pc)
            
            # Create video track from OpenCV
            video_track = OpenCVVideoTrack(self._capture, self._processor, self.fps)
            pc.addTrack(video_track)
            
            # Create data channel for metadata
            dc = pc.createDataChannel("metadata")
            
            @dc.on("open")
            def on_open():
                asyncio.create_task(self._send_metadata(dc))
            
            await pc.setRemoteDescription(offer)
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)
            
            return web.json_response({
                "sdp": pc.localDescription.sdp,
                "type": pc.localDescription.type,
            })
        
        app = web.Application()
        app.router.add_get('/', handle_index)
        app.router.add_post('/offer', handle_offer)
        
        print(f"\n🚀 WebRTC Visualizer starting at http://{self.host}:{self.port}")
        print(f"📹 RTSP: {self.rtsp_url}")
        print(f"⚡ FPS: {self.fps}")
        print(f"📐 Size: {self.width}x{self.height}")
        print(f"🎥 Mode: WebRTC (ultra-low latency)")
        print("\nOpen in browser to view stream!")
        
        try:
            web.run_app(app, host=self.host, port=self.port, print=None)
        finally:
            self.stop()
    
    async def _send_metadata(self, dc):
        """Send metadata over data channel."""
        while self._running and dc.readyState == "open":
            try:
                if self._processor and self._processor._frame_count > 0:
                    msg = {
                        "f": self._processor._frame_count,
                        "ts": time.time(),
                    }
                    dc.send(json.dumps(msg))
                await asyncio.sleep(0.1)
            except Exception:
                break
    
    def stop(self):
        self._running = False
        if self._capture:
            self._capture.stop()
        print("🛑 WebRTC Visualizer stopped")
    
    def _get_webrtc_html(self):
        return '''<!DOCTYPE html>
<html>
<head>
    <title>WebRTC Stream</title>
    <style>
        body { margin: 0; background: #000; display: flex; justify-content: center; align-items: center; height: 100vh; }
        video { max-width: 100%; max-height: 100%; }
        #status { position: fixed; top: 10px; left: 10px; color: #0f0; font-family: monospace; font-size: 12px; }
    </style>
</head>
<body>
    <div id="status">Connecting...</div>
    <video id="video" autoplay playsinline></video>
    <script>
        const video = document.getElementById('video');
        const status = document.getElementById('status');
        
        async function start() {
            const pc = new RTCPeerConnection();
            
            pc.ontrack = (e) => {
                video.srcObject = e.streams[0];
                status.textContent = 'Connected (WebRTC)';
            };
            
            pc.ondatachannel = (e) => {
                e.channel.onmessage = (msg) => {
                    const data = JSON.parse(msg.data);
                    status.textContent = 'Frame: ' + data.f + ' | ' + new Date(data.ts * 1000).toLocaleTimeString();
                };
            };
            
            pc.addTransceiver('video', {direction: 'recvonly'});
            
            const offer = await pc.createOffer();
            await pc.setLocalDescription(offer);
            
            const resp = await fetch('/offer', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({sdp: offer.sdp, type: offer.type}),
            });
            
            const answer = await resp.json();
            await pc.setRemoteDescription(answer);
        }
        
        start().catch(e => {
            status.textContent = 'Error: ' + e.message;
            console.error(e);
        });
    </script>
</body>
</html>'''


# Placeholder for WebRTC video track (requires aiortc)
try:
    from aiortc import VideoStreamTrack
    from av import VideoFrame
    
    class OpenCVVideoTrack(VideoStreamTrack):
        """Video track that reads from OpenCV capture."""
        
        def __init__(self, capture, processor, fps):
            super().__init__()
            self.capture = capture
            self.processor = processor
            self.fps = fps
            self._timestamp = 0
        
        async def recv(self):
            import asyncio
            
            pts, time_base = await self.next_timestamp()
            
            # Get frame from capture
            frame = self.capture.get_frame(timeout=0.1)
            if frame is None:
                # Return black frame if no data
                import numpy as np
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
            
            # Convert to VideoFrame
            video_frame = VideoFrame.from_ndarray(frame, format="bgr24")
            video_frame.pts = pts
            video_frame.time_base = time_base
            
            return video_frame

except ImportError:
    # aiortc not installed, define placeholder
    class OpenCVVideoTrack:
        def __init__(self, *args, **kwargs):
            raise ImportError("aiortc required for WebRTC")


# ============================================================================
# MQTT DSL Publisher
# ============================================================================

class MQTTDSLPublisher:
    """
    MQTT publisher for DSL metadata.
    
    Publishes motion detection events and metadata to MQTT broker.
    Can run standalone or alongside other visualizers.
    
    Topics:
        - {prefix}/dsl          - Full DSL text
        - {prefix}/motion       - Motion percentage (float)
        - {prefix}/objects      - Object count (int)
        - {prefix}/events       - Motion events (JSON)
        - {prefix}/frame        - Frame metadata (JSON)
        - {prefix}/preview      - JPEG preview (binary, every N seconds)
    
    Usage:
        publisher = MQTTDSLPublisher(
            rtsp_url="rtsp://camera/stream",
            mqtt_broker="localhost",
            mqtt_port=1883,
            topic_prefix="streamware/camera1"
        )
        publisher.start()
    """
    
    def __init__(
        self,
        rtsp_url: str,
        mqtt_broker: str = "localhost",
        mqtt_port: int = 1883,
        mqtt_username: Optional[str] = None,
        mqtt_password: Optional[str] = None,
        topic_prefix: str = "streamware/dsl",
        fps: float = 5.0,
        width: int = 320,
        height: int = 240,
        preview_interval: float = 5.0,  # Send preview every N seconds
        motion_threshold: float = 2.0,  # Only publish if motion > threshold
    ):
        self.rtsp_url = rtsp_url
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.mqtt_username = mqtt_username
        self.mqtt_password = mqtt_password
        self.topic_prefix = topic_prefix.rstrip('/')
        self.fps = fps
        self.width = width
        self.height = height
        self.preview_interval = preview_interval
        self.motion_threshold = motion_threshold
        
        self._running = False
        self._capture = None
        self._processor = None
        self._mqtt_client = None
        self._thread = None
        
        # Stats
        self._messages_sent = 0
        self._events_published = 0
    
    def start(self):
        """Start MQTT publisher."""
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            print("❌ MQTT mode requires 'paho-mqtt' library.")
            print("   Install with: pip install paho-mqtt")
            return
        
        # Setup MQTT client
        self._mqtt_client = mqtt.Client(client_id=f"streamware-dsl-{int(time.time())}")
        
        if self.mqtt_username:
            self._mqtt_client.username_pw_set(self.mqtt_username, self.mqtt_password)
        
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print(f"✅ Connected to MQTT broker: {self.mqtt_broker}:{self.mqtt_port}")
                # Publish online status
                client.publish(f"{self.topic_prefix}/status", "online", retain=True)
            else:
                print(f"❌ MQTT connection failed: rc={rc}")
        
        def on_disconnect(client, userdata, rc):
            print(f"⚠️ MQTT disconnected: rc={rc}")
        
        self._mqtt_client.on_connect = on_connect
        self._mqtt_client.on_disconnect = on_disconnect
        
        # Set last will (offline status)
        self._mqtt_client.will_set(f"{self.topic_prefix}/status", "offline", retain=True)
        
        try:
            self._mqtt_client.connect(self.mqtt_broker, self.mqtt_port, keepalive=60)
            self._mqtt_client.loop_start()
        except Exception as e:
            print(f"❌ Failed to connect to MQTT broker: {e}")
            return
        
        # Setup capture and processor
        self._processor = RealtimeProcessor(width=self.width, height=self.height)
        self._capture = RTSPCapture(
            self.rtsp_url,
            fps=self.fps,
            width=self.width,
            height=self.height,
        )
        self._capture.start()
        self._running = True
        
        print(f"\n🚀 MQTT DSL Publisher started")
        print(f"📹 RTSP: {self.rtsp_url}")
        print(f"📡 MQTT: {self.mqtt_broker}:{self.mqtt_port}")
        print(f"📝 Topic: {self.topic_prefix}/*")
        print(f"⚡ FPS: {self.fps}")
        print(f"📐 Size: {self.width}x{self.height}")
        print(f"🎯 Motion threshold: {self.motion_threshold}%")
        print(f"\nSubscribe to topics:")
        print(f"   {self.topic_prefix}/dsl      - Full DSL text")
        print(f"   {self.topic_prefix}/motion   - Motion % (float)")
        print(f"   {self.topic_prefix}/events   - Motion events (JSON)")
        print(f"   {self.topic_prefix}/frame    - Frame metadata (JSON)")
        print(f"   {self.topic_prefix}/preview  - JPEG preview (binary)")
        print(f"\nPress Ctrl+C to stop\n")
        
        # Run main loop
        self._run_loop()
    
    def _run_loop(self):
        """Main processing loop."""
        frame_interval = 1.0 / max(1.0, self.fps)
        last_frame_time = 0
        last_preview_time = 0
        last_log_time = 0
        
        try:
            while self._running:
                now = time.time()
                
                if now - last_frame_time < frame_interval:
                    time.sleep(0.005)
                    continue
                
                frame = self._capture.get_frame(timeout=0.3)
                if frame is None:
                    time.sleep(0.01)
                    continue
                
                # Process frame
                frame_data = self._processor.process_frame(frame)
                last_frame_time = now
                
                motion = frame_data.motion_percent
                objects = frame_data.objects or []
                
                # Build timestamp
                ts = time.time()
                ts_iso = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(ts)) + f".{int((ts % 1) * 1000):03d}Z"
                
                # Always publish motion level
                self._mqtt_client.publish(
                    f"{self.topic_prefix}/motion",
                    f"{motion:.2f}",
                    qos=0
                )
                self._messages_sent += 1
                
                # Publish frame metadata
                frame_msg = {
                    "frame": frame_data.frame_num,
                    "timestamp": ts,
                    "timestamp_iso": ts_iso,
                    "motion_percent": round(motion, 2),
                    "object_count": len(objects),
                }
                self._mqtt_client.publish(
                    f"{self.topic_prefix}/frame",
                    json.dumps(frame_msg),
                    qos=0
                )
                self._messages_sent += 1
                
                # Publish DSL and events only if motion exceeds threshold
                if motion >= self.motion_threshold:
                    # Full DSL
                    self._mqtt_client.publish(
                        f"{self.topic_prefix}/dsl",
                        frame_data.dsl_text,
                        qos=1
                    )
                    
                    # Event JSON
                    event = {
                        "type": "motion_detected",
                        "timestamp": ts,
                        "timestamp_iso": ts_iso,
                        "frame": frame_data.frame_num,
                        "motion_percent": round(motion, 2),
                        "objects": objects,
                        "level": "HIGH" if motion > 20 else "MEDIUM" if motion > 5 else "LOW",
                    }
                    self._mqtt_client.publish(
                        f"{self.topic_prefix}/events",
                        json.dumps(event),
                        qos=1
                    )
                    self._events_published += 1
                    self._messages_sent += 2
                
                # Publish preview image periodically
                if now - last_preview_time >= self.preview_interval:
                    if frame_data.jpeg_base64:
                        # Decode base64 to binary for MQTT
                        jpeg_bytes = base64.b64decode(frame_data.jpeg_base64)
                        self._mqtt_client.publish(
                            f"{self.topic_prefix}/preview",
                            jpeg_bytes,
                            qos=0
                        )
                        self._messages_sent += 1
                    last_preview_time = now
                
                # Log stats every 5 seconds
                if now - last_log_time >= 5.0:
                    print(f"[{ts_iso[:19]}] F#{frame_data.frame_num:04d} | motion={motion:5.1f}% obj={len(objects)} | msgs={self._messages_sent} events={self._events_published}")
                    last_log_time = now
                    
        except KeyboardInterrupt:
            print("\n⏹️ Stopping...")
        finally:
            self.stop()
    
    def stop(self):
        """Stop publisher and cleanup."""
        self._running = False
        
        if self._mqtt_client:
            # Publish offline status
            self._mqtt_client.publish(f"{self.topic_prefix}/status", "offline", retain=True)
            self._mqtt_client.loop_stop()
            self._mqtt_client.disconnect()
        
        if self._capture:
            self._capture.stop()
        
        print(f"🛑 MQTT Publisher stopped (sent {self._messages_sent} messages, {self._events_published} events)")


def start_mqtt_publisher(
    rtsp_url: str,
    mqtt_broker: str = "localhost",
    mqtt_port: int = 1883,
    mqtt_username: Optional[str] = None,
    mqtt_password: Optional[str] = None,
    topic_prefix: str = "streamware/dsl",
    fps: float = 5.0,
    width: int = 320,
    height: int = 240,
    motion_threshold: float = 2.0,
):
    """Start MQTT DSL publisher."""
    publisher = MQTTDSLPublisher(
        rtsp_url=rtsp_url,
        mqtt_broker=mqtt_broker,
        mqtt_port=mqtt_port,
        mqtt_username=mqtt_username,
        mqtt_password=mqtt_password,
        topic_prefix=topic_prefix,
        fps=fps,
        width=width,
        height=height,
        motion_threshold=motion_threshold,
    )
    publisher.start()


# ============================================================================
# Entry Points
# ============================================================================

def start_visualizer(
    rtsp_url: str,
    port: int = 8080,
    fps: float = 2.0,
    width: int = 640,
    height: int = 480,
    use_simple: bool = False,
    video_mode: str = "ws",
    transport: str = "tcp",
    backend: str = "opencv",
):
    """
    Start real-time visualizer.
    
    Args:
        rtsp_url: RTSP stream URL
        port: HTTP port
        fps: Frames per second for analysis
        width: Frame width
        height: Frame height
        use_simple: Use simple HTTP server (no aiohttp)
        video_mode: Video streaming mode:
            - 'ws': JPEG frames over WebSocket (default, lowest latency)
            - 'hls': HTTP Live Streaming (higher latency, more stable)
            - 'meta': Metadata-only mode (high FPS analysis, 1 frame/sec preview)
            - 'webrtc': WebRTC (experimental, ultra-low latency)
        transport: RTSP transport - 'tcp' (stable) or 'udp' (lower latency)
        backend: Capture backend - 'opencv', 'gstreamer', 'pyav'
    """
    transport_label = "UDP" if transport == "udp" else "TCP"
    backend_label = {"opencv": "OpenCV/ffmpeg", "gstreamer": "GStreamer", "pyav": "PyAV"}.get(backend, backend)
    print(f"\n🎯 Starting Real-time Motion Visualizer")
    print(f"   URL: {rtsp_url}")
    print(f"   Port: {port}")
    print(f"   FPS: {fps}")
    print(f"   Size: {width}x{height}")
    print(f"   Mode: {video_mode.upper()}")
    print(f"   Transport: {transport_label}")
    print(f"   Backend: {backend_label}")
    
    if video_mode == "hls":
        server = HLSVisualizerServer(
            rtsp_url,
            port=port,
            fps=fps,
            width=width,
            height=height,
            transport=transport,
            backend=backend,
        )
    elif video_mode == "meta":
        server = MetadataVisualizerServer(
            rtsp_url,
            port=port,
            fps=fps,
            width=width,
            height=height,
            transport=transport,
            backend=backend,
        )
    elif video_mode == "webrtc":
        server = WebRTCVisualizerServer(
            rtsp_url,
            port=port,
            fps=fps,
            width=width,
            height=height,
            transport=transport,
            backend=backend,
        )
    elif use_simple:
        server = SimpleVisualizerServer(rtsp_url, port=port, fps=fps)
    else:
        try:
            import aiohttp
            server = RealtimeVisualizerServer(
                rtsp_url,
                port=port,
                fps=fps,
                width=width,
                height=height,
                transport=transport,
                backend=backend,
            )
        except ImportError:
            print("aiohttp not found, using simple server")
            server = SimpleVisualizerServer(rtsp_url, port=port, fps=fps)
    
    server.start()


# CLI entry point
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python realtime_visualizer.py <rtsp_url> [port] [fps]")
        print("Example: python realtime_visualizer.py rtsp://camera/stream 8080 2")
        sys.exit(1)
    
    rtsp_url = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
    fps = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
    
    start_visualizer(rtsp_url, port=port, fps=fps)
