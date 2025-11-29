# Media Analysis Guide - Streamware 0.2.0

## 🎬 Overview

Streamware includes powerful AI-powered multimedia analysis:
- **Video**: Description with 3 analysis modes (full/stream/diff)
- **Audio**: Transcription (STT) and generation (TTS)
- **Image**: AI-powered descriptions
- **Music**: Analysis and mood detection

## 📂 Related Resources

| Resource | Description |
|----------|-------------|
| [Examples: Media Processing](../../examples/media-processing/) | Working code examples |
| [video_captioning.py](../../examples/media-processing/video_captioning.py) | Video analysis demo |
| [video_modes_demo.py](../../examples/media-processing/video_modes_demo.py) | Compare all modes |
| [Quick CLI Reference](../components/QUICK_CLI.md) | All `sq` commands |
| [Source: media.py](../../streamware/components/media.py) | Implementation |

## 🚀 Quick Start

### Install Models

```bash
# Install LLaVA for vision (video/images)
ollama pull llava

# Install Whisper for audio transcription
pip install openai-whisper

# Install Bark for text-to-speech
pip install bark
```

### Basic Usage

```bash
# Describe video
sq media describe_video --file video.mp4 --model llava

# Describe image
sq media describe_image --file photo.jpg --model llava

# Transcribe audio
sq media transcribe --file audio.mp3

# Text to speech
sq media speak --text "Hello World" --output hello.wav

# Auto-detect and caption
sq media caption --file media_file.mp4
```

## 📹 Video Analysis

Streamware offers **3 different modes** for video analysis. See [examples/media-processing/](../../examples/media-processing/) for working code.

### Video Analysis Modes

| Mode | Description | Best For |
|------|-------------|----------|
| `full` | Coherent narrative (default) | Summaries, SEO, accessibility |
| `stream` | Frame-by-frame details | Documentation, training data |
| `diff` | Track changes between frames | Surveillance, activity tracking |

### Mode: `full` (default)

Creates a coherent narrative tracking subjects through the video.

```bash
sq media describe_video --file video.mp4 --mode full

# Output:
{
  "mode": "full",
  "description": "The video shows a presenter explaining...",
  "num_frames": 8,
  "scenes": 8,
  "duration": "2:34"
}
```

### Mode: `stream`

Detailed frame-by-frame analysis with subjects, objects, actions.

```bash
sq media describe_video --file video.mp4 --mode stream

# Output:
{
  "mode": "stream",
  "frames": [
    {"frame": 1, "timestamp": "0:00", "description": "SUBJECTS: Person... OBJECTS: ..."},
    {"frame": 2, "timestamp": "0:15", "description": "SUBJECTS: ..."}
  ]
}
```

### Mode: `diff`

Tracks changes between frames - what appeared, moved, or disappeared.

```bash
sq media describe_video --file video.mp4 --mode diff

# Output:
{
  "mode": "diff",
  "timeline": [
    {"frame": 1, "type": "start", "description": "Empty room..."},
    {"frame": 2, "type": "change", "changes": "NEW: Person entered..."}
  ],
  "summary": "Person enters room, sits at desk...",
  "significant_changes": 5
}
```

> 📚 **Full documentation**: [examples/media-processing/README.md](../../examples/media-processing/README.md)

### Video Description (Legacy)

### Video Surveillance

```bash
#!/bin/bash
# Monitor camera with AI

while true; do
    # Capture frame
    ffmpeg -i rtsp://camera/stream -vframes 1 frame.jpg -y
    
    # Analyze
    desc=$(sq media describe_image --file frame.jpg | jq -r '.description')
    
    # Alert on person detection
    if echo "$desc" | grep -i "person"; then
        sq slack security --message "⚠️ Person detected: $desc"
    fi
    
    sleep 5
done
```

## 🖼️ Image Analysis

### Image Description

```bash
# Describe image
sq media describe_image --file photo.jpg

# Custom prompt
sq media describe_image --file artwork.jpg \
  --prompt "Describe the artistic style and techniques used"
```

### Content Moderation

```bash
# Check if image is appropriate
desc=$(sq media describe_image --file upload.jpg | jq -r '.description')
result=$(echo "$desc" | sq llm "is this appropriate?" --analyze)

if echo "$result" | grep -i "no"; then
    echo "Content flagged"
    mv upload.jpg quarantine/
fi
```

## 🎤 Audio Processing

### Speech-to-Text (STT)

```bash
# Basic transcription
sq media transcribe --file audio.mp3

# Save to file
sq media transcribe --file interview.mp3 --output transcript.txt

# Specific language
sq media transcribe --file spanish.mp3 --language es
```

### Podcast Transcription

```bash
#!/bin/bash
# Complete podcast workflow

# Download
sq get https://podcast.com/episode.mp3 --save episode.mp3

# Transcribe
sq media transcribe --file episode.mp3 --output transcript.txt

# Summarize
cat transcript.txt | sq llm "summarize key points" > summary.txt

# Generate blog post
sq llm "write blog post from: $(cat transcript.txt)" > blog.md
```

### Text-to-Speech (TTS)

```bash
# Generate speech
sq media speak --text "Hello, welcome to our service" --output welcome.wav

# Long text
cat announcement.txt | sq media speak --output announcement.wav
```

## 🎵 Music Analysis

```bash
# Analyze music properties
sq media analyze_music --file song.mp3

# Output:
{
  "tempo": 120.5,
  "duration": 180.0,
  "sample_rate": 44100
}

# Describe music mood
sq media analyze_music --file song.mp3 | \
  sq llm "describe the mood and style" --analyze
```

## 🚀 Service Deployment

### Deploy Media API

```bash
# Create Flask service
cat > media_api.py << 'EOF'
from flask import Flask, request, jsonify
import subprocess
import json

app = Flask(__name__)

@app.route('/analyze/video', methods=['POST'])
def analyze_video():
    file = request.files['video']
    file.save('temp.mp4')
    
    result = subprocess.run(
        ['sq', 'media', 'describe_video', '--file', 'temp.mp4'],
        capture_output=True, text=True
    )
    
    return result.stdout

@app.route('/transcribe', methods=['POST'])
def transcribe():
    file = request.files['audio']
    file.save('temp.mp3')
    
    result = subprocess.run(
        ['sq', 'media', 'transcribe', '--file', 'temp.mp3'],
        capture_output=True, text=True
    )
    
    return result.stdout

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
EOF

# Install as service (no Docker/systemd needed!)
sq service install --name media-api --command "python media_api.py"

# Start
sq service start --name media-api

# Check status
sq service status --name media-api

# Use API
curl -X POST -F "video=@video.mp4" http://localhost:8080/analyze/video
```

### Service Management

```bash
# Start service
sq service start --name media-api

# Stop service
sq service stop --name media-api

# Restart
sq service restart --name media-api

# Status
sq service status --name media-api

# List all services
sq service list

# Uninstall
sq service uninstall --name media-api
```

## 💡 Advanced Examples

### Video Summary Generation

```bash
#!/bin/bash
# Complete video analysis

VIDEO="lecture.mp4"

# Visual description
visual=$(sq media describe_video --file "$VIDEO" | jq -r '.description')

# Audio transcription
audio=$(sq media transcribe --file "$VIDEO" | jq -r '.text')

# Combined summary
cat << EOF | sq llm "create comprehensive summary"
Visual Content: $visual

Spoken Content: $audio
EOF
```

### Multilingual Content

```bash
# Transcribe multiple languages
for file in uploads/*.mp3; do
    lang=$(detect_language "$file")
    sq media transcribe --file "$file" --language "$lang" \
      --output "${file%.mp3}.txt"
done
```

### Content Pipeline

```bash
# Complete content processing pipeline
sq media describe_video --file raw.mp4 | \
  sq llm "generate social media posts" | \
  sq post https://api.social.com/posts
```

## 📊 Supported Models

| Model | Type | Provider | Use Case |
|-------|------|----------|----------|
| **llava** | Vision-Language | Ollama | Video/Image description |
| **whisper** | Speech Recognition | OpenAI | Audio transcription |
| **bark** | TTS | Suno | Text-to-speech |
| **musicgen** | Music Gen | Facebook | Music generation |

## 🔧 Installation

### LLaVA (Vision)

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull LLaVA model
ollama pull llava
```

### Whisper (STT)

```bash
pip install openai-whisper
```

### Bark (TTS)

```bash
pip install bark
```

## 🎯 Use Cases

### 1. Video Surveillance
Monitor cameras with AI alerts

### 2. Content Moderation
Automatically flag inappropriate content

### 3. Podcast Transcription
Convert audio to searchable text

### 4. Accessibility
Generate captions and audio descriptions

### 5. Content Creation
AI-powered summaries and social posts

### 6. Music Analysis
Analyze and categorize music libraries

## 📝 Tips

1. **Batch Processing**: Process multiple files in parallel
2. **Caching**: Cache AI results to save API costs
3. **Quality**: Use higher quality models for better results
4. **Languages**: Specify language for better transcription
5. **Services**: Deploy as background services for production

---

**AI-Powered Media Analysis with Streamware!** 🎬🤖✨
