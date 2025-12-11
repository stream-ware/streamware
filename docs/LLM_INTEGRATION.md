# 🤖 LLM Integration

Configure vision models for intelligent video analysis.

**[← Back to Documentation](README.md)**

---

## Overview

StreamWare uses Ollama for vision LLM inference. Supports multiple models with automatic selection and async processing.

## Supported Models

| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| `moondream` | 1.8B | ⚡⚡⚡ | ⭐⭐ | Fast detection |
| `llava:7b` | 7B | ⚡⚡ | ⭐⭐⭐ | Balanced (default) |
| `llava:13b` | 13B | ⚡ | ⭐⭐⭐⭐ | High quality |
| `llava:34b` | 34B | 🐢 | ⭐⭐⭐⭐⭐ | Best quality |

## Configuration

### Select Model

```bash
# Use specific model
sq live narrator --url "rtsp://..." --model llava:7b

# Fast mode auto-selects smaller model
sq live narrator --url "rtsp://..." --fast
```

### Auto Model Selection

In `--fast` or `--turbo` mode, StreamWare automatically selects the fastest available model:

```
Priority: moondream → llava:7b → llava:13b
```

## Async LLM

### How It Works

```
┌─────────────────────────────────────────────────┐
│ Frame 1 → LLM Request (async)                   │
│                ↓                                │
│ Frame 2 → Continue processing (don't wait)     │
│                ↓                                │
│ Frame 3 → LLM Response arrives → Process       │
└─────────────────────────────────────────────────┘
```

### Enable Async Mode

```bash
# Enabled by default in realtime mode
sq live narrator --url "rtsp://..." --realtime

# Disable if needed
sq live narrator --url "rtsp://..." --no-async-llm
```

## Guarder Model

Secondary model for filtering responses:

```bash
# Default: gemma:2b
export SQ_GUARDER_MODEL=gemma:2b

# Use different model
export SQ_GUARDER_MODEL=llama3:8b
```

## Prompts

### Track Mode (Default)

```
Look at this image carefully. Is there a person clearly visible?
If yes, describe: position, action, direction of movement.
If no person, say "No person visible" and briefly describe the scene.
```

### Diff Mode

```
Compare this frame to the previous. What changed?
Focus on: movement, new objects, disappeared objects.
```

## Response Filtering

StreamWare filters LLM responses for quality:

1. **Duplicate filter** - Skip identical responses
2. **Significance filter** - Only report meaningful changes
3. **Guarder filter** - Validate with secondary model

## Performance Tips

### Reduce LLM Latency

1. Use smaller model: `--model moondream`
2. Use `--turbo` mode
3. Lower image resolution
4. Enable async: `--realtime`

### Skip LLM Entirely

```bash
# DSL-only mode - no LLM calls
sq live narrator --url "rtsp://..." --dsl-only
```

## Ollama Setup

### Install Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Pull Models

```bash
ollama pull llava:7b
ollama pull moondream
ollama pull gemma:2b
```

### Check Status

```bash
ollama list
curl http://localhost:11434/api/tags
```

---

**Related:**
- [Performance Optimization](PERFORMANCE.md)
- [Motion Analysis](MOTION_ANALYSIS.md)
- [Back to Documentation](README.md)
