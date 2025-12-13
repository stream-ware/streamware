"""
Visualizer Server Classes - Core Servers

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

