# Video Captioning - Quick Usage Guide

Ultra-fast start guide using Streamware Quick commands.

## ⚡ 3-Step Start

```bash
# 1. Install
bash install.sh

# 2. Run
./run.sh

# 3. Open
open http://localhost:8080
```

## 🎯 Quick Examples

### Example 1: Webcam

```bash
# Edit config
export RTSP_URL="0"

# Run
python video_captioning_complete.py
```

### Example 2: Video File

```bash
# Use your video
export RTSP_URL="/path/to/video.mp4"

python video_captioning_complete.py
```

### Example 3: RTSP Camera

```bash
# Real camera
export RTSP_URL="rtsp://user:pass@192.168.1.100:554/stream"

python video_captioning_complete.py
```

### Example 4: Docker One-Liner

```bash
docker run -d -p 8080:8080 \
  -e RTSP_URL="rtsp://camera/stream" \
  streamware-video-captioning
```

## 🔧 Quick Configuration

```bash
# Fast config
export RTSP_URL="0"                    # Webcam
export LLM_PROVIDER="ollama"           # Free LLM
export YOLO_MODEL="yolov8n.pt"        # Fast model
export WEB_PORT=8080                   # Port

python video_captioning_complete.py
```

## 📊 Test Without Camera

```bash
# Start mock RTSP
docker run -d -p 8554:8554 aler9/rtsp-simple-server

# Stream test video
ffmpeg -re -stream_loop -1 \
  -i test_data/test_video.mp4 \
  -f rtsp rtsp://localhost:8554/stream &

# Run captioning
export RTSP_URL="rtsp://localhost:8554/stream"
python video_captioning_complete.py
```

## 🚀 Production Quick Setup

```bash
# Install as service
sudo cp video-captioning.service /etc/systemd/system/
sudo systemctl enable video-captioning
sudo systemctl start video-captioning

# Check status
sudo systemctl status video-captioning
```

## 💡 Quick Tips

```bash
# Better accuracy (slower)
export YOLO_MODEL="yolov8m.pt"

# Faster processing
export PROCESS_FPS=0.5

# Only detect people
export YOLO_CLASSES="person"

# Use OpenAI (better captions)
export LLM_PROVIDER="openai"
export OPENAI_API_KEY="sk-..."
```

## 🐛 Quick Fixes

```bash
# Can't connect to camera?
ffplay rtsp://your-camera/stream

# YOLO too slow?
export YOLO_MODEL="yolov8n.pt"

# Ollama not working?
ollama pull llama3.2
ollama list

# Port in use?
export WEB_PORT=9000
```

## 📱 Access from Phone

```bash
# Find your IP
ip addr show | grep inet

# Access from phone
http://192.168.1.100:8080
```

## 🎬 Record Output

```bash
# Save video with captions
ffmpeg -i http://localhost:8080/video_feed \
  -c copy output.mp4
```

## 🔄 Auto-restart

```bash
# Keep running forever
while true; do
    python video_captioning_complete.py
    sleep 5
done
```

---

**That's it! Simple and fast!** 🚀
