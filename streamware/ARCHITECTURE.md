# Streamware Architecture

## Modular Structure

```
streamware/
├── cli/                      # Command Line Interface
│   ├── __init__.py          # Exports
│   ├── parser.py            # Argument definitions
│   ├── handlers.py          # Command handlers (watch, live, detect, config, test)
│   └── main.py              # Entry point
│
├── narrator/                 # Video Narration Pipeline
│   ├── __init__.py          # Orchestrator & API
│   ├── frame_analyzer.py    # Motion detection, edge tracking
│   └── models.py            # Data classes (NarrationEntry, DetectionResult, etc.)
│
├── detector/                 # Smart Detection Pipeline
│   ├── __init__.py          # Exports
│   ├── models.py            # DetectionResult, DetectionLevel, MotionLevel
│   ├── yolo.py              # YOLO detector wrapper
│   ├── motion.py            # Motion detection (OpenCV)
│   └── pipeline.py          # SmartDetector orchestrator
│
├── filters/                  # Response Filtering
│   ├── __init__.py          # Exports
│   ├── significance.py      # Significance checks (is_significant, should_notify)
│   ├── tts.py               # TTS formatting (format_for_tts, clean_for_speech)
│   ├── detection.py         # Detection helpers (quick_person_check, summarize_detection)
│   └── llm_analysis.py      # LLM validation (validate_with_llm, summarize_session)
│
├── llm_intent.py            # LLM-based natural language parsing
├── notifier.py              # Email/Slack/Telegram/Webhook notifications
├── intent.py                # Regex-based intent parsing (fallback)
├── config.py                # Configuration management
└── core.py                  # Flow/Pipeline core
```

## Key Components

### 1. LLM Intent Parser (`llm_intent.py`)

Parses natural language commands using local Ollama or OpenAI:

```python
from streamware.llm_intent import parse_command

intent = parse_command("detect person and email tom@example.com immediately")
print(intent.to_cli_string())
# sq watch --detect person --email tom@example.com --notify-mode instant
```

### 2. CLI Module (`cli/`)

Modular command-line interface:

```python
from streamware.cli import run_cli, create_parser

# Run with arguments
run_cli(["watch", "detect person", "--duration", "30"])

# Or use parser directly
parser = create_parser()
args = parser.parse_args()
```

### 3. Narrator Module (`narrator/`)

Video analysis pipeline:

```python
from streamware.narrator import NarratorOrchestrator, NarratorConfig

config = NarratorConfig.from_intent("track person")
narrator = NarratorOrchestrator(config)
results = narrator.run(url="rtsp://...", duration=30)
```

### 4. Filters Module (`filters/`)

Response filtering and TTS formatting:

```python
from streamware.filters import is_significant, format_for_tts, should_notify

if is_significant(response):
    tts_text = format_for_tts(response)
    if should_notify(response):
        send_notification(response)
```

### 5. Notifier (`notifier.py`)

Multi-channel notifications:

```python
from streamware.notifier import Notifier, notify

# Quick notification
notify("Person detected at entrance")

# Or use Notifier class
notifier = Notifier(email="tom@example.com", mode="instant")
notifier.add_event("Person detected", screenshot_path="/tmp/frame.jpg")
notifier.flush()
```

## Data Flow

```
Natural Language Command
        ↓
┌───────────────────┐
│   LLM Intent      │  Parse "detect person and email..."
│   (llm_intent.py) │  → LLMIntent object
└─────────┬─────────┘
          ↓
┌───────────────────┐
│   CLI Handler     │  Route to watch/live/detect handler
│   (cli/handlers)  │
└─────────┬─────────┘
          ↓
┌───────────────────┐
│   Narrator        │  Process video frames
│   (narrator/)     │
└─────────┬─────────┘
          ↓
┌───────────────────┐
│   Smart Detector  │  YOLO + LLM detection
│   (smart_detector)│
└─────────┬─────────┘
          ↓
┌───────────────────┐
│   Filters         │  Check significance
│   (filters/)      │
└─────────┬─────────┘
          ↓
┌───────────────────┐
│   Notifier        │  Send email/slack/telegram
│   (notifier.py)   │
└───────────────────┘
```

## Backward Compatibility

Old imports still work:

```python
# Old way (still works)
from streamware.response_filter import is_significant, format_for_tts

# New way (recommended)
from streamware.filters import is_significant, format_for_tts
```

## Configuration

Environment variables in `.env`:

```bash
# Detection
SQ_DEFAULT_URL=rtsp://...
SQ_MODE=hybrid
SQ_TARGET=person

# Email
SQ_SMTP_HOST=smtp.gmail.com
SQ_SMTP_PORT=587
SQ_SMTP_USER=your@gmail.com
SQ_SMTP_PASS=app-password

# Notifications
SQ_NOTIFY_EMAIL=recipient@example.com
SQ_NOTIFY_MODE=digest
SQ_NOTIFY_INTERVAL=60

# LLM
SQ_OLLAMA_URL=http://localhost:11434
SQ_ANALYSIS_MODEL=qwen2.5:3b
```
