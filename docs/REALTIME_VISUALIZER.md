# Real-time Motion Visualizer

Real-time video analysis with motion detection, SVG overlays, and DSL metadata streaming.

## Quick Start

```bash
# Basic usage - WebSocket mode (lowest latency)
sq visualize --url "rtsp://admin:password@camera-ip:554/stream" --port 8080

# Open http://localhost:8080 in browser
```

## Video Modes

| Mode | Description | Latency | Use Case |
|------|-------------|---------|----------|
| `ws` | JPEG over WebSocket | ~100ms | Default, full video |
| `hls` | HTTP Live Streaming | ~2-5s | Stable, compatible |
| `meta` | Metadata only + 1 FPS preview | ~50ms | Low bandwidth, logging |
| `webrtc` | WebRTC (experimental) | ~50ms | Ultra-low latency |

```bash
# Metadata-only mode (high FPS analysis, minimal bandwidth)
sq visualize --url "rtsp://..." --port 8080 --video-mode meta --fps 10

# HLS mode (stable streaming)
sq visualize --url "rtsp://..." --port 8080 --video-mode hls
```

## Transport Options

| Transport | Latency | Stability |
|-----------|---------|-----------|
| `tcp` | ~100-200ms | High |
| `udp` | ~50-100ms | May drop frames |

```bash
# UDP for lowest latency
sq visualize --url "rtsp://..." --transport udp
```

## Capture Backends

| Backend | Description | Latency | Requirements |
|---------|-------------|---------|--------------|
| `opencv` | OpenCV + ffmpeg | ~100-200ms | opencv-python |
| `gstreamer` | GStreamer pipeline | ~50-100ms | OpenCV with GStreamer |
| `pyav` | Direct ffmpeg API | ~50-80ms | `pip install av` |

```bash
# PyAV backend (no subprocess overhead)
sq visualize --url "rtsp://..." --backend pyav

# GStreamer (requires OpenCV with GStreamer support)
sq visualize --url "rtsp://..." --backend gstreamer
```

## Lowest Latency Configuration

```bash
sq visualize \
  --url "rtsp://admin:password@camera:554/stream" \
  --port 8080 \
  --video-mode meta \
  --fps 15 \
  --transport udp \
  --backend pyav \
  --width 320 \
  --height 240
```

## All Options

```
sq visualize --help

Options:
  --url, -u URL         RTSP stream URL (required)
  --port, -p PORT       HTTP server port (default: 8080)
  --fps FPS             Frames per second (default: 1)
  --width WIDTH         Frame width (default: 320)
  --height HEIGHT       Frame height (default: 240)
  --video-mode MODE     ws, hls, meta, webrtc (default: ws)
  --transport TRANSPORT tcp, udp (default: tcp)
  --backend BACKEND     opencv, gstreamer, pyav (default: opencv)
  --simple              Use simple HTTP server (no WebSocket)
  --fast                Fast mode: lower resolution, higher FPS
```

## Browser Interface

The web interface shows:
- **Live Video** - Real-time video stream with SVG overlay
- **SVG Overlay** - Motion detection bounding boxes and vectors
- **DSL Metadata** - Structured motion events in real-time
- **Statistics** - Motion %, object count, FPS, latency

### Controls
- **Overlay ON/OFF** - Toggle motion overlay
- **Copy Logs** - Copy DSL to clipboard
- **Save DSL** - Download motion analysis file

## DSL Output Format

```
FRAME 1234 @ 23:15:45.123
  MOTION 15.7% (HIGH)
  BLOB id=1 pos=(0.45,0.32) size=(0.12,0.18) area=2.16% quadrant=CENTER
  BLOB id=2 pos=(0.78,0.65) size=(0.08,0.10) area=0.80% quadrant=BOTTOM-RIGHT
  EVENT motion_detected level=HIGH objects=2
```

## Programmatic Usage

```python
from streamware.realtime_visualizer import start_visualizer

# Start visualizer
start_visualizer(
    rtsp_url="rtsp://admin:password@camera:554/stream",
    port=8080,
    fps=5.0,
    width=320,
    height=240,
    video_mode="meta",
    transport="udp",
    backend="pyav",
)
```

## Performance Tips

1. **Lower resolution** - Use 320x240 for faster processing
2. **UDP transport** - Lower latency but may drop frames
3. **PyAV backend** - No subprocess overhead
4. **Metadata mode** - Minimal bandwidth, high FPS analysis
5. **Flush buffers** - Automatic at startup to remove stale frames

## Troubleshooting

### High Latency (>1s)
- Use `--transport udp`
- Use `--backend pyav`
- Lower resolution: `--width 320 --height 240`
- Check camera settings (keyframe interval, bitrate)

### H.264 Decode Errors
- Errors are automatically suppressed
- If persistent, check camera stream compatibility

### Connection Failed
- Verify RTSP URL is correct
- Check network connectivity
- Try `--transport tcp` if UDP fails

## See Also

- [MQTT DSL Publisher](./MQTT_PUBLISHER.md)
- [Examples](../examples/media-processing/)
