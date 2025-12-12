# Security Monitoring Example

Intrusion detection with LLM verification.

## Quick Start

```bash
# Natural language
sq watch "alert when someone enters"

# With triggers
sq watch --url rtsp://camera/stream --detect person --alert speak

# Polish
sq watch "powiadom gdy ktoś wchodzi"
```

## Features

- **YOLO + LLM verification**: Double-check detections
- **Intrusion alerts**: Voice and log alerts
- **High sensitivity**: Catches subtle movements

## Configuration

```env
# .env settings for security mode
SQ_STREAM_FPS=1.0
SQ_YOLO_SKIP_LLM_THRESHOLD=0.7  # Verify uncertain detections
SQ_USE_GUARDER=true
SQ_MODEL=llava:7b
```

## Alert Types

| Alert | Command |
|-------|---------|
| Voice | `--alert speak` |
| Log | `--alert log` |
| Slack | `--alert slack` |
| Telegram | `--alert telegram` |

## Python API

```python
from streamware.workflow import load_workflow

# Load security preset
workflow = load_workflow(preset="security")
print(f"LLM: {workflow.llm}")
print(f"Guarder: {workflow.guarder}")

# Apply and run
from streamware.core import flow
result = flow(f"live://narrator?source={url}&mode=track&focus=person").run()
```

## Triggers

```bash
# Multiple triggers
sq live narrator --url rtsp://... --trigger "person appears,vehicle approaching"
```
