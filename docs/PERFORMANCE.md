# ⚡ Performance Optimization

Guide to optimizing StreamWare for maximum performance.

**[← Back to Documentation](README.md)**

---

## Overview

StreamWare is optimized for real-time video analysis. This guide covers timing analysis, GPU acceleration, and performance tuning.

## Performance Modes

### Turbo Mode (Recommended)

```bash
sq live narrator --url "rtsp://..." --turbo
```

Enables:
- Skip dependency checks
- Fast model selection (moondream → llava:7b)
- Aggressive caching
- Optimized intervals

### DSL-Only Mode (Fastest)

```bash
sq live narrator --url "rtsp://..." --dsl-only --realtime --fps 20
```

- **No LLM calls** - Pure OpenCV processing
- **~10ms per frame** - Up to 100 FPS theoretical
- **Ideal for** - Motion detection without AI descriptions

### Real-time Mode

```bash
sq live narrator --url "rtsp://..." --realtime --fps 5
```

- **Separate DSL process** - Smooth browser updates
- **Async LLM** - Non-blocking inference
- **Balanced** - Good quality + good speed

## Timing Logs

### Enable CSV Logging

Timing logs are automatically generated in real-time mode:

```bash
sq live narrator --url "rtsp://..." --realtime --turbo
# Creates: dsl_timing_*.csv
```

### CSV Format

```csv
frame_num,timestamp,total_ms,capture_ms,grayscale_ms,blur_ms,diff_ms,threshold_ms,contours_ms,tracking_ms,thumbnail_ms,blobs,motion_pct
1,16:43:24.463,18.3,1.7,0.2,0.3,13.0,0.8,0.2,0.0,0.7,0,100.00
2,16:43:26.467,10.8,1.7,0.2,0.2,5.5,0.7,0.1,0.0,0.6,2,0.94
```

### Real-time Console Output

```
⏱️ F1: 18ms total | 0 blobs | 100.0% motion | blur:0ms | capture:2ms | diff:13ms
⏱️ F2: 11ms total | 2 blobs | 0.9% motion | blur:0ms | capture:2ms | diff:6ms
```

## Bottleneck Analysis

### Typical Frame Timing

| Step | Time | % Total |
|------|------|---------|
| **diff** (background subtraction) | 5-15ms | 50-70% |
| capture | 1-2ms | 10-20% |
| threshold | 0.5-1ms | 5-10% |
| thumbnail | 0.5-1ms | 5-10% |
| blur/grayscale | 0.2-0.5ms | 2-5% |

### LLM Timing

| Model | Typical | Notes |
|-------|---------|-------|
| moondream | 300-800ms | Fastest |
| llava:7b | 800-2000ms | Good quality |
| llava:13b | 2000-5000ms | Best quality |

## GPU Acceleration

### What Uses GPU

| Component | GPU | Notes |
|-----------|-----|-------|
| YOLO detection | ✅ | CUDA acceleration |
| Ollama LLM | ✅ | GPU inference |
| OpenCV DSL | ❌ | CPU only |
| FastCapture | ⚠️ | Optional NVDEC |

### Check GPU Usage

```bash
# Monitor GPU
watch -n 1 nvidia-smi

# Check Ollama GPU
curl http://localhost:11434/api/tags | jq
```

### Enable GPU for Capture

```bash
export SQ_CAPTURE_BACKEND=opencv  # Uses CUDA if available
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SQ_FAST_CAPTURE` | true | Use FastCapture |
| `SQ_RAMDISK_PATH` | /dev/shm/streamware | Frame storage |
| `SQ_CAPTURE_BACKEND` | auto | opencv/ffmpeg |
| `SQ_GUARDER_MODEL` | gemma:2b | Filter model |

### Recommended Settings

```bash
# High performance
export SQ_FAST_CAPTURE=true
export SQ_RAMDISK_PATH=/dev/shm/streamware

# Memory optimization
export SQ_LITE_MODE=true
```

## Benchmarks

### DSL Analysis (640x480)

```
Average: 10-15ms per frame
Effective FPS: 65-100 FPS (theoretical)
Bottleneck: Background subtraction (diff)
```

### LLM Analysis

```
moondream:  ~500ms (2 FPS)
llava:7b:   ~1200ms (0.8 FPS)  
llava:13b:  ~3000ms (0.3 FPS)
```

### Combined (Real-time mode)

```
DSL streaming: 5-20 FPS (smooth)
LLM analysis:  0.3-1 FPS (background)
```

## Tips

### Reduce Latency

1. Use `--turbo` mode
2. Lower resolution: camera sub-stream
3. Use RAM disk (default)
4. Reduce FPS if not needed

### Reduce CPU Usage

1. Use `--dsl-only` when AI not needed
2. Lower `--fps` value
3. Disable verbose logging

### Reduce Memory

1. Use `--lite` mode
2. Smaller buffer: `buffer_size=3`
3. Lower resolution

---

**Related:**
- [Real-time Streaming](REALTIME_STREAMING.md)
- [LLM Integration](LLM_INTEGRATION.md)
- [Back to Documentation](README.md)
