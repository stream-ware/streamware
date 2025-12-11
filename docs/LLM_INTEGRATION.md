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

```text
Priority: moondream → llava:7b → llava:13b
```

## Async LLM

### How It Works

```text
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

# Analysis model for response processing
export SQ_ANALYSIS_MODEL=qwen2.5:3b
```

## Timeout Configuration (NEW!)

All LLM operations now have configurable timeouts:

```ini
# Response Filter Timeouts
SQ_GUARDER_TIMEOUT=5                  # Timeout for guarder model availability check
SQ_QUICK_PERSON_TIMEOUT=10            # Timeout for quick person detection
SQ_QUICK_CHANGE_TIMEOUT=8             # Timeout for quick change detection
SQ_SUMMARIZE_TIMEOUT=15               # Timeout for detection summarization
SQ_VALIDATE_TIMEOUT=10                # Timeout for LLM validation
SQ_ANALYZE_TIMEOUT=8                  # Timeout for LLM analysis
SQ_ANALYZE_TRACKING_TIMEOUT=10        # Timeout for LLM analysis with tracking
```

**Impact:**

- Prevents hanging operations
- Allows tuning for different hardware capabilities
- Improves system reliability

## Prompts

### Track Mode (Default)

```text
Look at this image carefully. Is there a person clearly visible?
If yes, describe: position, action, direction of movement.
If no person, say "No person visible" and briefly describe the scene.
```

### Diff Mode

```text
Compare this frame to the previous. What changed?
Focus on: movement, new objects, disappeared objects.
```

## Vision Model Confidence Thresholds (NEW!)

All vision model confidence thresholds are now configurable:

```ini
# Vision Model Confidence Thresholds
SQ_VISION_ASSUME_PRESENT=0.5          # Default confidence when vision can't load
SQ_VISION_CONFIDENT_PRESENT=0.9       # Confidence for confident YES response
SQ_VISION_CONFIDENT_ABSENT=0.9        # Confidence for confident NO response
```

**How thresholds work:**

- **ASSUME_PRESENT**: Used when vision model fails to load/process
- **CONFIDENT_PRESENT**: Applied when vision model gives confident YES response
- **CONFIDENT_ABSENT**: Applied when vision model gives confident NO response

**Tuning tips:**

- Lower `CONFIDENT_PRESENT` for more sensitive detection
- Higher `CONFIDENT_ABSENT` to reduce false positives
- Adjust `ASSUME_PRESENT` based on your error tolerance

## Response Filtering

StreamWare filters LLM responses for quality:

1. **Duplicate filter** - Skip identical responses
2. **Significance filter** - Only report meaningful changes
3. **Guarder filter** - Validate with secondary model

**Guarder Filter Improvements (NEW!):**
- Configurable timeouts prevent hanging
- Improved track mode logic reduces false negatives
- Better error handling with fallback responses

## Custom Prompts (NEW!)

All LLM prompts are now fully configurable through environment variables:

```ini
# Custom prompt templates (override defaults)
SQ_PROMPT_STREAM_DIFF=                # Custom stream diff prompt
SQ_PROMPT_STREAM_FOCUS=               # Custom stream focus prompt
SQ_PROMPT_TRIGGER_CHECK=              # Custom trigger check prompt
SQ_PROMPT_MOTION_REGION=              # Custom motion region prompt
SQ_PROMPT_TRACKING_DETECT=            # Custom tracking detection prompt
SQ_PROMPT_LIVE_NARRATOR_TRACK=        # Custom live narrator track prompt
```

**Example custom prompt:**

```ini
SQ_PROMPT_LIVE_NARRATOR_TRACK=Analyze this image for human presence. Focus on detailed description of position, activity, and movement direction. Be very specific about location within frame.
```

**Prompt variables:**

- `{focus}` - Target object (person, vehicle, etc.)
- `{mode}` - Detection mode (track, diff, etc.)
- `{tracking_data}` - DSL tracking information

## Performance Tips

### Reduce LLM Latency

1. Use smaller model: `--model moondream`
2. Use `--turbo` mode
3. Lower image resolution
4. Enable async: `--realtime`

### Optimize Timeouts

```ini
# Faster timeouts for quick response
SQ_ANALYZE_TIMEOUT=5
SQ_GUARDER_TIMEOUT=3

# Longer timeouts for slow hardware
SQ_ANALYZE_TIMEOUT=15
SQ_SUMMARIZE_TIMEOUT=30
```

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
