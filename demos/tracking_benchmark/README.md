# YOLO11n + ByteTrack Tracking Benchmark

Standalone demo for testing the recommended AMD CPU/iGPU tracking stack:

- **YOLO11n** with OpenVINO acceleration (or PyTorch)
- **ByteTrack** via Supervision library
- **MOG2** motion gating to reduce detection frequency
- Track state management (new/stable/lost)
- Threaded RTSP capture for live streams

## Benchmark Results (AMD Ryzen 7940HS)

**Tested on 640x480 RTSP stream @ 10 FPS:**

| Metric | Value |
|--------|-------|
| **YOLO11n detection** | ~10-12ms (PyTorch) |
| **Full pipeline** | 74+ FPS capability |
| **Motion gate savings** | 45-86% fewer detections |
| **Track events** | Enter/leave detection working |

**Key findings:**
- PyTorch is already very fast (~10ms), OpenVINO optional
- Motion gating is highly effective
- ByteTrack provides stable track IDs
- FPS limited by source stream, not detection

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Test with webcam (with display + stats overlay)
python tracker_demo.py --source 0 --display --stats --trace

# Test with RTSP stream (15 second benchmark)
python tracker_demo.py \
    --source "rtsp://user:pass@ip:554/stream" \
    --no-openvino --duration 15 --stats

# Process video file and save output
python tracker_demo.py \
    --source input.mp4 \
    --output result.mp4 \
    --stats
```

## Key Options

| Option | Description | Default |
|--------|-------------|---------|
| `--source`, `-s` | Video source (file, RTSP URL, webcam index) | required |
| `--display`, `-d` | Show live window | off |
| `--output`, `-o` | Save output video | none |
| `--model`, `-m` | YOLO model path | `yolo11n.pt` |
| `--no-openvino` | Disable OpenVINO (use PyTorch) | off |
| `--imgsz` | Detection input size | 640 |
| `--conf` | Confidence threshold | 0.5 |
| `--motion-threshold` | Pixels to trigger detection | 1000 |
| `--periodic-interval` | Force detection every N frames | 30 |
| `--track-buffer` | Frames before deleting lost track | 90 |
| `--trace` | Show movement traces | off |
| `--stats` | Show FPS/detection stats overlay | off |
| `--duration` | Limit benchmark to N seconds | 0 (unlimited) |
| `--max-frames` | Limit benchmark to N frames | 0 (unlimited) |

## Keyboard Shortcuts (with `--display`)

- `q` - Quit
- `s` - Save screenshot

## Tuning Tips

### Too many false detections?

- Increase `--conf` to 0.6-0.7
- Increase `--motion-threshold` to 2000-3000

### Tracks lost too quickly?

- Increase `--track-buffer` to 120-150 (4-5 sec at 30 FPS)
- Decrease `--periodic-interval` to 15-20

### Low FPS?

- Use `--imgsz 480` for faster detection
- Increase `--motion-threshold` to reduce detection frequency

## Integration Recommendations

Based on benchmark results, for stream-ware integration:

1. **Replace ObjectTracker** with ByteTrack via Supervision
2. **Keep PyTorch** backend (fast enough, simpler than OpenVINO)
3. **Wire motion gating** from FrameDiffAnalyzer to control YOLO calls
4. **Use track state events** (new/lost) for TTS announcements
