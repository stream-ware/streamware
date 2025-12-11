"""
Real-time DSL Streaming Server

WebSocket-based server that streams DSL motion analysis in real-time.
Enables live animation updates during live narrator sessions.

Architecture:
  [FastCapture] → [FrameDiffAnalyzer] → [DSL Server] → [WebSocket] → [Browser Player]
                                              ↓
                                        [HTTP Server]
                                        (serves HTML player)

Usage:
  # Start server
  from streamware.realtime_dsl_server import RealtimeDSLServer
  server = RealtimeDSLServer(port=8765)
  server.start()
  
  # Feed frames during live narrator
  server.add_frame(delta, background_base64)
  
  # Open browser: http://localhost:8765
"""

import asyncio
import json
import logging
import threading
import time
import base64
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional, Set
from queue import Queue

logger = logging.getLogger(__name__)

# Try to import websockets
try:
    import websockets
    from websockets.server import serve
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False
    logger.warning("websockets not installed. Real-time DSL streaming disabled.")


class RealtimeDSLServer:
    """
    WebSocket server for real-time DSL streaming.
    
    Streams frame deltas to connected browser clients for live animation.
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8765, http_port: int = 8766):
        self.host = host
        self.port = port
        self.http_port = http_port
        
        self._running = False
        self._clients: Set = set()
        self._frame_queue: Queue = Queue(maxsize=100)
        self._frames: List[Dict] = []
        self._backgrounds: Dict[int, str] = {}
        
        self._ws_server = None
        self._http_server = None
        self._loop = None
        self._thread = None
        
    def start(self):
        """Start WebSocket and HTTP servers in background thread."""
        if not HAS_WEBSOCKETS:
            logger.error("Cannot start server: websockets not installed")
            return False
        
        if self._running:
            return True
        
        self._running = True
        self._thread = threading.Thread(target=self._run_servers, daemon=True)
        self._thread.start()
        
        # Wait for servers to start
        time.sleep(0.5)
        logger.info(f"Real-time DSL server started: ws://{self.host}:{self.port}, http://{self.host}:{self.http_port}")
        return True
    
    def stop(self):
        """Stop servers."""
        self._running = False
        
        # Stop event loop gracefully
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        
        if self._thread:
            self._thread.join(timeout=1.0)
        
        # Close WebSocket server
        if self._ws_server:
            try:
                self._ws_server.close()
            except:
                pass
            self._ws_server = None
        
        logger.info("Real-time DSL server stopped")
    
    def add_frame(self, delta: 'FrameDelta', background_base64: str = ""):
        """Add frame to broadcast queue."""
        frame_data = self._delta_to_dict(delta)
        frame_data['background'] = background_base64
        
        self._frames.append(frame_data)
        if background_base64:
            self._backgrounds[delta.frame_num] = background_base64
        
        # Queue for broadcast
        try:
            self._frame_queue.put_nowait(frame_data)
        except:
            pass  # Queue full, skip
    
    def _delta_to_dict(self, delta: 'FrameDelta') -> Dict:
        """Convert FrameDelta to JSON-serializable dict."""
        blobs = []
        for b in delta.blobs:
            blobs.append({
                'id': b.id,
                'x': b.center.x,
                'y': b.center.y,
                'w': b.size.x,
                'h': b.size.y,
                'vx': b.velocity.x,
                'vy': b.velocity.y,
            })
        
        events = []
        for e in delta.events:
            events.append({
                'type': e.type.value,
                'blob_id': e.blob_id,
                'direction': e.direction.value,
            })
        
        return {
            'frame_num': delta.frame_num,
            'timestamp': delta.timestamp,
            'motion_percent': delta.motion_percent,
            'blobs': blobs,
            'events': events,
        }
    
    def _run_servers(self):
        """Run WebSocket and HTTP servers."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        try:
            self._loop.run_until_complete(self._start_servers())
            self._loop.run_forever()
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            self._loop.close()
    
    async def _start_servers(self):
        """Start both servers."""
        # WebSocket server
        self._ws_server = await serve(
            self._handle_websocket,
            self.host,
            self.port,
        )
        
        # HTTP server for player HTML
        import http.server
        import socketserver
        
        class PlayerHandler(http.server.SimpleHTTPRequestHandler):
            server_instance = self
            
            def do_GET(self):
                if self.path == '/' or self.path == '/player':
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    html = self.server_instance._get_player_html()
                    self.wfile.write(html.encode())
                elif self.path == '/api/frames':
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    data = json.dumps({
                        'frames': self.server_instance._frames,
                        'backgrounds': self.server_instance._backgrounds,
                    })
                    self.wfile.write(data.encode())
                else:
                    self.send_error(404)
            
            def log_message(self, format, *args):
                pass  # Suppress logs
        
        # Run HTTP server in thread with SO_REUSEADDR to prevent "Address already in use"
        def run_http():
            import socket
            
            class ReusableTCPServer(socketserver.TCPServer):
                allow_reuse_address = True
                
                def server_bind(self):
                    self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    super().server_bind()
            
            try:
                with ReusableTCPServer((self.host, self.http_port), PlayerHandler) as httpd:
                    self._http_server = httpd
                    httpd.socket.settimeout(1.0)  # Allow periodic checks
                    while self._running:
                        try:
                            httpd.handle_request()
                        except socket.timeout:
                            pass  # Normal timeout, check _running flag
            except OSError as e:
                logger.warning(f"HTTP server error: {e}")
        
        threading.Thread(target=run_http, daemon=True).start()
        
        # Start broadcast task
        asyncio.create_task(self._broadcast_frames())
    
    async def _handle_websocket(self, websocket, path=None):
        """Handle WebSocket connection."""
        self._clients.add(websocket)
        logger.debug(f"Client connected. Total: {len(self._clients)}")
        
        try:
            # Send existing frames
            for frame in self._frames:
                await websocket.send(json.dumps({'type': 'frame', 'data': frame}))
            
            # Keep connection alive
            async for message in websocket:
                # Handle client messages (e.g., requests)
                pass
                
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self._clients.discard(websocket)
            logger.debug(f"Client disconnected. Total: {len(self._clients)}")
    
    async def _broadcast_frames(self):
        """Broadcast new frames to all clients."""
        while self._running:
            try:
                # Check queue
                if not self._frame_queue.empty():
                    frame = self._frame_queue.get_nowait()
                    message = json.dumps({'type': 'frame', 'data': frame})
                    
                    # Broadcast to all clients
                    if self._clients:
                        await asyncio.gather(
                            *[client.send(message) for client in self._clients],
                            return_exceptions=True
                        )
                
                await asyncio.sleep(0.05)  # 20 FPS max
                
            except Exception as e:
                logger.debug(f"Broadcast error: {e}")
                await asyncio.sleep(0.1)
    
    def _get_player_html(self) -> str:
        """Generate real-time player HTML."""
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎬 Real-time Motion Analysis</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Consolas', monospace;
            background: #0a0a1a;
            color: #eee;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }}
        header {{
            background: #111;
            padding: 15px 20px;
            border-bottom: 1px solid #333;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        h1 {{ color: #00d9ff; font-size: 18px; }}
        .status {{
            display: flex;
            gap: 20px;
            font-size: 12px;
        }}
        .status-item {{ display: flex; align-items: center; gap: 5px; }}
        .dot {{ width: 8px; height: 8px; border-radius: 50%; }}
        .dot.connected {{ background: #00ff88; }}
        .dot.disconnected {{ background: #ff6b6b; }}
        main {{
            flex: 1;
            display: grid;
            grid-template-columns: 1fr 300px;
            gap: 0;
        }}
        #canvas-container {{
            padding: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        #canvas {{
            width: 100%;
            max-width: 800px;
            aspect-ratio: 4/3;
            background: #1a1a2e;
            border: 1px solid #333;
            border-radius: 8px;
        }}
        .sidebar {{
            background: #111;
            border-left: 1px solid #333;
            overflow-y: auto;
            padding: 15px;
        }}
        .panel {{ margin-bottom: 20px; }}
        .panel h3 {{ color: #00d9ff; font-size: 11px; text-transform: uppercase; margin-bottom: 10px; }}
        .stat {{ display: flex; justify-content: space-between; font-size: 12px; padding: 3px 0; }}
        .stat-value {{ color: #00ff88; }}
        .events {{ font-size: 11px; max-height: 200px; overflow-y: auto; }}
        .event {{ padding: 3px 5px; margin: 2px 0; border-radius: 2px; }}
        .event-ENTER {{ background: #1a3a1a; color: #00ff88; }}
        .event-EXIT {{ background: #3a1a1a; color: #ff6b6b; }}
        .event-MOVE {{ background: #1a1a3a; color: #4ecdc4; }}
        .event-APPEAR {{ background: #2a2a1a; color: #ffd93d; }}
        #objects {{ font-size: 11px; }}
        .object {{ padding: 5px; margin: 3px 0; background: #1a1a2e; border-radius: 4px; }}
    </style>
</head>
<body>
    <header>
        <h1>🎬 Real-time Motion Analysis</h1>
        <div class="status">
            <div class="status-item">
                <div class="dot" id="ws-status"></div>
                <span id="ws-text">Connecting...</span>
            </div>
            <div class="status-item">
                <span>Frames:</span>
                <span id="frame-count" class="stat-value">0</span>
            </div>
            <div class="status-item">
                <span>Objects:</span>
                <span id="object-count" class="stat-value">0</span>
            </div>
        </div>
    </header>
    
    <main>
        <div id="canvas-container">
            <svg id="canvas" viewBox="0 0 800 600"></svg>
        </div>
        
        <div class="sidebar">
            <div class="panel">
                <h3>📊 Current Frame</h3>
                <div class="stat"><span>Frame #</span><span class="stat-value" id="cur-frame">-</span></div>
                <div class="stat"><span>Motion</span><span class="stat-value" id="cur-motion">-</span></div>
                <div class="stat"><span>Blobs</span><span class="stat-value" id="cur-blobs">-</span></div>
            </div>
            
            <div class="panel">
                <h3>🎯 Tracked Objects</h3>
                <div id="objects"></div>
            </div>
            
            <div class="panel">
                <h3>⚡ Events</h3>
                <div class="events" id="events"></div>
            </div>
        </div>
    </main>
    
    <script>
        const COLORS = ['#ff6b6b','#4ecdc4','#45b7d1','#96ceb4','#ffeaa7','#fd79a8','#a29bfe','#74b9ff'];
        let ws = null;
        let frames = [];
        let objects = {{}};
        let currentFrame = null;
        
        function connect() {{
            ws = new WebSocket('ws://' + location.hostname + ':{self.port}');
            
            ws.onopen = () => {{
                document.getElementById('ws-status').className = 'dot connected';
                document.getElementById('ws-text').textContent = 'Connected';
            }};
            
            ws.onclose = () => {{
                document.getElementById('ws-status').className = 'dot disconnected';
                document.getElementById('ws-text').textContent = 'Disconnected';
                setTimeout(connect, 2000);
            }};
            
            ws.onmessage = (e) => {{
                const msg = JSON.parse(e.data);
                if (msg.type === 'frame') {{
                    addFrame(msg.data);
                }}
            }};
        }}
        
        function addFrame(frame) {{
            frames.push(frame);
            currentFrame = frame;
            
            // Update stats
            document.getElementById('frame-count').textContent = frames.length;
            document.getElementById('cur-frame').textContent = frame.frame_num;
            document.getElementById('cur-motion').textContent = frame.motion_percent.toFixed(1) + '%';
            document.getElementById('cur-blobs').textContent = frame.blobs.length;
            
            // Track objects
            frame.blobs.forEach(b => {{
                if (!objects[b.id]) {{
                    objects[b.id] = {{ id: b.id, firstFrame: frame.frame_num, path: [] }};
                }}
                objects[b.id].lastFrame = frame.frame_num;
                objects[b.id].lastPos = {{ x: b.x, y: b.y }};
                if (Math.abs(b.vx) > 0.01 || Math.abs(b.vy) > 0.01) {{
                    const dir = Math.abs(b.vx) > Math.abs(b.vy) ? (b.vx > 0 ? 'R' : 'L') : (b.vy > 0 ? 'D' : 'U');
                    if (objects[b.id].path.slice(-1)[0] !== dir) objects[b.id].path.push(dir);
                }}
            }});
            
            document.getElementById('object-count').textContent = Object.keys(objects).length;
            
            // Update objects panel
            let objHtml = '';
            Object.values(objects).slice(-5).forEach(o => {{
                const path = o.path.length ? o.path.join('→') : '•';
                objHtml += '<div class="object">#' + o.id + ': F' + o.firstFrame + '-' + o.lastFrame + ' ' + path + '</div>';
            }});
            document.getElementById('objects').innerHTML = objHtml;
            
            // Update events
            let evtHtml = '';
            frame.events.forEach(e => {{
                evtHtml = '<div class="event event-' + e.type + '">F' + frame.frame_num + ': ' + e.type + ' #' + e.blob_id + '</div>' + evtHtml;
            }});
            document.getElementById('events').innerHTML = evtHtml + document.getElementById('events').innerHTML;
            
            // Render
            renderFrame(frame);
        }}
        
        function renderFrame(frame) {{
            const svg = document.getElementById('canvas');
            let html = '<rect width="800" height="600" fill="#1a1a2e"/>';
            
            // Background image
            if (frame.background) {{
                html += '<image href="data:image/jpeg;base64,' + frame.background + '" width="800" height="600" preserveAspectRatio="xMidYMid slice" opacity="0.5"/>';
            }}
            
            // Blobs
            frame.blobs.forEach(b => {{
                const color = COLORS[b.id % COLORS.length];
                const cx = b.x * 800, cy = b.y * 600;
                const w = b.w * 800, h = b.h * 600;
                
                html += '<rect x="' + (cx-w/2) + '" y="' + (cy-h/2) + '" width="' + w + '" height="' + h + '" fill="' + color + '" fill-opacity="0.3" stroke="' + color + '" stroke-width="2" rx="3"/>';
                html += '<text x="' + cx + '" y="' + (cy-h/2-5) + '" fill="' + color + '" font-size="12" text-anchor="middle">#' + b.id + '</text>';
                html += '<circle cx="' + cx + '" cy="' + cy + '" r="4" fill="' + color + '"/>';
                
                // Velocity arrow
                if (Math.abs(b.vx) > 0.005 || Math.abs(b.vy) > 0.005) {{
                    const ax = cx + b.vx * 500, ay = cy + b.vy * 500;
                    html += '<line x1="' + cx + '" y1="' + cy + '" x2="' + ax + '" y2="' + ay + '" stroke="#ffff00" stroke-width="2"/>';
                }}
            }});
            
            // Frame info
            html += '<text x="10" y="25" fill="#00d9ff" font-size="14">Frame ' + frame.frame_num + ' | Motion: ' + frame.motion_percent.toFixed(1) + '%</text>';
            
            svg.innerHTML = html;
        }}
        
        // Load existing frames
        fetch('/api/frames').then(r => r.json()).then(data => {{
            data.frames.forEach(addFrame);
        }});
        
        connect();
    </script>
</body>
</html>'''


# Global instance
_server: Optional[RealtimeDSLServer] = None


def get_realtime_server(auto_start: bool = True) -> Optional[RealtimeDSLServer]:
    """Get or create global real-time DSL server."""
    global _server
    
    if not HAS_WEBSOCKETS:
        return None
    
    if _server is None:
        _server = RealtimeDSLServer()
        if auto_start:
            _server.start()
    
    return _server


def stop_realtime_server():
    """Stop global server."""
    global _server
    if _server:
        _server.stop()
        _server = None
        # Give async tasks time to cleanup
        import time
        time.sleep(0.2)
