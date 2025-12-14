# 📡 API Reference

CLI options and configuration reference.

**[← Back to Documentation](README.md)**

---

## CLI Commands

### `sq accounting`

Document scanning / OCR / accounting projects.

Due to multiple modes (one-shot scan vs web UI + RTSP), the full up-to-date usage is documented here:

- [🧾 Accounting Scanner](ACCOUNTING.md)

### `sq live narrator`

Main command for live video analysis.

```bash
sq live narrator --url "rtsp://..." [OPTIONS]
```

## Required Options

| Option | Description |
|--------|-------------|
| `--url`, `-u` | RTSP stream URL |

## Mode Options

| Option | Default | Description |
|--------|---------|-------------|
| `--mode` | `track` | Analysis mode: `track`, `diff`, `full` |
| `--focus` | `person` | Focus target: `person`, `vehicle`, `any` |
| `--dsl-only` | off | Skip LLM, use only OpenCV tracking |

## Performance Options

| Option | Default | Description |
|--------|---------|-------------|
| `--turbo` | off | Skip checks + fast model + aggressive caching |
| `--fast` | off | Fast mode: smaller model, lower resolution |
| `--fps N` | 2 | Target frames per second |
| `--duration N` | 60 | Run duration in seconds |
| `--interval N` | 3.0 | Seconds between analyses |

## Real-time Options

| Option | Default | Description |
|--------|---------|-------------|
| `--realtime` | off | Enable browser viewer at :8766 |
| `--verbose`, `-v` | off | Show detailed timing logs |

## Model Options

| Option | Default | Description |
|--------|---------|-------------|
| `--model` | `llava:7b` | Vision model name |
| `--ollama-url` | `http://localhost:11434` | Ollama API URL |

## Output Options

| Option | Default | Description |
|--------|---------|-------------|
| `--tts` | off | Enable text-to-speech |
| `--webhook-url` | none | Webhook URL for events |
| `--quiet` | off | Suppress output |
| `--lite` | off | Lite mode (no images in memory) |

## Advanced Options

| Option | Default | Description |
|--------|---------|-------------|
| `--ramdisk` | on | Use RAM disk for frames |
| `--no-ramdisk` | off | Disable RAM disk |
| `--skip-checks` | off | Skip dependency checks |
| `--benchmark` | off | Run performance benchmark |
| `--auto` | off | Auto-configure based on hardware |

---

## Environment Variables

### Capture

| Variable | Default | Description |
|----------|---------|-------------|
| `SQ_FAST_CAPTURE` | `true` | Enable FastCapture |
| `SQ_RAMDISK_PATH` | `/dev/shm/streamware` | Frame storage path |
| `SQ_CAPTURE_BACKEND` | `auto` | `opencv` or `ffmpeg` |

### LLM

| Variable | Default | Description |
|----------|---------|-------------|
| `SQ_GUARDER_MODEL` | `gemma:2b` | Filter model |
| `SQ_USE_GUARDER` | `false` | Enable guarder filtering |

### Performance

| Variable | Default | Description |
|----------|---------|-------------|
| `SQ_LITE_MODE` | `false` | Memory optimization |

---

## Examples

### Basic Usage

```bash
# Simple tracking
sq live narrator --url "rtsp://camera/stream"

# With turbo mode
sq live narrator --url "rtsp://..." --turbo
```

### Real-time Viewer

```bash
# With LLM
sq live narrator --url "rtsp://..." --realtime --fps 5

# DSL only (fastest)
sq live narrator --url "rtsp://..." --dsl-only --realtime --fps 20
```

### Production

```bash
# Full setup with TTS and webhook
sq live narrator \
  --url "rtsp://..." \
  --mode track \
  --turbo \
  --realtime \
  --tts \
  --webhook-url "http://localhost:8080/events" \
  --duration 3600
```

### Development

```bash
# Verbose with timing
sq live narrator --url "rtsp://..." --verbose --realtime --turbo
```

---

**Related:**
- [Performance Optimization](PERFORMANCE.md)
- [Real-time Streaming](REALTIME_STREAMING.md)
- [Back to Documentation](README.md)
