# ⚙️ Configuration Guide

Comprehensive configuration reference for Streamware after the recent refactoring.

**[← Back to Documentation](README.md)**

---

## Overview

Streamware has been fully refactored to eliminate hardcoded values and provide complete configurability through environment variables and `.env` files. All detection thresholds, timeouts, and model parameters can now be customized without code modifications.

## Configuration Files

### Primary Configuration: `.env`

All configuration is managed through environment variables. The system automatically loads from `.env` file in the project root.

### Default Values: `config.py`

Default values are defined in `streamware/config.py` for reference and fallback.

---

## 🎯 Detection Configuration

### YOLO Object Detection

```ini
# Detection sensitivity (lower = more sensitive)
SQ_YOLO_CONFIDENCE_THRESHOLD=0.15     # YOLO detection confidence threshold
SQ_YOLO_CONFIDENCE_THRESHOLD_HIGH=0.3 # Higher threshold for reducing false positives
```

**Impact:**

- Lower values detect more objects but may increase false positives
- Higher values reduce false positives but may miss small/distant objects

### HOG Person Detection

```ini
# HOG detection parameters
SQ_HOG_SCALE=400                      # Max dimension for HOG detection
SQ_HOG_WINSTRIDE=8                    # HOG detection window stride
SQ_HOG_PADDING=4                      # HOG detection padding
SQ_HOG_SCALE_FACTOR=1.05              # HOG detection scale factor
SQ_HOG_CONFIDENT_NO_PERSON=0.8        # Confidence when no person detected
SQ_HOG_MIGHT_BE_PERSON=0.5            # Confidence when might be person
```

### Motion Detection

```ini
# Motion detection thresholds
SQ_MOTION_DIFF_THRESHOLD=25           # OpenCV threshold for motion detection
SQ_MOTION_BLUR_KERNEL=5               # Gaussian blur kernel size
SQ_MOTION_CONTOUR_MIN_AREA=100        # Minimum contour area for motion regions
SQ_MOTION_SCALE_WIDTH=320             # Max width for motion detection scaling
SQ_MOTION_SCALE_HEIGHT=240            # Max height for motion detection scaling
SQ_MOTION_FIRST_FRAME_PERCENT=100.0   # Assume motion percent for first frame
SQ_MOTION_ERROR_PERCENT=50.0          # Motion error handling

# Motion classification thresholds
SQ_MOTION_MIN_PERCENT=0.5             # Minimum motion percent to consider
SQ_MOTION_LOW_PERCENT=1.0             # Low motion threshold
SQ_MOTION_MEDIUM_PERCENT=5.0          # Medium motion threshold
SQ_MOTION_HIGH_PERCENT=15.0           # High motion threshold
```

---

## ⏱️ Timeout Configuration

### Response Filter Timeouts

```ini
# Timeout values for various LLM operations (in seconds)
SQ_GUARDER_TIMEOUT=5                  # Timeout for guarder model availability check
SQ_QUICK_PERSON_TIMEOUT=10            # Timeout for quick person detection
SQ_QUICK_CHANGE_TIMEOUT=8             # Timeout for quick change detection
SQ_SUMMARIZE_TIMEOUT=15               # Timeout for detection summarization
SQ_VALIDATE_TIMEOUT=10                # Timeout for LLM validation
SQ_ANALYZE_TIMEOUT=8                  # Timeout for LLM analysis
SQ_ANALYZE_TRACKING_TIMEOUT=10        # Timeout for LLM analysis with tracking
```

### General Timeouts

```ini
# General system timeouts
SQ_LLM_TIMEOUT=30                     # Main LLM request timeout
SQ_CAPTURE_TIMEOUT=10                 # RTSP capture timeout
SQ_TTS_TIMEOUT=5                      # Text-to-speech timeout
```

---

## 🤖 Vision Model Configuration

### Model Selection

```ini
# Vision model for image analysis
SQ_MODEL=llava:7b                     # Default vision model
SQ_VISION_MODELS=llava,moondream,bakllava,llava-llama3,minicpm-v
```

### Confidence Thresholds

```ini
# Vision model confidence thresholds
SQ_VISION_ASSUME_PRESENT=0.5          # Default confidence when vision can't load
SQ_VISION_CONFIDENT_PRESENT=0.9       # Confidence for confident YES response
SQ_VISION_CONFIDENT_ABSENT=0.9        # Confidence for confident NO response
```

### Image Optimization

```ini
# Image preprocessing for vision models
SQ_IMAGE_PRESET=balanced              # Preset: fast, balanced, quality, minimal
SQ_IMAGE_MAX_SIZE=512                 # Max dimension in pixels
SQ_IMAGE_QUALITY=65                   # JPEG quality 1-100
SQ_IMAGE_POSTERIZE=0                  # 0=off, 8-256=reduce colors
SQ_IMAGE_GRAYSCALE=false              # Convert to grayscale
SQ_FRAME_SCALE=0.5                    # Frame scaling factor
```

---

## 🛡️ Guarder Filter Configuration

```ini
# Guarder model for response filtering
SQ_GUARDER_MODEL=gemma:2b             # Default guarder model
SQ_USE_GUARDER=true                   # Enable/disable guarder filter
SQ_ANALYSIS_MODEL=qwen2.5:3b          # Model for response analysis
```

**Guarder Filter Behavior:**

- Filters verbose vision model responses
- Provides YES/NO decisions for person detection
- Reduces false negatives in track mode
- Can be disabled with `--no-guarder` flag

---

## 🔄 Tracking Configuration

```ini
# Object tracking parameters
SQ_TRACK_MIN_STABLE_FRAMES=3          # Frames before track is stable
SQ_TRACK_BUFFER=90                    # Frames before deleting lost track
SQ_TRACK_ACTIVATION_THRESHOLD=0.25   # Min confidence for new tracks
SQ_TRACK_MATCHING_THRESHOLD=0.8       # IoU threshold for track matching

# Motion gating for tracking
SQ_MOTION_GATE_THRESHOLD=1000         # Min motion area to trigger detection
SQ_PERIODIC_INTERVAL=30               # Force detection every N frames
SQ_SKIP_INTERVAL=5                    # Skip LLM check interval in other modes
SQ_CONSECUTIVE_NO_TARGET_SKIP=5       # Skip every Nth frame when no target detected
```

---

## 🎤 TTS Configuration

```ini
# Text-to-speech settings
SQ_TTS_ENGINE=auto                    # auto, pyttsx3, espeak, say, powershell
SQ_TTS_VOICE=                         # Voice name fragment
SQ_TTS_RATE=150                       # Speech rate (words per minute)

# Speech-to-text settings
SQ_STT_PROVIDER=google                # google, whisper_local, whisper_api
SQ_WHISPER_MODEL=small                # tiny, base, small, medium, large
```

---

## 📡 Network Configuration

```ini
# Ollama configuration
SQ_OLLAMA_URL=http://localhost:11434   # Ollama server URL

# RTSP configuration
SQ_RTSP_TIMEOUT=10                    # RTSP connection timeout
SQ_RTSP_RECONNECT_DELAY=5             # Delay between reconnection attempts
SQ_CAPTURE_FPS=1                      # Default capture FPS
SQ_FAST_CAPTURE=true                  # Enable fast capture mode
```

---

## 🗄️ Storage Configuration

```ini
# RAM disk configuration
SQ_RAMDISK_PATH=/dev/shm/streamware   # RAM disk path for fast I/O
SQ_RAMDISK_ENABLED=true               # Enable/disable RAM disk
SQ_RAMDISK_SIZE_MB=512                # RAM disk size in MB
```

---

## 📊 Logging Configuration

```ini
# Logging settings
SQ_LOG_LEVEL=INFO                     # DEBUG, INFO, WARNING, ERROR
SQ_LOG_FILE=                          # Log file path (empty = stdout only)
SQ_LOG_FORMAT=yaml                    # Log format: text, yaml, json
SQ_TIMING_ENABLED=true                # Enable timing logs
SQ_PERFORMANCE_ENABLED=true           # Enable performance metrics
```

---

## 🧪 Performance Configuration

### Optimization Presets

```ini
# Performance optimization
SQ_LLM_MIN_MOTION_PERCENT=30          # Minimum motion to trigger LLM
SQ_FAST_CAPTURE=true                  # Persistent RTSP connection
SQ_STREAM_MODE=track                  # Smart movement tracking
SQ_STREAM_FOCUS=person                # Focus on person detection
```

### Resource Limits

```ini
# Resource management
SQ_MAX_CONCURRENT_LLM=2               # Maximum concurrent LLM requests
SQ_MAX_FRAME_QUEUE=10                 # Maximum frame queue size
SQ_CLEANUP_INTERVAL=60                # Cleanup interval in seconds
```

---

## 🔧 Advanced Configuration

### Custom Prompts

```ini
# Custom prompt templates (override defaults)
SQ_PROMPT_STREAM_DIFF=                # Custom stream diff prompt
SQ_PROMPT_STREAM_FOCUS=               # Custom stream focus prompt
SQ_PROMPT_TRIGGER_CHECK=              # Custom trigger check prompt
SQ_PROMPT_MOTION_REGION=              # Custom motion region prompt
SQ_PROMPT_TRACKING_DETECT=            # Custom tracking detection prompt
SQ_PROMPT_LIVE_NARRATOR_TRACK=        # Custom live narrator track prompt
```

### Feature Flags

```ini
# Enable/disable features
SQ_USE_SMART_DETECTOR=true            # Enable smart detector
SQ_USE_RESPONSE_FILTER=true           # Enable response filter
SQ_USE_IMAGE_OPTIMIZATION=true        # Enable image optimization
SQ_USE_ASYNC_LLM=true                 # Enable async LLM processing
SQ_USE_MOTION_GATING=true             # Enable motion gating
```

---

## 📝 Configuration Examples

### High Performance Setup

```ini
# Optimized for speed and low resource usage
SQ_MODEL=moondream
SQ_IMAGE_PRESET=fast
SQ_YOLO_CONFIDENCE_THRESHOLD=0.2
SQ_LLM_MIN_MOTION_PERCENT=50
SQ_RAMDISK_SIZE_MB=256
SQ_TTS_ENGINE=espeak
```

### High Accuracy Setup

```ini
# Optimized for maximum accuracy
SQ_MODEL=llava:13b
SQ_IMAGE_PRESET=quality
SQ_YOLO_CONFIDENCE_THRESHOLD=0.1
SQ_VISION_CONFIDENT_PRESENT=0.95
SQ_TRACK_MIN_STABLE_FRAMES=5
SQ_TRACK_BUFFER=120
```

### Low Resource Setup

```ini
# Optimized for systems with limited resources
SQ_MODEL=moondream
SQ_IMAGE_PRESET=minimal
SQ_FRAME_SCALE=0.25
SQ_RAMDISK_SIZE_MB=128
SQ_MAX_CONCURRENT_LLM=1
SQ_USE_ASYNC_LLM=false
```

---

## 🔄 Configuration Reload

Most configuration changes require restarting the application:

```bash
# Restart live narrator with new configuration
sq live narrator --url "rtsp://..." --restart
```

Some settings can be changed at runtime:

- Log level
- TTS voice and rate
- Image optimization preset

---

## 🐛 Troubleshooting Configuration

### Common Issues

1. **High false positive rate:**

   ```ini
   SQ_YOLO_CONFIDENCE_THRESHOLD=0.3
   SQ_VISION_CONFIDENT_PRESENT=0.95
   ```

2. **Missing detections:**

   ```ini
   SQ_YOLO_CONFIDENCE_THRESHOLD=0.1
   SQ_VISION_CONFIDENT_PRESENT=0.8
   ```

3. **Slow performance:**

   ```ini
   SQ_MODEL=moondream
   SQ_IMAGE_PRESET=fast
   SQ_LLM_MIN_MOTION_PERCENT=50
   ```

4. **Memory issues:**

   ```ini
   SQ_RAMDISK_SIZE_MB=128
   SQ_MAX_FRAME_QUEUE=5
   SQ_MAX_CONCURRENT_LLM=1
   ```

### Validation

```bash
# Check configuration
sq --check config

# Test specific settings
sq --check camera "rtsp://..."
sq --check tts
sq --check ollama
```

---

## 📚 Related Documentation

- [🏗️ Architecture](ARCHITECTURE.md)
- [🤖 LLM Integration](LLM_INTEGRATION.md)
- [⚡ Performance](PERFORMANCE.md)
- [🎯 Motion Analysis](MOTION_ANALYSIS.md)
- [📡 API Reference](API.md)

---

**Last Updated:** December 2024 (Post-Refactoring v2.0)
