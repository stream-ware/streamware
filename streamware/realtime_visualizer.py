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
    """Data for single frame."""
    frame_num: int
    timestamp: float
    jpeg_base64: str = ""
    svg_overlay: str = ""
    dsl_text: str = ""
    motion_percent: float = 0.0
    objects: List[Dict] = None
    events: List[str] = None
    
    def to_json(self) -> str:
        return json.dumps(asdict(self), default=str)


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
    
    def process_frame(self, frame_jpeg: bytes) -> FrameData:
        """
        Process single frame - FAST in-memory processing.
        
        Args:
            frame_jpeg: JPEG encoded frame
            
        Returns:
            FrameData with all analysis
        """
        self._ensure_initialized()
        self._frame_count += 1
        
        try:
            import cv2
            import numpy as np
            
            # Decode JPEG in memory (no file I/O!)
            nparr = np.frombuffer(frame_jpeg, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                return self._empty_frame_data(frame_jpeg)
            
            h, w = frame.shape[:2]
            
            # Fast motion detection
            motion_percent = 0.0
            blobs = []
            events = []
            
            if self._bg_subtractor is not None:
                # Apply background subtraction
                mask = self._bg_subtractor.apply(frame)
                
                # Quick morphology
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
                
                # Motion percentage
                motion_percent = (cv2.countNonZero(mask) / (h * w)) * 100
                
                # Find contours (fast)
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                # Process top 5 largest contours only
                contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
                
                for contour in contours:
                    area = cv2.contourArea(contour)
                    if area < 300:  # Skip tiny areas
                        continue
                    
                    x, y, bw, bh = cv2.boundingRect(contour)
                    cx, cy = x + bw/2, y + bh/2
                    
                    blobs.append({
                        "id": len(blobs) + 1,
                        "x": cx / w,
                        "y": cy / h,
                        "w": bw / w,
                        "h": bh / h,
                        "area": area,
                    })
            
            # Generate simple SVG overlay
            svg = self._generate_fast_svg(blobs, motion_percent)
            
            # Generate simple DSL
            dsl_text = self._generate_fast_dsl(blobs, motion_percent)
            
            return FrameData(
                frame_num=self._frame_count,
                timestamp=time.time(),
                jpeg_base64=base64.b64encode(frame_jpeg).decode(),
                svg_overlay=svg,
                dsl_text=dsl_text,
                motion_percent=motion_percent,
                objects=blobs,
                events=events,
            )
            
        except Exception as e:
            logger.debug(f"Frame processing error: {e}")
            return self._empty_frame_data(frame_jpeg)
    
    def _empty_frame_data(self, frame_jpeg: bytes) -> FrameData:
        """Return empty frame data."""
        return FrameData(
            frame_num=self._frame_count,
            timestamp=time.time(),
            jpeg_base64=base64.b64encode(frame_jpeg).decode(),
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
        """Generate simple DSL text."""
        ts = time.strftime("%H:%M:%S")
        lines = [f"FRAME {self._frame_count} @ {ts}"]
        lines.append(f"  DELTA motion={motion_percent:.1f}% blobs={len(blobs)}")
        
        for blob in blobs:
            lines.append(f"  BLOB id={blob['id']} pos=({blob['x']:.2f},{blob['y']:.2f}) size=({blob['w']:.2f},{blob['h']:.2f})")
        
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
    """
    
    def __init__(
        self,
        rtsp_url: str,
        fps: float = 2.0,
        width: int = 640,
        height: int = 480,
    ):
        self.rtsp_url = rtsp_url
        self.fps = fps
        self.width = width
        self.height = height
        
        self._running = False
        self._thread = None
        self._frame_queue = queue.Queue(maxsize=5)
        self._capture = None
    
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
    
    def _capture_loop(self):
        """Background capture loop."""
        try:
            import cv2
        except ImportError:
            logger.error("OpenCV not available")
            return
        
        # Open capture
        self._capture = cv2.VideoCapture(self.rtsp_url)
        if not self._capture.isOpened():
            logger.error(f"Failed to open: {self.rtsp_url}")
            return
        
        interval = 1.0 / self.fps
        last_capture = 0
        
        while self._running:
            now = time.time()
            if now - last_capture < interval:
                time.sleep(0.01)
                continue
            
            ret, frame = self._capture.read()
            if not ret:
                time.sleep(0.1)
                continue
            
            # Resize
            frame = cv2.resize(frame, (self.width, self.height))
            
            # Encode to JPEG
            _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            
            # Queue frame
            try:
                self._frame_queue.put_nowait(jpeg.tobytes())
            except queue.Full:
                # Drop old frame
                try:
                    self._frame_queue.get_nowait()
                    self._frame_queue.put_nowait(jpeg.tobytes())
                except:
                    pass
            
            last_capture = now
        
        self._capture.release()


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
        body {
            font-family: 'Consolas', monospace;
            background: #0a0a1a;
            color: #eee;
            overflow: hidden;
        }
        .container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-template-rows: 1fr 200px;
            height: 100vh;
            gap: 10px;
            padding: 10px;
        }
        .panel {
            background: #111;
            border-radius: 8px;
            overflow: hidden;
            position: relative;
        }
        .panel-header {
            background: #1a1a2e;
            padding: 8px 15px;
            font-size: 12px;
            color: #00d9ff;
            text-transform: uppercase;
            letter-spacing: 1px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .video-panel {
            position: relative;
        }
        #video-container {
            width: 100%;
            height: calc(100% - 35px);
            position: relative;
            background: #000;
        }
        #video-frame {
            width: 100%;
            height: 100%;
            object-fit: contain;
        }
        #svg-overlay {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
        }
        .svg-panel {
            display: flex;
            flex-direction: column;
        }
        #svg-standalone {
            flex: 1;
            background: #1a1a2e;
        }
        #svg-standalone svg {
            width: 100%;
            height: 100%;
        }
        .dsl-panel {
            grid-column: span 2;
        }
        #dsl-output {
            height: calc(100% - 35px);
            overflow-y: auto;
            padding: 10px;
            font-size: 11px;
            line-height: 1.4;
            white-space: pre-wrap;
            color: #888;
        }
        #dsl-output .frame-header {
            color: #00d9ff;
            font-weight: bold;
        }
        #dsl-output .event {
            color: #00ff88;
        }
        #dsl-output .blob {
            color: #4ecdc4;
        }
        .stats {
            display: flex;
            gap: 20px;
            font-size: 11px;
        }
        .stat { color: #888; }
        .stat-value { color: #00ff88; margin-left: 5px; }
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #ff0000;
            animation: pulse 1s infinite;
        }
        .status-dot.connected { background: #00ff00; }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .controls {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        button {
            background: #333;
            border: none;
            color: white;
            padding: 5px 10px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 11px;
        }
        button:hover { background: #444; }
        #motion-bar {
            width: 100px;
            height: 6px;
            background: #333;
            border-radius: 3px;
            overflow: hidden;
        }
        #motion-fill {
            height: 100%;
            background: linear-gradient(90deg, #00ff00, #ffff00, #ff0000);
            transition: width 0.2s;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="panel video-panel">
            <div class="panel-header">
                <span>📹 Live Video + SVG Overlay</span>
                <div class="controls">
                    <div class="status-dot" id="status-dot"></div>
                    <span id="fps-counter">0 FPS</span>
                </div>
            </div>
            <div id="video-container">
                <img id="video-frame" src="" alt="Video">
                <div id="svg-overlay"></div>
            </div>
        </div>
        
        <div class="panel svg-panel">
            <div class="panel-header">
                <span>🎯 SVG Analysis View</span>
                <div class="stats">
                    <span class="stat">Motion: <span class="stat-value" id="motion-value">0%</span></span>
                    <span class="stat">Objects: <span class="stat-value" id="objects-value">0</span></span>
                    <span class="stat">Frame: <span class="stat-value" id="frame-value">0</span></span>
                </div>
            </div>
            <div id="svg-standalone"></div>
        </div>
        
        <div class="panel dsl-panel">
            <div class="panel-header">
                <span>📝 DSL Metadata Stream</span>
                <div class="controls">
                    <div id="motion-bar"><div id="motion-fill" style="width: 0%"></div></div>
                    <button onclick="clearDSL()">Clear</button>
                    <button onclick="togglePause()">Pause</button>
                    <button onclick="downloadDSL()">Download</button>
                </div>
            </div>
            <div id="dsl-output"></div>
        </div>
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
        
        let paused = false;
        let frameCount = 0;
        let lastFpsTime = Date.now();
        let fpsFrames = 0;
        let allDSL = [];
        
        // WebSocket connection
        const ws = new WebSocket(`ws://${window.location.host}/ws`);
        
        ws.onopen = () => {
            statusDot.classList.add('connected');
            console.log('Connected');
        };
        
        ws.onclose = () => {
            statusDot.classList.remove('connected');
            console.log('Disconnected');
        };
        
        ws.onmessage = (event) => {
            if (paused) return;
            
            const data = JSON.parse(event.data);
            
            // Update video
            if (data.jpeg_base64) {
                videoFrame.src = 'data:image/jpeg;base64,' + data.jpeg_base64;
            }
            
            // Update SVG overlay
            if (data.svg_overlay) {
                svgOverlay.innerHTML = data.svg_overlay;
                
                // Also show in standalone panel with dark background
                svgStandalone.innerHTML = data.svg_overlay.replace(
                    'style="position:absolute',
                    'style="background:#1a1a2e;'
                );
            }
            
            // Update DSL
            if (data.dsl_text) {
                const formatted = formatDSL(data.dsl_text);
                dslOutput.innerHTML = formatted + dslOutput.innerHTML;
                allDSL.push(data.dsl_text);
                
                // Limit lines
                if (dslOutput.children.length > 100) {
                    dslOutput.removeChild(dslOutput.lastChild);
                }
            }
            
            // Update stats
            motionValue.textContent = data.motion_percent.toFixed(1) + '%';
            objectsValue.textContent = data.objects ? data.objects.length : 0;
            frameValue.textContent = data.frame_num;
            motionFill.style.width = Math.min(100, data.motion_percent * 2) + '%';
            
            // FPS counter
            fpsFrames++;
            const now = Date.now();
            if (now - lastFpsTime >= 1000) {
                fpsCounter.textContent = fpsFrames + ' FPS';
                fpsFrames = 0;
                lastFpsTime = now;
            }
        };
        
        function formatDSL(text) {
            return text
                .replace(/(FRAME \\d+ @ [\\d:.]+)/g, '<span class="frame-header">$1</span>')
                .replace(/(EVENT [^\\n]+)/g, '<span class="event">$1</span>')
                .replace(/(BLOB [^\\n]+)/g, '<span class="blob">$1</span>')
                + '\\n\\n';
        }
        
        function clearDSL() {
            dslOutput.innerHTML = '';
            allDSL = [];
        }
        
        function togglePause() {
            paused = !paused;
            event.target.textContent = paused ? 'Resume' : 'Pause';
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
    ):
        self.rtsp_url = rtsp_url
        self.host = host
        self.port = port
        self.fps = fps
        self.width = width
        self.height = height
        
        self._capture = None
        self._processor = None
        self._running = False
        self._clients = set()
    
    def start(self):
        """Start the visualization server."""
        try:
            import asyncio
            from aiohttp import web
        except ImportError:
            logger.error("aiohttp required: pip install aiohttp")
            return
        
        # Initialize components
        self._capture = RTSPCapture(
            self.rtsp_url,
            fps=self.fps,
            width=self.width,
            height=self.height,
        )
        self._processor = RealtimeProcessor(
            width=self.width,
            height=self.height,
        )
        
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
        
        # Run server
        web.run_app(app, host=self.host, port=self.port, print=None)
    
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
        
        try:
            while self._running and not ws.closed:
                try:
                    # Rate limit
                    now = time.time()
                    if now - last_frame_time < frame_interval:
                        await asyncio.sleep(0.02)
                        continue
                    
                    # Get frame
                    frame_jpeg = self._capture.get_frame(timeout=0.5)
                    if frame_jpeg is None:
                        await asyncio.sleep(0.05)
                        continue
                    
                    # Process frame
                    frame_data = self._processor.process_frame(frame_jpeg)
                    
                    # Send to client (with timeout)
                    try:
                        await asyncio.wait_for(
                            ws.send_str(frame_data.to_json()),
                            timeout=1.0
                        )
                        last_frame_time = now
                    except asyncio.TimeoutError:
                        logger.debug("WebSocket send timeout")
                        break
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.debug(f"Frame error: {e}")
                    await asyncio.sleep(0.1)
                
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
                    except:
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
# Entry Points
# ============================================================================

def start_visualizer(
    rtsp_url: str,
    port: int = 8080,
    fps: float = 2.0,
    width: int = 640,
    height: int = 480,
    use_simple: bool = False,
):
    """
    Start real-time visualizer.
    
    Args:
        rtsp_url: RTSP stream URL
        port: HTTP port
        fps: Frames per second
        width: Frame width
        height: Frame height
        use_simple: Use simple HTTP server (no aiohttp)
    """
    if use_simple:
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
