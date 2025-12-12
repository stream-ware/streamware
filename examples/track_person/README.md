# Track Person Example

Fast person tracking using YOLO without LLM.

## Quick Start

```bash
# Natural language
sq watch "track person"

# With custom URL
sq watch "track person" --url rtsp://camera/stream

# Polish
sq watch "śledź osoby"
```

## Features

- **Fast detection**: ~1 FPS using YOLO only
- **Movement tracking**: Position, direction, entering/exiting
- **TTS announcements**: Voice alerts on changes

## Output Messages

| Event | Message |
|-------|---------|
| Person appears | "Person entering from left" |
| Position | "Person on left detected" |
| Movement | "Person moving right" |
| Exit | "Person left to the right" |

## Configuration

```env
# .env settings for track mode
SQ_STREAM_FPS=1.0
SQ_YOLO_SKIP_LLM_THRESHOLD=0.3
SQ_USE_GUARDER=false
```

## Python API

```python
from streamware.intent import parse_intent, apply_intent
from streamware.core import flow

# Parse natural language
intent = parse_intent("track person")
apply_intent(intent)

# Run
result = flow(f"live://narrator?source={url}&mode=track&focus=person").run()
```
