# YOLO11n + ByteTrack Tracking Benchmark

Standalone demo for testing the recommended AMD CPU/iGPU tracking stack:

- **YOLO11n** with OpenVINO acceleration
- **ByteTrack** via Supervision library
- **MOG2** motion gating to reduce detection frequency
- Threaded RTSP capture for live streams

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Test with webcam (with display + stats overlay)
python tracker_demo.py --source 0 --display --stats --trace

# Test with RTSP stream
python tracker_demo.py \
    --source "rtsp://admin:123456@192.168.188.146:554/h264Preview_01_sub" \
    --display --stats --trace

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

## Expected Performance (AMD Ryzen 7940HS)

| Metric | Value |
|--------|-------|
| YOLO11n detection | 18-22 FPS @ 640px |
| ByteTrack association | <1 ms |
| Motion gate savings | 60-80% fewer detections |
| **Total pipeline** | **15-20 FPS** sustained |

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

## Next Steps

Once you confirm this works well:

1. Compare tracking quality vs current ObjectTracker
2. Measure actual FPS on your RTSP stream
3. Proceed with integration into main streamware pipeline
