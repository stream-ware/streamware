# Describe Scene Example

Detailed scene descriptions using LLM (llava).

## Quick Start

```bash
# Describe what's happening
sq watch "describe what's happening"
sq watch "opisz co się dzieje"

# Detailed analysis
sq watch "slow detailed analysis"
sq watch "szczegółowo opisz scenę"
```

## Features

- **LLM-powered**: Uses llava:7b for rich descriptions
- **Full scene analysis**: Objects, activities, atmosphere
- **Guarder filtering**: Clean, relevant responses

## Configuration

```env
# .env settings for describe mode
SQ_STREAM_FPS=0.2          # 1 frame every 5 seconds
SQ_YOLO_SKIP_LLM_THRESHOLD=1.0  # Always use LLM
SQ_USE_GUARDER=true
SQ_MODEL=llava:7b
```

## Output Examples

```
"A person is sitting at a desk working on a laptop. 
The room appears to be an office with natural lighting 
coming from a window on the left."

"Two people are having a conversation near the entrance. 
One is holding a coffee cup. The area looks like a 
building lobby with modern furniture."
```

## Python API

```python
from streamware.intent import parse_intent, apply_intent
from streamware.core import flow

# Parse intent
intent = parse_intent("describe scene")
print(f"LLM: {intent.llm}")        # True
print(f"Model: {intent.llm_model}") # llava:7b

# Build URI
uri = f"live://narrator?source={url}"
uri += "&mode=full"
uri += "&tts=true"
uri += "&duration=60"

result = flow(uri).run()
```

## LLM Models

| Model | Speed | Quality |
|-------|-------|---------|
| moondream | Fast | Basic |
| llava:7b | Medium | Good |
| llava:13b | Slow | Best |
