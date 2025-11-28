#!/usr/bin/env python3
"""
COMPLETE VIDEO CAPTIONING PROJECT
==================================

Real-time video captioning system using Streamware Quick commands.

Features:
- Read from RTSP stream
- Object detection with YOLO
- Frame analysis with OpenCV
- AI captions with LLM
- Real-time web streaming
- Text stream on webpage

Tech Stack:
- RTSP: Video input
- OpenCV: Frame processing
- YOLO: Object detection
- LLM (Ollama): Caption generation
- Flask: Web server
- WebSockets: Real-time updates

Author: Streamware Team
License: Apache 2.0
"""

import sys
import os
import time
import json
import base64
import threading
from datetime import datetime
from pathlib import Path

# Streamware imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from streamware import flow
from streamware.components.llm import llm_generate

# Web server
try:
    from flask import Flask, render_template, Response, jsonify
    from flask_socketio import SocketIO, emit
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("⚠️  Flask not installed. Install: pip install flask flask-socketio")

# Video processing
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("⚠️  OpenCV not installed. Install: pip install opencv-python")

# YOLO detection
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("⚠️  YOLO not installed. Install: pip install ultralytics")


# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """Configuration for video captioning system"""
    
    # Video source
    RTSP_URL = os.environ.get("RTSP_URL", "rtsp://localhost:8554/stream")
    # For testing with webcam, use: "0"
    # For video file: "/path/to/video.mp4"
    
    # Processing
    PROCESS_FPS = 1  # Process 1 frame per second
    SKIP_FRAMES = 30  # Skip 30 frames between detections
    
    # YOLO
    YOLO_MODEL = "yolov8n.pt"  # Lightweight model
    YOLO_CONFIDENCE = 0.5
    YOLO_CLASSES = None  # None = all classes, or list like ["person", "car"]
    
    # LLM
    LLM_PROVIDER = "ollama"  # Free, local
    LLM_MODEL = "llama3.2:latest"
    CAPTION_INTERVAL = 5  # Generate caption every 5 seconds
    
    # Web server
    WEB_HOST = "0.0.0.0"
    WEB_PORT = 8080
    
    # Logging
    SAVE_DETECTIONS = True
    DETECTION_LOG = "/tmp/detections.jsonl"


# ============================================================================
# VIDEO PROCESSOR
# ============================================================================

class VideoProcessor:
    """Process video frames with YOLO and generate captions"""
    
    def __init__(self, config: Config):
        self.config = config
        self.running = False
        self.current_frame = None
        self.current_detections = []
        self.current_caption = "Initializing..."
        self.frame_count = 0
        self.last_caption_time = 0
        
        # Load YOLO model
        if YOLO_AVAILABLE:
            print(f"📦 Loading YOLO model: {config.YOLO_MODEL}")
            self.model = YOLO(config.YOLO_MODEL)
        else:
            self.model = None
            print("⚠️  YOLO not available, using basic analysis")
    
    def start(self):
        """Start video processing"""
        self.running = True
        
        # Start processing thread
        thread = threading.Thread(target=self._process_loop, daemon=True)
        thread.start()
        
        print(f"🎥 Video processing started")
        print(f"   Source: {self.config.RTSP_URL}")
        print(f"   FPS: {self.config.PROCESS_FPS}")
        return thread
    
    def stop(self):
        """Stop processing"""
        self.running = False
        print("🛑 Video processing stopped")
    
    def _process_loop(self):
        """Main processing loop"""
        print(f"🔌 Connecting to video source...")
        
        # Open video source
        cap = cv2.VideoCapture(self.config.RTSP_URL)
        
        if not cap.isOpened():
            print(f"❌ Failed to open video source: {self.config.RTSP_URL}")
            return
        
        print(f"✅ Connected to video source")
        
        last_process_time = 0
        process_interval = 1.0 / self.config.PROCESS_FPS
        
        while self.running:
            ret, frame = cap.read()
            
            if not ret:
                print("⚠️  Failed to read frame, reconnecting...")
                cap.release()
                time.sleep(1)
                cap = cv2.VideoCapture(self.config.RTSP_URL)
                continue
            
            self.frame_count += 1
            current_time = time.time()
            
            # Process at specified FPS
            if current_time - last_process_time >= process_interval:
                last_process_time = current_time
                
                # Store current frame
                self.current_frame = frame.copy()
                
                # Detect objects
                detections = self._detect_objects(frame)
                self.current_detections = detections
                
                # Generate caption periodically
                if current_time - self.last_caption_time >= self.config.CAPTION_INTERVAL:
                    self.last_caption_time = current_time
                    caption = self._generate_caption(detections)
                    self.current_caption = caption
                    
                    # Log
                    self._log_detection(detections, caption)
                    
                    print(f"\n📝 Caption: {caption}")
                    print(f"   Detected: {len(detections)} objects")
        
        cap.release()
    
    def _detect_objects(self, frame):
        """Detect objects in frame"""
        if not YOLO_AVAILABLE or self.model is None:
            return []
        
        # Run YOLO detection
        results = self.model(frame, conf=self.config.YOLO_CONFIDENCE, verbose=False)
        
        detections = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                class_name = self.model.names[int(box.cls)]
                
                # Filter by class if specified
                if self.config.YOLO_CLASSES:
                    if class_name not in self.config.YOLO_CLASSES:
                        continue
                
                detection = {
                    "class": class_name,
                    "confidence": float(box.conf),
                    "bbox": box.xyxy[0].tolist()
                }
                detections.append(detection)
        
        return detections
    
    def _generate_caption(self, detections):
        """Generate natural language caption"""
        if not detections:
            return "Scene is empty or no objects detected."
        
        # Count objects
        object_counts = {}
        for det in detections:
            class_name = det["class"]
            object_counts[class_name] = object_counts.get(class_name, 0) + 1
        
        # Create prompt for LLM
        objects_str = ", ".join([f"{count} {obj}(s)" for obj, count in object_counts.items()])
        prompt = f"Generate a short, natural caption for a video frame containing: {objects_str}. Be concise and descriptive."
        
        try:
            # Use Streamware LLM component
            caption = llm_generate(prompt, provider=self.config.LLM_PROVIDER)
            return caption.strip()
        except Exception as e:
            print(f"⚠️  LLM caption failed: {e}")
            # Fallback caption
            return f"Scene contains {objects_str}"
    
    def _log_detection(self, detections, caption):
        """Log detection to file"""
        if not self.config.SAVE_DETECTIONS:
            return
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "frame": self.frame_count,
            "detections": detections,
            "caption": caption
        }
        
        try:
            with open(self.config.DETECTION_LOG, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            print(f"⚠️  Failed to log: {e}")
    
    def get_frame_jpeg(self):
        """Get current frame as JPEG bytes"""
        if self.current_frame is None:
            return None
        
        # Draw detections on frame
        frame = self.current_frame.copy()
        
        for det in self.current_detections:
            bbox = det["bbox"]
            x1, y1, x2, y2 = map(int, bbox)
            
            # Draw box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Draw label
            label = f"{det['class']} {det['confidence']:.2f}"
            cv2.putText(frame, label, (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Add caption
        cv2.putText(frame, self.current_caption, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # Encode to JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        return buffer.tobytes()


# ============================================================================
# WEB SERVER
# ============================================================================

# Global processor instance
processor = None

# Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'streamware-video-captioning'
socketio = SocketIO(app, cors_allowed_origins="*")


@app.route('/')
def index():
    """Main page"""
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>Streamware Video Captioning</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f0f0f0;
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .container {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 20px;
        }
        .video-panel {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .info-panel {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        img {
            width: 100%;
            border-radius: 4px;
        }
        .caption {
            font-size: 18px;
            margin: 15px 0;
            padding: 15px;
            background: #e3f2fd;
            border-left: 4px solid #2196f3;
            border-radius: 4px;
        }
        .detections {
            margin-top: 20px;
        }
        .detection-item {
            padding: 8px;
            margin: 5px 0;
            background: #f5f5f5;
            border-radius: 4px;
        }
        .stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 20px;
        }
        .stat {
            padding: 15px;
            background: #f5f5f5;
            border-radius: 4px;
            text-align: center;
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #2196f3;
        }
        .stat-label {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
        }
        .powered-by {
            text-align: center;
            margin-top: 20px;
            color: #666;
        }
    </style>
</head>
<body>
    <h1>🎥 Streamware Video Captioning</h1>
    <p style="text-align: center; color: #666;">
        Real-time video analysis with YOLO + AI captions
    </p>
    
    <div class="container">
        <div class="video-panel">
            <h2>Live Video Stream</h2>
            <img src="/video_feed" id="video" alt="Video Stream">
            
            <div class="caption" id="caption">
                Initializing...
            </div>
        </div>
        
        <div class="info-panel">
            <h2>Detection Info</h2>
            
            <div class="stats">
                <div class="stat">
                    <div class="stat-value" id="frame-count">0</div>
                    <div class="stat-label">Frames</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="object-count">0</div>
                    <div class="stat-label">Objects</div>
                </div>
            </div>
            
            <div class="detections">
                <h3>Detected Objects</h3>
                <div id="detections-list"></div>
            </div>
        </div>
    </div>
    
    <div class="powered-by">
        Powered by <strong>Streamware</strong> | 
        YOLO + OpenCV + LLM
    </div>
    
    <script>
        const socket = io();
        
        socket.on('update', function(data) {
            // Update caption
            document.getElementById('caption').textContent = data.caption;
            
            // Update stats
            document.getElementById('frame-count').textContent = data.frame_count;
            document.getElementById('object-count').textContent = data.detections.length;
            
            // Update detections list
            const list = document.getElementById('detections-list');
            list.innerHTML = '';
            
            data.detections.forEach(det => {
                const div = document.createElement('div');
                div.className = 'detection-item';
                div.textContent = `${det.class} (${(det.confidence * 100).toFixed(0)}%)`;
                list.appendChild(div);
            });
        });
        
        console.log('🎥 Video captioning client started');
    </script>
</body>
</html>
    """
    return html


@app.route('/video_feed')
def video_feed():
    """Video streaming route"""
    def generate():
        while True:
            if processor and processor.current_frame is not None:
                frame = processor.get_frame_jpeg()
                if frame:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.1)
    
    return Response(generate(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/status')
def status():
    """API status endpoint"""
    if processor:
        return jsonify({
            "running": processor.running,
            "frame_count": processor.frame_count,
            "detections": len(processor.current_detections),
            "caption": processor.current_caption
        })
    return jsonify({"running": False})


def broadcast_updates():
    """Broadcast updates to clients"""
    while True:
        if processor:
            socketio.emit('update', {
                "frame_count": processor.frame_count,
                "detections": processor.current_detections,
                "caption": processor.current_caption,
                "timestamp": time.time()
            })
        time.sleep(1)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point"""
    global processor
    
    print("=" * 70)
    print("STREAMWARE VIDEO CAPTIONING SYSTEM")
    print("=" * 70)
    print()
    
    # Check dependencies
    print("📦 Checking dependencies...")
    if not CV2_AVAILABLE:
        print("❌ OpenCV not installed: pip install opencv-python")
        return 1
    if not YOLO_AVAILABLE:
        print("⚠️  YOLO not installed: pip install ultralytics")
        print("   Will use basic analysis instead")
    if not FLASK_AVAILABLE:
        print("❌ Flask not installed: pip install flask flask-socketio")
        return 1
    
    print("✅ All dependencies OK")
    print()
    
    # Configuration
    config = Config()
    print("⚙️  Configuration:")
    print(f"   Video source: {config.RTSP_URL}")
    print(f"   Process FPS: {config.PROCESS_FPS}")
    print(f"   YOLO model: {config.YOLO_MODEL}")
    print(f"   LLM provider: {config.LLM_PROVIDER}")
    print(f"   Web server: http://{config.WEB_HOST}:{config.WEB_PORT}")
    print()
    
    # Initialize processor
    print("🚀 Starting video processor...")
    processor = VideoProcessor(config)
    processor.start()
    
    # Start broadcast thread
    broadcast_thread = threading.Thread(target=broadcast_updates, daemon=True)
    broadcast_thread.start()
    
    print()
    print("=" * 70)
    print(f"🌐 Web interface: http://localhost:{config.WEB_PORT}")
    print(f"📊 API status: http://localhost:{config.WEB_PORT}/api/status")
    print("=" * 70)
    print()
    print("Press Ctrl+C to stop")
    print()
    
    try:
        # Start web server
        socketio.run(app, host=config.WEB_HOST, port=config.WEB_PORT, debug=False)
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping...")
        processor.stop()
        print("✅ Shutdown complete")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
