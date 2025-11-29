# Media Processing Examples

Image, video, audio, and **real-time stream** analysis with AI (LLaVA, Whisper).

## 📁 Examples

| File | Description |
|------|-------------|
| [image_analysis.py](image_analysis.py) | Describe images with LLaVA |
| [video_captioning.py](video_captioning.py) | Video file analysis (3 modes) |
| [video_modes_demo.py](video_modes_demo.py) | Compare full/stream/diff modes |
| [stream_analysis.py](stream_analysis.py) | **Real-time stream analysis** |
| [screen_monitor.py](screen_monitor.py) | **Screen capture + AI analysis** |
| [audio_transcription.py](audio_transcription.py) | Transcribe audio files |

---

## 📡 Real-time Stream Analysis (NEW!)

Analyze live video streams from multiple sources in real-time:

| Source | Description | Example |
|--------|-------------|---------|
| `rtsp` | Security/IP cameras | `sq stream rtsp --url rtsp://camera/live` |
| `hls` | Live TV, broadcasts | `sq stream hls --url https://stream.m3u8` |
| `youtube` | YouTube live/videos | `sq stream youtube --url "https://..."` |
| `twitch` | Twitch streams | `sq stream twitch --url "https://twitch.tv/..."` |
| `screen` | Desktop capture | `sq stream screen --mode diff` |
| `webcam` | Local camera | `sq stream webcam --device 0` |

### Quick Start - Streams

```bash
# 🎥 Security camera (RTSP)
sq stream rtsp --url rtsp://192.168.1.100/live --mode diff --interval 5

# 📺 YouTube live
sq stream youtube --url "https://youtube.com/watch?v=xxx" --mode stream

# 🖥️ Screen monitoring (detect activity)
sq stream screen --mode diff --interval 2

# 🖥️ Continuous screen watch (Ctrl+C to stop)
sq stream screen --mode diff --continuous

# 📹 Webcam analysis
sq stream webcam --device 0 --mode stream --duration 30

# 🎮 Twitch stream
sq stream twitch --url "https://twitch.tv/channel" --mode stream
```

### Stream Analysis Modes

Same modes as video files:

| Mode | Description | Use Case |
|------|-------------|----------|
| `diff` | Track changes between frames | Security, activity monitoring |
| `stream` | Detailed frame-by-frame | Documentation, debugging |
| `full` | Periodic summaries | Overview, logging |

### Python API - Streams

```python
from streamware import flow
from streamware.components.stream import analyze_screen, watch_screen

# One-time screen analysis
result = flow("stream://screen?mode=diff&duration=30").run()
print(result["timeline"])

# Continuous monitoring (generator)
for event in watch_screen(mode="diff", interval=2):
    if event.get("type") == "change":
        print(f"🔵 Change detected: {event['changes']}")

# YouTube analysis
result = flow("stream://youtube?url=https://youtube.com/watch?v=xxx&mode=stream").run()
for frame in result["frames"]:
    print(f"[{frame['timestamp']}] {frame['description']}")

# RTSP camera
result = flow("stream://rtsp?url=rtsp://camera/live&mode=diff&interval=5").run()
```

---

## 🎬 Video Analysis Modes

Streamware offers **3 different modes** for video analysis:

| Mode | Use Case | Output |
|------|----------|--------|
| `full` | Overall summary, coherent narrative | Single `description` |
| `stream` | Frame-by-frame detailed analysis | `frames[]` list |
| `diff` | Track changes between frames | `timeline[]` + `summary` |

### Mode: `full` (default)

Creates a **coherent narrative** tracking subjects through the entire video.

```bash
sq media describe_video --file presentation.mp4 --mode full
```

**Output:**
```json
{
  "mode": "full",
  "description": "The video shows a presenter explaining a software demo. They begin at a whiteboard, then move to a laptop to demonstrate the interface. Key features are highlighted with screen recordings.",
  "num_frames": 8,
  "scenes": 8,
  "duration": "2:34"
}
```

**Best for:**
- Video summaries
- Content description for accessibility
- SEO metadata generation

### Mode: `stream`

**Detailed frame-by-frame** analysis with subjects, objects, actions.

```bash
sq media describe_video --file tutorial.mp4 --mode stream
```

**Output:**
```json
{
  "mode": "stream",
  "frames": [
    {
      "frame": 1,
      "timestamp": "0:00",
      "description": "SUBJECTS: A person in blue shirt, facing camera. SETTING: Office with whiteboard. OBJECTS: Laptop, coffee mug, notebook. ACTION: Speaking to camera. TEXT: 'Welcome' on screen."
    },
    {
      "frame": 2,
      "timestamp": "0:15",
      "description": "SUBJECTS: Same person, now pointing at screen. SETTING: Same office. OBJECTS: Code editor visible. ACTION: Explaining code. TEXT: 'def main():' visible."
    }
  ],
  "num_frames": 12
}
```

**Best for:**
- Detailed video documentation
- Training data generation
- Scene-by-scene breakdown

### Mode: `diff`

Tracks **changes between frames** - what appeared, moved, or disappeared.

```bash
sq media describe_video --file timelapse.mp4 --mode diff
```

**Output:**
```json
{
  "mode": "diff",
  "timeline": [
    {"frame": 1, "timestamp": "0:00", "type": "start", "description": "Empty room with desk and chair."},
    {"frame": 2, "timestamp": "0:10", "type": "change", "changes": "NEW: Person entered from left. MOVED: Chair pushed back."},
    {"frame": 3, "timestamp": "0:20", "type": "change", "changes": "NEW: Laptop opened on desk. ACTION: Person typing."},
    {"frame": 4, "timestamp": "0:30", "type": "no_change", "changes": "No significant changes."}
  ],
  "summary": "Person enters room, sits at desk, and begins working on laptop.",
  "significant_changes": 2
}
```

**Best for:**
- Motion detection analysis
- Activity tracking
- Surveillance video analysis
- Timelapse documentation

---

## 🚀 Quick Start Commands

### Image Analysis

```bash
# Basic description
sq media describe_image --file photo.jpg

# Custom prompt
sq media describe_image --file diagram.png --prompt "Explain this diagram step by step"

# Different model
sq media describe_image --file art.jpg --model llava:13b
```

### Video Analysis

```bash
# Quick summary (default: full mode)
sq media describe_video --file video.mp4

# Detailed frame-by-frame
sq media describe_video --file video.mp4 --mode stream

# Track changes
sq media describe_video --file video.mp4 --mode diff

# Custom prompt for specific focus
sq media describe_video --file meeting.mp4 --mode full --prompt "Focus on the speaker and their gestures"
```

### Audio Transcription

```bash
# Basic transcription
sq media transcribe --file audio.mp3

# Save to file
sq media transcribe --file meeting.wav --output transcript.txt
```

### Text-to-Speech

```bash
# Generate speech
sq media speak --text "Hello, welcome to Streamware" --output welcome.wav
```

---

## 💻 Python API Examples

### Image Analysis

```python
from streamware import flow

# Basic
result = flow("media://describe_image?file=photo.jpg").run()
print(result["description"])

# With custom prompt
result = flow("media://describe_image?file=chart.png&prompt=Analyze this chart data").run()
```

### Video Analysis with Modes

```python
from streamware import flow

# Full narrative mode
result = flow("media://describe_video?file=video.mp4&mode=full").run()
print(result["description"])

# Stream mode - iterate frames
result = flow("media://describe_video?file=video.mp4&mode=stream").run()
for frame in result["frames"]:
    print(f"[{frame['timestamp']}] {frame['description']}")

# Diff mode - track changes
result = flow("media://describe_video?file=video.mp4&mode=diff").run()
print(f"Summary: {result['summary']}")
print(f"Significant changes: {result['significant_changes']}")
for change in result["timeline"]:
    if change["type"] == "change":
        print(f"[{change['timestamp']}] {change['changes']}")
```

### Pipeline Example

```python
from streamware import flow

# Video to text summary to Slack notification
result = (
    flow("media://describe_video?file=security_cam.mp4&mode=diff")
    .pipe("transform://jsonpath?query=$.summary")
    .pipe("slack://send?channel=security-alerts")
).run()
```

---

## 🔧 Requirements

### System Dependencies

```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows
choco install ffmpeg
```

### AI Models

```bash
# LLaVA for image/video (required)
ollama pull llava

# Optional: larger model for better results
ollama pull llava:13b

# Qwen for narrative generation
ollama pull qwen2.5:14b
```

### Python Packages

```bash
pip install streamware[media]

# Or manually
pip install SpeechRecognition pydub
```

---

## 📚 Related Documentation

| Document | Description |
|----------|-------------|
| [Media Guide](../../docs/v2/guides/MEDIA_GUIDE.md) | Full media processing guide |
| [LLM Component](../../docs/v2/components/LLM_COMPONENT.md) | AI provider configuration |
| [Quick CLI Reference](../../docs/v2/components/QUICK_CLI.md) | All `sq` commands |
| [DSL Examples](../../docs/v2/components/DSL_EXAMPLES.md) | Pipeline syntax |

## 🔗 Related Examples

| Example | Description |
|---------|-------------|
| [LLM AI](../llm-ai/) | Text generation, SQL conversion |
| [Voice Control](../voice-control/) | Voice commands, STT/TTS |
| [Data Pipelines](../data-pipelines/) | ETL with media data |
| [Automation](../automation/) | Screenshot analysis |

## 🔗 Source Code

| Component | Path |
|-----------|------|
| MediaComponent | [streamware/components/media.py](../../streamware/components/media.py) |
| VideoComponent | [streamware/components/video.py](../../streamware/components/video.py) |
| VoiceComponent | [streamware/components/voice.py](../../streamware/components/voice.py) |

---

## 📋 Use Case Examples

### 1. Security Camera Analysis

```bash
# Detect activity in surveillance footage
sq media describe_video --file cam_footage.mp4 --mode diff --prompt "Focus on people and movement"
```

### 2. Meeting Transcription

```bash
# Transcribe and summarize meeting
sq media transcribe --file meeting.mp3 | sq llm "Summarize this meeting transcript"
```

### 3. Content Moderation

```bash
# Check video for inappropriate content
sq media describe_video --file upload.mp4 --mode stream --prompt "Flag any inappropriate content"
```

### 4. Accessibility Descriptions

```bash
# Generate alt-text for images
sq media describe_image --file product.jpg --prompt "Write a concise alt-text for accessibility"
```

### 5. Video Documentation

```bash
# Document a tutorial video
sq media describe_video --file tutorial.mp4 --mode stream > tutorial_docs.json
```
