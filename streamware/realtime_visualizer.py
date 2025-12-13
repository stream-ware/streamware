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

# Import extracted modules
from .visualizer_processor import FrameData, RealtimeProcessor
from .visualizer_capture import RTSPCapture


# ============================================================================
# Web Server HTML Template
# ============================================================================

# Note: FrameData and RealtimeProcessor are now in visualizer_processor.py
# Note: RTSPCapture is now in visualizer_capture.py

# Keeping HTML_TEMPLATE inline for backwards compatibility
# Classes extracted to separate modules

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



# Import server classes from extracted modules
from .visualizer_servers import (
    RealtimeVisualizerServer,
    SimpleVisualizerServer,
)
from .visualizer_servers_hls import (
    HLSVisualizerServer,
    MetadataVisualizerServer,
)
from .visualizer_servers_advanced import (
    WebRTCVisualizerServer,
    MQTTDSLPublisher,
    start_mqtt_publisher,
)

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
