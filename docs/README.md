# 📚 StreamWare Documentation

Welcome to StreamWare documentation. This guide covers all features for real-time video analysis with AI.

## 📋 Table of Contents

### Getting Started
- [Installation](../README.md#installation)
- [Quick Start](../README.md#quick-start)

### Core Features
- [🎬 Real-time DSL Streaming](REALTIME_STREAMING.md) - Live motion visualization in browser
- [⚡ Performance Optimization](PERFORMANCE.md) - GPU acceleration, timing logs, benchmarks
- [🤖 LLM Integration](LLM_INTEGRATION.md) - Vision models, async inference
- [🎯 Motion Analysis](MOTION_ANALYSIS.md) - DSL-based tracking, blob detection

### Architecture
- [🏗️ System Architecture](ARCHITECTURE.md) - Multiprocessing, data flow
- [📡 API Reference](API.md) - CLI options, configuration

### Development
- [🔧 Refactoring Plan](REFACTORING_PLAN.md) - Tracking optimization roadmap

### Deployment
- [💾 USB/ISO Builder](USB_ISO_BUILDER.md) - Bootable offline LLM environments

---

## 🚀 Quick Reference

### Basic Commands

```bash
# Real-time viewer with LLM (recommended)
sq live narrator --url "rtsp://..." --realtime --turbo --fps 5

# DSL-only mode (fastest, no LLM)
sq live narrator --url "rtsp://..." --dsl-only --realtime --fps 20

# Full analysis with TTS
sq live narrator --url "rtsp://..." --mode track --tts
```

### Key Options

| Option | Description |
|--------|-------------|
| `--realtime` | Enable browser viewer at http://localhost:8766 |
| `--dsl-only` | Skip LLM, use only OpenCV tracking |
| `--fps N` | Target frames per second |
| `--turbo` | Skip checks + fast model + aggressive caching |
| `--verbose` | Show detailed timing logs |

### Performance Modes

| Mode | FPS | LLM | Use Case |
|------|-----|-----|----------|
| `--dsl-only --fps 20` | 20 | ❌ | Fast motion detection |
| `--realtime --fps 5` | 5 | ✅ (async) | Balanced analysis |
| `--turbo` | 2-5 | ✅ (fast) | Quick setup |

---

## 📁 File Structure

```
streamware/
├── docs/                      # 📚 Documentation
│   ├── README.md              # This file
│   ├── REALTIME_STREAMING.md  # Real-time viewer guide
│   ├── PERFORMANCE.md         # Performance optimization
│   ├── LLM_INTEGRATION.md     # LLM configuration
│   ├── MOTION_ANALYSIS.md     # Motion tracking
│   └── ARCHITECTURE.md        # System design
├── streamware/
│   ├── components/
│   │   └── live_narrator.py   # Main narrator component
│   ├── frame_diff_dsl.py      # DSL motion analysis
│   ├── dsl_streamer_process.py # Separate DSL process
│   ├── realtime_dsl_server.py # WebSocket server
│   ├── fast_capture.py        # RTSP capture
│   ├── dsl_timing_logger.py   # Performance logging
│   └── async_llm.py           # Async LLM inference
└── README.md                  # Project overview
```

---

## 🔗 Related Links

- [GitHub Repository](https://github.com/tom/stream-ware)
- [Main README](../README.md)
