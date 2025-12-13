"""
Visualizer Server Classes - WebRTC and MQTT Servers

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


