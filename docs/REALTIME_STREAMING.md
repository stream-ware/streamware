# 🎬 Real-time DSL Streaming

Real-time motion visualization in browser using WebSocket streaming.

**[← Back to Documentation](README.md)**

---

## Overview

StreamWare provides real-time motion analysis visualization through a browser-based viewer. The system uses a separate process architecture to ensure smooth streaming regardless of LLM processing speed.

## Architecture

```
┌─────────────────────────────┐    ┌─────────────────────────────┐
│     MAIN PROCESS            │    │   DSL STREAMER PROCESS      │
│                             │    │   (Isolated)                │
├─────────────────────────────┤    ├─────────────────────────────┤
│                             │    │ FastCapture (5-20 FPS)      │
│  LLM Analysis               │    │     │                       │
│  (~1-4s per frame)          │    │     ▼                       │
│                             │    │ DSL Analysis (~10ms)        │
│  - Throttled rate           │    │     │                       │
│  - Background thread        │    │     ▼                       │
│                             │    │ WebSocket → Browser :8766   │
└─────────────────────────────┘    └─────────────────────────────┘
```

## Quick Start

### Basic Real-time Mode

```bash
# Start with real-time viewer
sq live narrator --url "rtsp://camera_ip/stream" --realtime --turbo

# Open browser
open http://localhost:8766
```

### DSL-Only Mode (Fastest)

```bash
# No LLM, maximum FPS
sq live narrator --url "rtsp://..." --dsl-only --realtime --fps 20
```

### With LLM Analysis

```bash
# Real-time viewer + async LLM
sq live narrator --url "rtsp://..." --realtime --turbo --fps 5
```

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `--realtime` | off | Enable WebSocket streaming |
| `--fps N` | 2 | Target frames per second |
| `--dsl-only` | off | Skip LLM, use only OpenCV |
| `--turbo` | off | Fast mode with optimizations |

## Ports

| Port | Service |
|------|---------|
| 8765 | WebSocket server |
| 8766 | HTTP viewer |

## Browser Viewer Features

The browser viewer at `http://localhost:8766` provides:

- **Live canvas** - Real-time motion visualization
- **Blob tracking** - Colored rectangles for detected objects
- **Motion stats** - Current motion percentage
- **Event log** - ENTER/EXIT/MOVE events
- **Object paths** - Movement trajectories

## Separate Process Architecture

When `--realtime` is enabled, DSL streaming runs in a **separate process**:

```python
# Main process only handles LLM (throttled)
# DSL process handles streaming (fast)

DSL Process:
  /dev/shm/streamware_dsl/  # Separate frame directory
  FastCapture → DSL Analysis → WebSocket
  
Main Process:
  /dev/shm/streamware/      # Main frame directory  
  FastCapture → LLM Analysis (async)
```

### Benefits

1. **Complete isolation** - GIL doesn't affect DSL streaming
2. **Smooth playback** - Browser updates at target FPS
3. **LLM doesn't block** - Analysis runs in background

## Performance

| Mode | DSL FPS | LLM Rate | Browser |
|------|---------|----------|---------|
| `--dsl-only` | 20+ | None | Smooth |
| `--realtime` | 5-10 | ~0.5/s | Smooth |
| No realtime | N/A | ~0.3/s | N/A |

## Troubleshooting

### Port already in use

```bash
# Kill existing processes
fuser -k 8765/tcp 8766/tcp
```

### Browser not updating

1. Check WebSocket connection status in browser
2. Verify DSL process is running: look for `📊 DSL F20:` logs
3. Try lower FPS: `--fps 5`

### High CPU usage

- Reduce FPS: `--fps 2`
- Use DSL-only mode: `--dsl-only`

---

**Related:**
- [Performance Optimization](PERFORMANCE.md)
- [Motion Analysis](MOTION_ANALYSIS.md)
- [Back to Documentation](README.md)
