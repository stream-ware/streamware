# 🏗️ System Architecture

StreamWare system design and data flow.

**[← Back to Documentation](README.md)**

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         STREAMWARE                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐           │
│  │   RTSP       │    │  FastCapture │    │   Frame      │           │
│  │   Camera     │───▶│  (OpenCV)    │───▶│   Queue      │           │
│  └──────────────┘    └──────────────┘    └──────────────┘           │
│                                                 │                   │
│                      ┌──────────────────────────┼──────────────┐    │
│                      │                          │              │    │
│                      ▼                          ▼              │    │
│              ┌──────────────┐          ┌──────────────┐        │    │
│              │ DSL Analysis │          │ LLM Analysis │        │    │
│              │  (OpenCV)    │          │  (Ollama)    │        │    │
│              └──────────────┘          └──────────────┘        │    │
│                      │                          │              │    │
│                      ▼                          ▼              │    │
│              ┌──────────────┐          ┌──────────────┐        │    │
│              │  WebSocket   │          │   Response   │        │    │
│              │   Server     │          │   Filter     │        │    │
│              └──────────────┘          └──────────────┘        │    │
│                      │                          │              │    │
│                      ▼                          ▼              │    │
│              ┌──────────────┐          ┌──────────────┐        │    │
│              │   Browser    │          │  TTS/Webhook │        │    │
│              │   Viewer     │          │   Output     │        │    │
│              └──────────────┘          └──────────────┘        │    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Multiprocessing Architecture

When `--realtime` is enabled:

```
┌─────────────────────────────────┐    ┌─────────────────────────────────┐
│     MAIN PROCESS (PID: parent)  │    │   DSL STREAMER (PID: child)     │
├─────────────────────────────────┤    ├─────────────────────────────────┤
│                                 │    │                                 │
│  /dev/shm/streamware/           │    │  /dev/shm/streamware_dsl/       │
│                                 │    │                                 │
│  FastCapture (0.5 FPS)          │    │  FastCapture (5-20 FPS)         │
│      │                          │    │      │                          │
│      ▼                          │    │      ▼                          │
│  LLM Analysis                   │    │  DSL Analysis (~10ms)           │
│      │                          │    │      │                          │
│      ▼                          │    │      ▼                          │
│  Response Filter                │    │  WebSocket Server               │
│      │                          │    │      │                          │
│      ▼                          │    │      ▼                          │
│  TTS / Webhook                  │    │  Browser :8766                  │
│                                 │    │                                 │
└─────────────────────────────────┘    └─────────────────────────────────┘
           │                                       │
           └───────── Completely Isolated ─────────┘
```

## Component Details

### FastCapture (`fast_capture.py`)

- Persistent RTSP connection
- OpenCV or FFmpeg backend
- Frame queue with buffer
- RAM disk storage

```python
FastCapture(
    rtsp_url="rtsp://...",
    fps=5.0,
    buffer_size=5,
    output_dir="/dev/shm/streamware"
)
```

### FrameDiffAnalyzer (`frame_diff_dsl.py`)

- Background subtraction
- Contour detection
- Blob tracking with IDs
- Velocity calculation

```python
analyzer = FrameDiffAnalyzer(
    motion_threshold=25,
    min_blob_area=500,
    filter_static=True
)
delta = analyzer.analyze(frame_path)
```

### DSL Streamer Process (`dsl_streamer_process.py`)

- Separate Python process
- Independent FastCapture
- WebSocket streaming
- Isolated from GIL

```python
from dsl_streamer_process import start_dsl_streamer
process = start_dsl_streamer(rtsp_url, fps=10)
```

### RealtimeDSLServer (`realtime_dsl_server.py`)

- WebSocket on port 8765
- HTTP viewer on port 8766
- JSON frame streaming
- SO_REUSEADDR for quick restart

### AsyncLLM (`async_llm.py`)

- ThreadPoolExecutor
- Non-blocking inference
- Request queuing
- Timeout handling

## Data Flow

### DSL-Only Mode

```
Camera → FastCapture → DSL Analysis → WebSocket → Browser
                           │
                           └─→ HTML Export
```

### Real-time + LLM Mode

```
                    ┌─→ DSL Process → WebSocket → Browser
Camera → FastCapture┤
                    └─→ Main Process → LLM → Filter → TTS
```

## File Structure

```
streamware/
├── components/
│   └── live_narrator.py      # Main orchestrator
├── fast_capture.py           # RTSP capture
├── frame_diff_dsl.py         # DSL analysis
├── dsl_streamer_process.py   # Separate process
├── realtime_dsl_server.py    # WebSocket server
├── async_llm.py              # Async LLM
├── dsl_timing_logger.py      # Performance logs
├── response_filter.py        # LLM filtering
├── image_optimizer.py        # Image preprocessing
└── tts.py                    # Text-to-speech
```

## Threading Model

| Component | Thread/Process | Notes |
|-----------|----------------|-------|
| FastCapture | Background thread | Continuous capture |
| DSL Analysis | Main thread | Fast (~10ms) |
| DSL Streamer | Separate process | Isolated |
| LLM Inference | ThreadPool | Non-blocking |
| WebSocket | Asyncio | Event loop |
| TTS | Background thread | Non-blocking |

---

**Related:**
- [Real-time Streaming](REALTIME_STREAMING.md)
- [Performance Optimization](PERFORMANCE.md)
- [Back to Documentation](README.md)
