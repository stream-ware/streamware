# 🎥 Video Captioning System - Complete Project

Real-time video captioning using Streamware Quick commands.

**Features:**
- ✅ RTSP stream reading
- ✅ YOLO object detection
- ✅ AI-powered captions (LLM)
- ✅ Real-time web interface
- ✅ Live text streaming
- ✅ All in Streamware Quick style

## 📦 Quick Start (3 commands!)

```bash
# 1. Install dependencies
bash install.sh

# 2. Start video captioning
python video_captioning_complete.py

# 3. Open browser
open http://localhost:8080
```

## 🚀 Complete Installation Guide

### Step 1: Install System Dependencies

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3-opencv ffmpeg

# macOS
brew install opencv ffmpeg

# Windows
# Download from opencv.org
```

### Step 2: Install Python Packages

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install all dependencies
pip install opencv-python numpy
pip install ultralytics  # YOLO
pip install flask flask-socketio
pip install openai anthropic  # Optional: for cloud LLM

# Install Ollama (FREE, local LLM)
curl https://ollama.ai/install.sh | sh
ollama pull llama3.2
```

### Step 3: Setup Video Source

#### Option A: Use Test RTSP Stream

```bash
# Start RTSP mock server (Docker)
docker run -d \
  --name rtsp-server \
  -p 8554:8554 \
  aler9/rtsp-simple-server

# Stream test video
ffmpeg -re -stream_loop -1 \
  -i test_video.mp4 \
  -f rtsp rtsp://localhost:8554/stream
```

#### Option B: Use Webcam

```python
# Edit video_captioning_complete.py
RTSP_URL = "0"  # Use webcam
```

#### Option C: Use Real RTSP Camera

```python
# Edit video_captioning_complete.py
RTSP_URL = "rtsp://username:password@camera-ip:554/stream"
```

### Step 4: Run the System

```bash
python video_captioning_complete.py
```

**Output:**
```
====================================================================
STREAMWARE VIDEO CAPTIONING SYSTEM
====================================================================

📦 Checking dependencies...
✅ All dependencies OK

⚙️  Configuration:
   Video source: rtsp://localhost:8554/stream
   Process FPS: 1
   YOLO model: yolov8n.pt
   LLM provider: ollama
   Web server: http://0.0.0.0:8080

🚀 Starting video processor...
📦 Loading YOLO model: yolov8n.pt
🎥 Video processing started
🔌 Connecting to video source...
✅ Connected to video source

====================================================================
🌐 Web interface: http://localhost:8080
📊 API status: http://localhost:8080/api/status
====================================================================
```

### Step 5: Open Web Interface

```bash
open http://localhost:8080
```

You'll see:
- Live video stream with object detection boxes
- Real-time AI captions
- Object detection statistics
- Detected objects list

## 🎯 Usage Examples

### Example 1: Basic Usage

```bash
# Default configuration (RTSP)
python video_captioning_complete.py
```

### Example 2: Use Webcam

```bash
# Edit config in code:
RTSP_URL = "0"

python video_captioning_complete.py
```

### Example 3: Use Video File

```bash
# Edit config:
RTSP_URL = "/path/to/video.mp4"

python video_captioning_complete.py
```

### Example 4: Custom Configuration

```python
# Edit Config class in video_captioning_complete.py

class Config:
    RTSP_URL = "rtsp://your-camera-ip/stream"
    PROCESS_FPS = 2  # Process 2 frames per second
    YOLO_MODEL = "yolov8m.pt"  # Medium model (better accuracy)
    YOLO_CONFIDENCE = 0.6
    YOLO_CLASSES = ["person", "car", "dog"]  # Only detect these
    LLM_PROVIDER = "openai"  # Use OpenAI instead of Ollama
    CAPTION_INTERVAL = 3  # Caption every 3 seconds
    WEB_PORT = 9000
```

## 🐳 Docker Deployment

### Build and Run

```bash
# Build image
docker build -t streamware-video-captioning .

# Run container
docker run -d \
  --name video-captioning \
  -p 8080:8080 \
  -e RTSP_URL="rtsp://your-camera/stream" \
  -e LLM_PROVIDER="ollama" \
  streamware-video-captioning

# View logs
docker logs -f video-captioning

# Open browser
open http://localhost:8080
```

### Docker Compose

```yaml
version: '3.8'

services:
  video-captioning:
    build: .
    ports:
      - "8080:8080"
    environment:
      - RTSP_URL=rtsp://camera.example.com/stream
      - LLM_PROVIDER=ollama
      - YOLO_MODEL=yolov8n.pt
    volumes:
      - ./logs:/tmp
    restart: unless-stopped
  
  rtsp-server:
    image: aler9/rtsp-simple-server
    ports:
      - "8554:8554"
  
  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama

volumes:
  ollama-data:
```

## 📊 API Endpoints

### GET /
Main web interface with live video and captions

### GET /video_feed
MJPEG stream with detection overlay

### GET /api/status
JSON status information

```bash
curl http://localhost:8080/api/status

# Response:
{
  "running": true,
  "frame_count": 1234,
  "detections": 3,
  "caption": "A person walking with a dog on the street"
}
```

## 🔧 Configuration Options

### Video Source

```python
RTSP_URL = "rtsp://camera/stream"  # RTSP camera
RTSP_URL = "0"                      # Webcam
RTSP_URL = "/path/to/video.mp4"   # Video file
RTSP_URL = "http://url/stream"     # HTTP stream
```

### Processing

```python
PROCESS_FPS = 1          # Frames per second to process
SKIP_FRAMES = 30         # Skip N frames between processing
YOLO_CONFIDENCE = 0.5    # Detection confidence threshold
YOLO_CLASSES = None      # None = all, or ["person", "car"]
```

### LLM Providers

```python
# Ollama (FREE, local)
LLM_PROVIDER = "ollama"
LLM_MODEL = "llama3.2:latest"

# OpenAI (paid, best quality)
LLM_PROVIDER = "openai"
export OPENAI_API_KEY="sk-..."

# Anthropic (paid)
LLM_PROVIDER = "anthropic"
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Web Server

```python
WEB_HOST = "0.0.0.0"     # Listen on all interfaces
WEB_PORT = 8080          # Port number
```

## 📝 Streamware Quick Commands

The system uses Streamware Quick style internally:

```bash
# Video capture
sq video rtsp://camera/stream --fps 1

# Object detection
sq video --detect --model yolov8n.pt --confidence 0.5

# Caption generation
sq llm "Scene contains 2 persons, 1 car" --generate --provider ollama

# Web streaming
sq http --serve --port 8080 --stream video
```

## 🎓 How It Works

### Architecture

```
RTSP Stream
    ↓
Video Capture (OpenCV)
    ↓
Frame Processing (1 FPS)
    ↓
Object Detection (YOLO)
    ↓
Caption Generation (LLM)
    ↓
Web Streaming (Flask + WebSockets)
    ↓
Browser Display
```

### Processing Pipeline

1. **Video Input**: Read frames from RTSP stream
2. **Frame Selection**: Process 1 frame per second
3. **Object Detection**: YOLO detects objects in frame
4. **Caption Generation**: LLM generates natural language description
5. **Overlay**: Draw boxes and caption on frame
6. **Streaming**: Stream to web clients via MJPEG
7. **Updates**: Push captions to clients via WebSockets

## 🐛 Troubleshooting

### Error: "Failed to open video source"

```bash
# Check RTSP stream
ffplay rtsp://your-camera/stream

# Test with VLC
vlc rtsp://your-camera/stream

# Check firewall
sudo ufw allow 8554
```

### Error: "YOLO model not found"

```bash
# Download YOLO model manually
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt

# Or let it auto-download on first run
```

### Error: "Ollama not available"

```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Pull model
ollama pull llama3.2

# Check service
ollama list
```

### Error: "Port 8080 already in use"

```bash
# Change port in Config
WEB_PORT = 9000

# Or kill existing process
sudo lsof -ti:8080 | xargs kill -9
```

### Low FPS / Slow Processing

```bash
# Use lighter YOLO model
YOLO_MODEL = "yolov8n.pt"  # Nano (fastest)

# Reduce processing rate
PROCESS_FPS = 0.5  # Process every 2 seconds

# Skip more frames
SKIP_FRAMES = 60

# Disable caption generation temporarily
CAPTION_INTERVAL = 999999
```

## 📊 Performance

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| RAM | 4 GB | 8+ GB |
| GPU | None | CUDA GPU |
| Storage | 2 GB | 10 GB |

### Benchmarks

| Model | FPS | Latency | Accuracy |
|-------|-----|---------|----------|
| YOLOv8n | 30+ | ~30ms | Good |
| YOLOv8s | 20+ | ~50ms | Better |
| YOLOv8m | 10+ | ~100ms | Best |

## 🎬 Demo Videos

### Test with Sample Video

```bash
# Download test video
wget https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4 \
     -O test.mp4

# Stream it
ffmpeg -re -stream_loop -1 -i test.mp4 \
  -f rtsp rtsp://localhost:8554/stream

# Run captioning
python video_captioning_complete.py
```

## 🚀 Production Deployment

### Systemd Service

```bash
# Create service file
sudo tee /etc/systemd/system/video-captioning.service << EOF
[Unit]
Description=Streamware Video Captioning
After=network.target

[Service]
Type=simple
User=streamware
WorkingDirectory=/opt/video-captioning
ExecStart=/opt/video-captioning/venv/bin/python video_captioning_complete.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl enable video-captioning
sudo systemctl start video-captioning

# Check status
sudo systemctl status video-captioning
```

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name video.example.com;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

### SSL with Let's Encrypt

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d video.example.com
```

## 📚 Additional Resources

- **Streamware Docs**: [docs/](../../docs/)
- **YOLO Docs**: https://docs.ultralytics.com
- **OpenCV Docs**: https://docs.opencv.org
- **Ollama**: https://ollama.ai

## 🤝 Contributing

Found a bug or want to add a feature? Open an issue or PR!

## 📄 License

Apache 2.0

---

**Built with ❤️ using Streamware**

For support: info@softreck.com
