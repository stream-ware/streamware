"""
Visualizer Server Classes - HLS and Metadata Servers

Extracted from visualizer_servers.py for modularity.
"""

import asyncio
import base64
import json
import logging
import queue
import threading
import time
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

from .visualizer_processor import FrameData, RealtimeProcessor
from .visualizer_capture import RTSPCapture

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
