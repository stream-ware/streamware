# Streamware Quick Start Guide

One-liner examples for the most common tasks.

## 🚀 Installation

```bash
pip install streamware

# Install fast models (recommended)
ollama pull llama3.2    # For LLM shell
ollama pull moondream   # Fast vision model

# Or use install script:
./install_fast_model.sh
```

## 🤖 Interactive LLM Shell (NEW - Recommended!)

```bash
# Start interactive shell
sq shell

# With auto-execute
sq shell --auto

# List available functions
sq functions
```

**Example session:**
```
sq> detect person and email me@company.com immediately
✅ Start person detection, send email immediately
   Command: sq watch --detect person --email me@company.com --notify-mode instant
   Execute? [Y/n]: y

sq> track cars for 5 minutes
✅ Track car objects for 300 seconds
   Command: sq watch --track car --fps 2 --duration 300

sq> stop
sq> exit
```

## 🎯 Live Narrator (NEW - Recommended)

**Real-time video analysis with YOLO + Vision LLM + TTS**

```bash
# Person tracking with voice narration
sq live narrator --url "rtsp://camera/stream" --mode track --focus person --tts

# Bird feeder monitoring
sq live narrator --url "rtsp://birdcam/stream" --mode track --focus bird --tts

# Pet camera (cats & dogs)
sq live narrator --url "rtsp://petcam/stream" --mode track --focus pet --tts

# Vehicle tracking
sq live narrator --url "rtsp://parking/stream" --mode track --focus vehicle --tts

# Verbose mode (see timing)
sq live narrator --url "rtsp://camera/stream" --mode track --focus person --tts --verbose
```

### Performance
| Component | Time |
|-----------|------|
| YOLO detection | ~10ms |
| Vision LLM (moondream) | ~1.5s |
| Guarder (gemma:2b) | ~250ms |
| **Total cycle** | **~2s** |

## 📷 Network & Cameras

### Find Cameras
```bash
# CLI
sq network find "cameras" --yaml

# Python
from streamware.helpers import find_cameras
cameras = find_cameras()
for cam in cameras:
    print(f"{cam['ip']}: {cam.get('connection', {}).get('rtsp', ['N/A'])[0]}")
```

### Scan Network
```bash
# CLI
sq network scan --yaml

# Python
from streamware.helpers import scan_network
result = scan_network()
print(f"Found {result['total_devices']} devices")
```

## 🎥 Stream Analysis

### Watch Camera for Activity
```bash
# CLI - detect people with low sensitivity (fewer false alarms)
sq stream rtsp --url "rtsp://admin:pass@192.168.1.100:554/stream" \
    --focus person --sensitivity low --duration 60

# Python
from streamware.helpers import watch_camera
result = watch_camera("rtsp://admin:pass@camera/live", focus="person", duration=60)
if result['significant_changes'] > 0:
    print("Activity detected!")
```

### Generate HTML Report with Images
```bash
sq stream rtsp --url "rtsp://camera/live" \
    --focus person --duration 60 \
    --file security_report.html
```

### Quick Security Check
```python
from streamware.helpers import security_check, send_alert

result = security_check("rtsp://camera/live", duration=30)
if result['activity']:
    send_alert("Motion detected!", slack=True)
```

## 👥 People Tracking

### Count People
```bash
# CLI
sq tracking count --url "rtsp://camera/live" --objects person --duration 300

# Python
from streamware.helpers import count_people
result = count_people("rtsp://camera/live", duration=300)
stats = result['statistics']['person']
print(f"Average: {stats['avg']:.1f}, Max: {stats['max']}")
```

### Track Person Movement
```python
from streamware.helpers import track_person
result = track_person("rtsp://camera/live", name="Visitor", duration=120)
print(f"Trajectory: {len(result['trajectory'])} points")
```

### Monitor Zone Entry/Exit
```python
from streamware.helpers import monitor_zone
result = monitor_zone("rtsp://camera/live", "entrance", 0, 0, 200, 300, duration=600)
for event in result['events']:
    print(f"{event['type']}: {event['object_type']} at {event['timestamp']}")
```

## 🔍 Motion Detection (Smart)

### Sensitive Detection (recommended)
```bash
# Low threshold (5-10) for better sensitivity
sq motion --url "rtsp://camera/live" \
    --threshold 5 \
    --min-region 50 \
    --duration 30 \
    --file motion_report.html

# Two-stage detection: pixel diff first, then AI on changed regions
sq smart watch --url "rtsp://camera/live" --min-interval 2 --duration 60 --no-ai
```

### Key Parameters
| Parameter | Default | Recommended | Description |
|-----------|---------|-------------|-------------|
| `--threshold` | 25 | **5-10** | Pixel diff threshold (lower = more sensitive) |
| `--min-region` | 100 | **50** | Minimum changed region size in pixels |
| `--interval` | 5 | **3-5** | Seconds between checks |

## 🎙️ Live Narrator (TTS)

### Three Modes
| Mode | Description | Best For |
|------|-------------|----------|
| `full` | Describe entire scene | General monitoring |
| `diff` | Only describe changes | Surveillance |
| `track` | Track specific object | Person tracking |

### Describe What's Happening
```bash
# Single description
sq live describe --url "rtsp://camera/live"

# FULL mode - describe everything
sq live narrator --url "rtsp://camera/live" --mode full --tts

# DIFF mode - describe only changes (recommended)
sq live narrator --url "rtsp://camera/live" --mode diff --tts --duration 60

# TRACK mode - track person movement
sq live narrator --url "rtsp://camera/live" \
    --mode track --focus person --tts --duration 120

# Watch for specific triggers
sq live watch --url "rtsp://camera/live" \
    --trigger "person appears,door opens" \
    --tts --duration 300 \
    --frames-dir ./frames   # save captured frames locally
```

> ℹ️ Frames captured by the live narrator can be persisted to a folder with `--frames-dir`.

### Python API
```python
from streamware.components import describe_now, watch_for

# Get description of current frame
description = describe_now("rtsp://camera/live", tts=True)
print(description)

# Watch for triggers
result = watch_for(
    "rtsp://camera/live",
    conditions=["person appears", "package delivered"],
    duration=600,
    tts=True
)
for alert in result.get("alerts", []):
    print(f"Alert: {alert['description']}")
```

## 🎯 Qualitative Watch (Simple)

### Intuitive Parameters
```bash
# Instead of --threshold 10 --min-region 50, use:
sq watch --url "rtsp://camera/live" \
    --detect person \
    --sensitivity high \
    --speed fast \
    --alert speak

# More examples:
sq watch --url "$URL" --detect vehicle --sensitivity medium
sq watch --url "$URL" --detect motion --sensitivity ultra --speed realtime
sq watch --url "$URL" --detect package --alert slack
```

### Sensitivity Levels
| Level | Threshold | Use Case |
|-------|-----------|----------|
| `ultra` | 3 | Detect tiny changes (noisy) |
| `high` | 8 | Security monitoring |
| `medium` | 15 | General use (default) |
| `low` | 25 | Stable scenes |
| `minimal` | 40 | Major changes only |

## 🔔 Alerts

### Send Alert
```python
from streamware.helpers import send_alert

# Slack (requires SQ_SLACK_WEBHOOK in .env)
send_alert("Motion detected!", slack=True)

# Telegram (requires SQ_TELEGRAM_BOT_TOKEN and SQ_TELEGRAM_CHAT_ID)
send_alert("Motion detected!", telegram=True)

# Custom webhook
send_alert("Motion detected!", webhook="https://your-webhook.com/alert")
```

## 📊 Full Monitoring Pipeline

```python
from streamware.helpers import (
    find_cameras, security_check, send_alert, 
    generate_report, log_event
)

# 1. Find all cameras
cameras = find_cameras()
print(f"Found {len(cameras)} cameras")

# 2. Check each camera
for cam in cameras:
    ip = cam['ip']
    url = cam.get('connection', {}).get('rtsp', [])[0]
    
    if not url:
        continue
    
    print(f"Checking {ip}...")
    result = security_check(url, duration=30)
    
    if result['activity']:
        print(f"🔴 Activity on {ip}!")
        
        # Log event
        log_event("motion_detected", {"camera": ip, "changes": result['changes']})
        
        # Send alert
        send_alert(f"Motion on camera {ip}: {result['changes']} changes", slack=True)
        
        # Generate report
        generate_report(result, f"alert_{ip}.html")
```

## ⚙️ Configuration

### Setup .env
```bash
# Create .env file
sq config --init

# Or use web panel
sq config --web
```

### Key Settings (.env)
```bash
# AI Model (llava:13b recommended)
SQ_MODEL=llava:13b

# Voice / STT–TTS configuration
SQ_STT_PROVIDER=whisper_local        # google, whisper_local, whisper_api
SQ_WHISPER_MODEL=small              # tiny, base, small, medium, large
SQ_TTS_ENGINE=pyttsx3               # auto, pyttsx3, espeak, say, powershell
SQ_TTS_VOICE=polski                 # preferred voice name (substring)
SQ_TTS_RATE=160                     # speech rate (words per minute)

# Default focus for detection
SQ_STREAM_FOCUS=person

# Detection sensitivity (low = fewer false alarms)
SQ_STREAM_SENSITIVITY=low

# Slack webhook for alerts
SQ_SLACK_WEBHOOK=https://hooks.slack.com/services/xxx

# Telegram for alerts
SQ_TELEGRAM_BOT_TOKEN=xxx
SQ_TELEGRAM_CHAT_ID=xxx
```

### Diagnostics

Run built-in checks to verify your setup:

```bash
# Check camera connectivity + Ollama vision
streamware --check camera "rtsp://admin:pass@192.168.1.100:554/stream"

# Check TTS engine (will offer to install if missing)
streamware --check tts

# Check Ollama only
streamware --check ollama

# All checks
streamware --check all "rtsp://camera/live"
```

### Smart Filtering (Guarder Model)

Streamware uses a small LLM to filter noise from logs:

```bash
# Install guarder model (recommended)
ollama pull qwen2.5:3b

# Or smaller/faster
ollama pull gemma2:2b
```

When you run `sq live narrator`, it will:
1. Check if guarder model is available
2. Offer to install if missing
3. Use LLM filtering by default (regex as fallback)

```bash
# Full monitoring with smart filtering
sq live narrator --url "rtsp://..." --mode track --focus person --tts

# Lite mode (less RAM, no images stored)
sq live narrator --url "rtsp://..." --lite --quiet
```

**Configuration (`.env`):**
```ini
SQ_GUARDER_MODEL=qwen2.5:3b   # Small LLM for validation
SQ_USE_GUARDER=true           # Enabled by default
```

### Troubleshooting RTSP / ffmpeg

If you see messages like:

```text
Frame capture failed: Command '['ffmpeg', ..., '-i', 'rtsp://camera/live', ...]' returned non-zero exit status 145
```

Najczęstsze przyczyny:
- Błędny URL RTSP lub kamera jest offline
- Nieprawidłowe dane logowania (`user:pass@` w URL)
- Firewall / sieć blokuje połączenie
- Brak lub niekompatybilna wersja `ffmpeg`

Spróbuj:
- Otworzyć ten sam URL w `ffplay` / `ffmpeg` lub VLC
- Zweryfikować, że `ffmpeg` jest zainstalowany i w `$PATH`
- Sprawdzić, czy kamera działa lokalnie w tej samej sieci

### Change Settings
```bash
sq config --set SQ_MODEL llava:13b --save
sq config --set SQ_STREAM_FOCUS person --save
sq config --show
```

## 📁 Output Formats

```bash
# YAML (default)
sq network scan --yaml

# JSON
sq network scan --json

# ASCII Table
sq network scan --table

# HTML Report with images
sq stream rtsp --url "..." --file report.html
```

## 🔗 CLI Reference

```bash
# Network
sq network scan                     # Scan network
sq network find "cameras"           # Find cameras
sq network find "printers"          # Find printers
sq network identify --ip 192.168.1.1  # Identify device

# Stream Analysis
sq stream rtsp --url URL --mode diff --focus person
sq stream screen --mode diff        # Screen capture
sq stream webcam --mode stream      # Webcam

# Tracking
sq tracking detect --url URL --objects person,vehicle
sq tracking count --url URL --objects person
sq tracking zones --url URL --zones "entrance:0,0,100,200"

# Configuration
sq config --show                    # Show config
sq config --web                     # Web panel
sq config --set KEY VALUE --save    # Set value
```

## 📚 More Examples

- `examples/network/smart_camera_monitor.py` - Auto-discover and monitor
- `examples/network/security_pipeline.py` - Full security system
- `examples/media-processing/object_tracking.py` - Object tracking demos
- `examples/media-processing/stream_analysis.py` - Stream analysis examples
