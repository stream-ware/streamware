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

## Configuration-Based Performance Tuning (NEW!)

All performance parameters are now configurable through environment variables:

### Detection Thresholds

```ini
# YOLO Detection Sensitivity
SQ_YOLO_CONFIDENCE_THRESHOLD=0.15     # Lower = more detections, slower
SQ_YOLO_CONFIDENCE_THRESHOLD_HIGH=0.3 # Higher = fewer false positives

# Motion Detection Sensitivity  
SQ_MOTION_DIFF_THRESHOLD=25           # Lower = more motion detected
SQ_MOTION_CONTOUR_MIN_AREA=100        # Higher = ignore small motion
```

### Resource Management

```ini
# Frame Processing
SQ_FRAME_SCALE=0.5                    # Process at 50% resolution
SQ_IMAGE_PRESET=fast                  # Smaller images for LLM
SQ_MAX_CONCURRENT_LLM=2               # Limit parallel LLM calls
SQ_MAX_FRAME_QUEUE=10                 # Limit frame buffer size
```

### Memory Optimization

```ini
# RAM Disk Configuration
SQ_RAMDISK_ENABLED=true               # Use RAM for temporary files
SQ_RAMDISK_SIZE_MB=512                # Allocate 512MB RAM disk
SQ_RAMDISK_PATH=/dev/shm/streamware   # Custom RAM disk path
```

**Performance Impact:**
- Lower thresholds = more accurate but slower
- Higher thresholds = faster but may miss detections
- RAM disk = 10x faster I/O for temporary files

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

## Timeout Optimization (NEW!)

Fine-tune LLM timeouts for your hardware and network conditions:

```ini
# Fast Hardware (GPU + Fast Network)
SQ_ANALYZE_TIMEOUT=5                  # Quick LLM analysis
SQ_SUMMARIZE_TIMEOUT=10               # Faster summarization
SQ_GUARDER_TIMEOUT=3                  # Quick guarder checks

# Standard Hardware (CPU + Average Network)
SQ_ANALYZE_TIMEOUT=8                  # Balanced timeouts
SQ_SUMMARIZE_TIMEOUT=15               # Standard summarization
SQ_GUARDER_TIMEOUT=5                  # Standard guarder checks

# Slow Hardware (Old CPU + Slow Network)
SQ_ANALYZE_TIMEOUT=15                 # Patient timeouts
SQ_SUMMARIZE_TIMEOUT=30               # Long summarization
SQ_GUARDER_TIMEOUT=10                 # Patient guarder checks
```

**Timeout Strategy:**

- **Too short**: Frequent timeouts, missed detections
- **Too long**: System hangs, poor user experience
- **Optimal**: 95% success rate, minimal wait time

**Monitoring Timeouts:**
```bash
# Check timeout performance
sq live narrator --url "rtsp://..." --verbose --log-format yaml
# Look for "timeout" in logs
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
