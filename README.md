![sq live narrator --url rtsp://192.168.1.1:554/h264Preview_01_main --tts --duration 20 --yaml --frames changed --focus person --tts --file report.html --model llava:13b --motion people](docs/v2/report2.png)


# 🚀 Streamware

<p align="center">
  <a href="https://pypi.org/project/streamware/"><img src="https://img.shields.io/pypi/v/streamware.svg?style=for-the-badge&logo=pypi&logoColor=white" alt="PyPI"></a>
  <a href="https://pypi.org/project/streamware/"><img src="https://img.shields.io/pypi/dm/streamware?style=for-the-badge&logo=pypi&logoColor=white" alt="Downloads"></a>
  <a href="https://github.com/softreck/streamware"><img src="https://img.shields.io/github/stars/softreck/streamware?style=for-the-badge&logo=github" alt="Stars"></a>
  <a href="https://github.com/softreck/streamware/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-green?style=for-the-badge" alt="License"></a>
  <img src="https://img.shields.io/badge/python-3.8+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python">
</p>

<p align="center">
  <b>🎯 One-line automation • 🤖 AI-powered • 🎤 Voice control • 🖥️ Desktop automation</b>
</p>

---

## ⚡ What Can You Do?

```bash
# 🎥 Real-time motion detection with SVG overlay (NEW!)
sq visualize --url "rtsp://camera/stream" --port 8080

# 📡 Publish motion events to MQTT (NEW!)
sq mqtt --url "rtsp://camera/stream" --broker localhost

# 🤖 AI: Convert natural language to SQL
sq llm "Get all users older than 30" --to-sql

# 🎤 Voice: Type with your voice  
sq voice-keyboard "wpisz hello world"

# 🖱️ AI Vision: Click anywhere by description
sq voice-click "click on the Submit button"

# 📧 Send notifications everywhere
sq slack general "Deploy complete! ✅"
sq telegram @channel "Server status: OK"

# 🎬 Analyze video with AI
sq media describe_video --file presentation.mp4

# 🔄 Data pipelines
sq get api.example.com/users | sq transform --json | sq file save users.json
```

---

**Streamware** is a modern Python framework that combines:
- **Apache Camel-style** data pipelines
- **AI/LLM integration** (OpenAI, Ollama, Groq, Anthropic...)
- **Voice control** and desktop automation
- **Multi-channel communication** (Email, Slack, Telegram, Discord...)

## 🎯 Why Streamware?

| Problem | Streamware Solution |
|---------|---------------------|
| "I need to automate repetitive tasks" | `sq auto type "Hello"` - one command |
| "I want AI without complex setup" | `sq llm "explain this code"` - works out of the box |
| "Voice control is complicated" | `sq voice-keyboard` - just speak |
| "Sending notifications is tedious" | `sq slack #channel "message"` - done |
| "ETL pipelines need too much code" | `sq get api | sq transform | sq save` |

## ✨ Features

| Category | Features |
|----------|----------|
| 🎥 **Visualizer** | Real-time motion detection, SVG overlay, DSL metadata, MQTT |
| 🤖 **AI/LLM** | OpenAI, Ollama, Groq, Anthropic, Gemini, DeepSeek, Mistral |
| 🎤 **Voice** | Speech-to-text, text-to-speech, voice commands |
| 🖥️ **Automation** | Mouse, keyboard, screenshots, AI-powered clicking |
| 📡 **Communication** | Email, Slack, Telegram, Discord, WhatsApp, SMS |
| 🔄 **Pipelines** | HTTP, files, transforms, Kafka, RabbitMQ, PostgreSQL |
| 🎬 **Media** | Video analysis, image description, audio transcription |

## 📦 Installation

```bash
# Basic install
pip install streamware

# With all features
pip install streamware[all]

# Or specific features
pip install streamware[llm,voice,automation]
```

### 🛠️ Auto-Configuration

After installation, run the setup wizard to automatically detect your environment (Ollama, API keys, voice settings, etc.):

```bash
# Full setup (LLM + voice) with mode presets
streamware --setup --mode balance      # default
streamware --setup --mode eco          # light models
streamware --setup --mode performance  # maximum quality

# TTS-only setup (does not touch LLM/STT)
streamware --setup tts
```

The setup will detect available LLM providers (Ollama, OpenAI, Anthropic), configure models, and write configuration to your `.env` file.

### 🔍 Diagnostics

Verify your setup with built-in diagnostic checks:

```bash
# Check camera/RTSP connectivity + Ollama
streamware --check camera "rtsp://admin:pass@192.168.1.100:554/stream"

# Check TTS engine (will speak a test message)
streamware --check tts

# Check Ollama connection and model availability
streamware --check ollama

# Run all checks
streamware --check all "rtsp://camera/live"
```

Example output:
```
🔍 Streamware Diagnostics
==================================================

📷 Camera / RTSP Check:
   camera_url: rtsp://admin:pass@192.168.1.100:554/stream
   ffmpeg_capture: ✅ OK (45231 bytes)

🤖 Ollama / LLM Check:
   ollama_url: http://localhost:11434
   model: llava:7b
   ollama_connection: ✅ OK
   model_available: ✅ llava:7b found

🔊 TTS / Voice Check:
   tts_engine: auto
   tts_test: ✅ OK (using espeak)

==================================================
✅ All checks passed!
```

### System Dependencies (optional but recommended)

```bash
# Linux/Ubuntu - for voice and automation
sudo apt-get install xdotool espeak scrot ffmpeg

# macOS
brew install xdotool espeak ffmpeg
```

## 🚀 Quick Start CLI (`sq`)

### 🤖 AI/LLM Commands

```bash
# Generate text
sq llm "Write a haiku about coding"

# Convert to SQL
sq llm "Get users who signed up last week" --to-sql
# Output: SELECT * FROM users WHERE created_at >= DATE_SUB(NOW(), INTERVAL 1 WEEK)

# Analyze code
sq llm --analyze --input main.py

# Use different providers (auto-detects API keys)
sq llm "Hello" --provider openai/gpt-4o
sq llm "Hello" --provider groq/llama3-70b-8192
sq llm "Hello" --provider ollama/qwen2.5:14b
```

### 🎤 Voice Control

```bash
# Type with voice (Polish/English)
sq voice-keyboard "wpisz hello world"
sq voice-keyboard --interactive  # Continuous mode

# AI-powered clicking (finds elements visually!)
sq voice-click "click on the blue Submit button"
sq voice-click "kliknij w menu File"

# Text to speech (uses TTS config from .env)
sq voice speak "Hello, I am Streamware"
```

#### 🔧 Voice / TTS Configuration (.env)

The setup wizard saves audio configuration into `.env` so all tools (`sq voice`, `sq live narrator`, etc.) use the same settings.

Key variables:

- `SQ_STT_PROVIDER` – `google`, `whisper_local`, `whisper_api`
- `SQ_WHISPER_MODEL` – `tiny`, `base`, `small`, `medium`, `large`
- `SQ_TTS_ENGINE` – `auto`, `pyttsx3`, `espeak`, `say`, `powershell`
- `SQ_TTS_VOICE` – fragment nazwy głosu (np. `polski`, `English`)
- `SQ_TTS_RATE` – szybkość mowy (słowa na minutę, np. `150`)

Example: lokalne STT Whisper + polski TTS przez pyttsx3:

```ini
SQ_STT_PROVIDER=whisper_local
SQ_WHISPER_MODEL=small
SQ_TTS_ENGINE=pyttsx3
SQ_TTS_VOICE=polski
SQ_TTS_RATE=160
```

Example: lekkie STT Google + systemowy TTS na Linux (espeak):

```ini
SQ_STT_PROVIDER=google
SQ_TTS_ENGINE=espeak
SQ_TTS_RATE=150
```

### 🖥️ Desktop Automation

```bash
# Mouse
sq auto click --x 100 --y 200
sq auto move --x 500 --y 300

# Keyboard
sq auto type --text "Hello World"
sq auto press --key enter
sq auto hotkey --keys ctrl+s

# Screenshot
sq auto screenshot /tmp/screen.png
```

### 📡 Communication

```bash
# Slack
sq slack general "Deploy complete! 🚀"

# Telegram
sq telegram @mychannel "Server status: OK"

# Email
sq email user@example.com --subject "Report" --body "See attached"

# Discord
sq discord --webhook URL --message "Alert!"
```

### 🎬 Media Analysis

```bash
# Describe image with AI
sq media describe_image --file photo.jpg

# Analyze video (scene tracking!)
sq media describe_video --file video.mp4

# Transcribe audio
sq media transcribe --file audio.mp3
```

### 🚀 Performance Optimization (iGPU / Low VRAM)

For systems with integrated GPU or limited VRAM (4-8GB shared):

```ini
# .env - optimized for speed
SQ_IMAGE_PRESET=fast         # smaller images (384px, 55% quality)
SQ_FRAME_SCALE=0.25          # analyze at 25% resolution
SQ_MOTION_THRESHOLD=30       # less sensitive (fewer LLM calls)
SQ_MODEL=llava:7b            # use 7B instead of 13B
SQ_LLM_TIMEOUT=90            # longer timeout for slow GPU
```

**CLI options for speed:**
```bash
sq live narrator --url "rtsp://..." --mode track --focus person --lite
#                                                              ^^^^^^
#                                              --lite = no images in RAM
```

**Model recommendations:**
| VRAM | Recommended Model | Speed |
|------|-------------------|-------|
| 2GB  | `moondream` ⭐ | ~1.5s |
| 4GB  | `llava:7b` | ~2-3s |
| 8GB  | `llava:13b` | ~4-5s |

### ⚡ Performance Optimizations (NEW)

Streamware includes major performance optimizations for real-time video analysis:

| Optimization | Before | After | Improvement |
|--------------|--------|-------|-------------|
| **FastCapture** | 4000ms | 0ms | Persistent RTSP connection |
| **Vision LLM** | 4000ms | 1500ms | moondream instead of llava:13b |
| **Guarder LLM** | 2700ms | 250ms | gemma:2b |
| **Total cycle** | 10s | 2s | **80% faster** |

**Quick setup for fast mode:**
```bash
# Install fast models (auto-installs on first run)
./install_fast_model.sh

# Or manually:
ollama pull moondream    # Fast vision model
ollama pull gemma:2b     # Fast guarder (text-only!)
```

**Optimal `.env` for speed:**
```ini
SQ_MODEL=moondream            # 2-3x faster than llava:13b
SQ_GUARDER_MODEL=gemma:2b     # Fast text filtering
SQ_FAST_CAPTURE=true          # Persistent RTSP connection
SQ_RAMDISK_ENABLED=true       # RAM disk for frames
SQ_STREAM_MODE=track          # Smart movement tracking
SQ_STREAM_FOCUS=person        # Focus on person detection
```

📖 **Full architecture documentation:** [docs/LIVE_NARRATOR_ARCHITECTURE.md](docs/LIVE_NARRATOR_ARCHITECTURE.md)

### 🛡️ Smart Response Filtering (Guarder)

Streamware uses a small text LLM to summarize and filter verbose vision model responses:

```bash
# Install fast guarder model
ollama pull gemma:2b
```

**⚠️ Important:** `gemma:2b` is a **text-only** model - it cannot analyze images. It only summarizes text responses from the vision model.

**Configuration (`.env`):**
```ini
SQ_GUARDER_MODEL=gemma:2b     # Fast text summarization
SQ_USE_GUARDER=true           # Enabled by default
```

**How it works:**
```
Vision LLM (llava:7b) → Response → Guarder (qwen2.5:3b) → YES/NO
                                                           │
                                        YES → Log + TTS ───┘
                                        NO  → Skip (noise)
```

**CLI options:**
```bash
# Full monitoring with smart filtering
sq live narrator --url "rtsp://..." --mode track --focus person --tts

# Disable guarder (use regex only)
sq live narrator --url "rtsp://..." --no-guarder

# Lite mode (less RAM) + quiet
sq live narrator --url "rtsp://..." --lite --quiet
```

### ⚡ Image Optimization for LLM

Streamware automatically optimizes images before sending to vision LLMs to reduce latency and API costs:

| Preset | Max Size | Quality | Colors | Use Case |
|--------|----------|---------|--------|----------|
| `fast` | 384px | 55% | 32 | Real-time monitoring, low latency |
| `balanced` | 512px | 65% | full | Default, good quality/speed balance |
| `quality` | 768px | 75% | full | Detailed analysis, accuracy priority |
| `minimal` | 256px | 50% | 16+grayscale | Extreme speed, basic detection |

Configure in `.env`:

```ini
# Use preset
SQ_IMAGE_PRESET=fast

# Or custom settings
SQ_IMAGE_MAX_SIZE=512      # max dimension in pixels
SQ_IMAGE_QUALITY=65        # JPEG quality 1-100
SQ_IMAGE_POSTERIZE=0       # 0=off, 8-256=reduce colors
SQ_IMAGE_GRAYSCALE=false   # convert to grayscale
```

**Optimization pipeline:**
1. **Crop to motion region** – only send changed area to LLM
2. **Downscale** – reduce to max 384-768px (configurable)
3. **JPEG compression** – quality 55-75% (minimal visual loss)
4. **Optional posterization** – reduce colors for faster processing
5. **Sharpening** – preserve edges after downscaling

### 📊 Logging & Reports

```bash
# Real-time logs in terminal
sq live narrator --url "rtsp://..." --mode diff --tts

# Save to file while watching
sq live narrator --url "rtsp://..." --mode diff 2>&1 | tee live.log

# Generate Markdown summary after run
sq watch --url "rtsp://..." --detect person --log md
# -> watch_log.md

sq live narrator --url "rtsp://..." --log md --file logs/live.md
# -> logs/live.md
```

### 🔄 Data Pipelines

```bash
# API to file
sq get api.example.com/users | sq file save users.json

# Transform data
sq file read data.csv | sq transform --csv --json | sq file save data.json

# PostgreSQL
sq postgres "SELECT * FROM users" --json
```

### 📝 Custom Prompts

All LLM prompts are stored in `streamware/prompts/*.txt` and can be customized:

```bash
# List available prompts
ls streamware/prompts/
# stream_diff.txt, trigger_check.txt, motion_region.txt, ...

# Edit a prompt
nano streamware/prompts/stream_diff.txt
```

Override via environment:
```bash
export SQ_PROMPT_STREAM_DIFF="Your custom prompt template with {variables}..."
```

Available prompts:
- `stream_diff` – frame comparison for sq stream
- `stream_focus` – focused object detection
- `trigger_check` – trigger condition checking
- `motion_region` – motion region analysis
- `tracking_detect` – object tracking
- `live_narrator_*` – live narration modes

---

## 🏗️ Architecture

### Core Modules

| Module | Description |
|--------|-------------|
| `llm_client.py` | Centralized LLM client with connection pooling, retries, metrics |
| `tts.py` | Unified TTS with automatic engine detection and fallback |
| `image_optimize.py` | Image preprocessing for vision LLMs (downscale, compress) |
| `prompts/` | External prompt templates (editable .txt files) |

### LLM Client Usage
```python
from streamware.llm_client import vision_query, get_client

# Quick query
result = vision_query("/path/to/image.jpg", "Describe this image")

# With metrics
client = get_client()
result = client.analyze_image(image_path, prompt)
print(client.get_metrics())  # {'total_calls': 5, 'avg_time_ms': 1200, ...}
```

### TTS Usage
```python
from streamware.tts import speak, get_available_engines

# Check available engines
print(get_available_engines())  # ['espeak', 'pyttsx3']

# Speak with options
speak("Hello world", engine="espeak", rate=150)
```

---

## 📖 Python API

### Simple Pipeline
```python
from streamware import flow
from streamware.dsl import configure

# Configure environment (optional)
configure(SQ_MODEL="llama3", SQ_DEBUG="true")

# Basic data transformation pipeline
result = (
    flow("http://api.example.com/data")
    | "transform://jsonpath?query=$.items[*]"
    | "file://write?path=/tmp/output.json"
).run()
```

### Fluent DSL with Configuration
```python
from streamware.dsl import Pipeline

# Configure and run in one chain
Pipeline() \
    .configure("SQ_MODEL", "gpt-4-vision") \
    .http_get("https://api.example.com/data") \
    .to_json() \
    .save("output.json") \
    .run()
```

### Streaming Pipeline
```python
# Real-time video processing
for frame in (
    flow("rtsp://camera/live")
    | "transcode://mp4?codec=h264"
    | "detect://faces"
    | "annotate://bbox"
).stream():
    process_frame(frame)
```

### CurLLM Integration
```python
# Web automation with LLM
result = (
    flow("curllm://browse?url=https://example.com")
    | "curllm://extract?instruction=Find all product prices under $50"
    | "transform://csv"
    | "file://write?path=products.csv"
).run()
```

## 🧩 Core Components

### HTTP/REST Component
```python
# GET request
flow("http://api.example.com/data").run()

# POST with data
flow("http://api.example.com/users?method=post").run({"name": "John"})

# GraphQL query
flow("graphql://api.example.com").run({"query": "{ users { id name } }"})
```

### Communication Components

#### Email
```python
# Send email
flow("email://send?to=user@example.com&subject=Hello").run("Message body")

# Watch inbox
for email in flow("email-watch://interval=60").stream():
    print(f"New email: {email['subject']}")
```

#### Telegram
```python
# Send message to Telegram
flow("telegram://send?chat_id=@channel&token=BOT_TOKEN").run("Hello!")

# Telegram bot
bot = flow("telegram-bot://token=BOT_TOKEN") | "telegram-command://"
```

#### WhatsApp
```python
# Send WhatsApp message (via Twilio)
flow("whatsapp://send?provider=twilio&to=+1234567890").run("Hello!")
```

#### Discord
```python
# Send to Discord channel
flow("discord://send?channel_id=123456&token=BOT_TOKEN").run("Announcement")

# Discord webhook
flow("discord://webhook?url=WEBHOOK_URL").run({"content": "Alert!"})
```

#### Slack
```python
# Post to Slack
flow("slack://send?channel=general&token=xoxb-TOKEN").run("Team update")

# Upload file to Slack
flow("slack://upload?channel=reports").run({"file": "report.pdf"})
```

#### SMS
```python
# Send SMS via Twilio
flow("sms://send?provider=twilio&to=+1234567890").run("Alert: System down!")

# Bulk SMS
flow("sms://bulk?numbers=+123,+456,+789").run("Broadcast message")
```

```python
flow("http://api.example.com/users")
```

# POST with data
```python
flow("http://api.example.com/users?method=post") \
    .with_data({"name": "John", "email": "john@example.com"})
```

### File Component
```python
# Read file
flow("file://read?path=/tmp/input.json")

# Write file
flow("file://write?path=/tmp/output.csv&mode=append")
```

### Transform Component
```python
# JSONPath extraction
flow("transform://jsonpath?query=$.users[?(@.age>18)]")

# Jinja2 template
flow("transform://template?file=report.j2")

# CSV conversion
flow("transform://csv?delimiter=;")
```

### CurLLM Component
```python
# Web scraping with LLM
flow("curllm://browse?url=https://example.com&visual=true&stealth=true") \
    | "curllm://extract?instruction=Extract all email addresses" \
    | "curllm://fill_form?data={'name':'John','email':'john@example.com'}"

# BQL (Browser Query Language)
flow("curllm://bql?query={page(url:'https://example.com'){title,links{text,url}}}")
```

## 🔥 Advanced Workflow Patterns

### Split/Join Pattern
```python
from streamware import flow, split, join

# Process items in parallel
result = (
    flow("http://api.example.com/items")
    | split("$.items[*]")  # Split array into individual items
    | "enrich://product_details"  # Process each item
    | join()  # Collect results back
    | "file://write?path=enriched.json"
).run()
```

### Multicast Pattern
```python
from streamware import flow, multicast

# Send to multiple destinations
flow("kafka://orders?topic=new-orders") \
    | multicast([
        "postgres://insert?table=orders",
        "rabbitmq://publish?exchange=notifications",
        "file://append?path=orders.log"
    ]).run()
```

### Choice/Switch Pattern
```python
from streamware import flow, choose

# Conditional routing
flow("http://api.example.com/events") \
    | choose() \
        .when("$.priority == 'high'", "kafka://high-priority") \
        .when("$.priority == 'low'", "rabbitmq://low-priority") \
        .otherwise("file://write?path=unknown.log") \
    .run()
```

## 🔌 Message Broker Integration

### Kafka
```python
# Consume from Kafka
flow("kafka://consume?topic=events&group=processor") \
    | "transform://json" \
    | "postgres://insert?table=events"

# Produce to Kafka
flow("file://watch?path=/tmp/uploads") \
    | "transform://json" \
    | "kafka://produce?topic=files&key=filename"
```

### RabbitMQ
```python
# Consume from RabbitMQ
flow("rabbitmq://consume?queue=tasks&auto_ack=false") \
    | "process://task_handler" \
    | "rabbitmq://ack"

# Publish to exchange
flow("postgres://query?sql=SELECT * FROM orders WHERE status='pending'") \
    | "rabbitmq://publish?exchange=orders&routing_key=pending"
```

### PostgreSQL
```python
# Query and transform
flow("postgres://query?sql=SELECT * FROM users WHERE active=true") \
    | "transform://jsonpath?query=$[?(@.age>25)]" \
    | "kafka://produce?topic=adult-users"

# Stream changes (CDC-like)
flow("postgres://stream?table=orders&events=insert,update") \
    | "transform://normalize" \
    | "elasticsearch://index?index=orders"
```

## 🎬 Multimedia Processing

### Video Streaming
```python
# RTSP to MP4 with face detection
flow("rtsp://camera/live") \
    | "transcode://mp4?codec=h264&fps=30" \
    | "detect://faces?model=haar" \
    | "annotate://bbox?color=green" \
    | "stream://hls?segment=10"
```

### Audio Processing
```python
# Speech to text pipeline
flow("audio://capture?device=default") \
    | "audio://denoise" \
    | "stt://whisper?lang=en" \
    | "transform://correct_grammar" \
    | "file://append?path=transcript.txt"
```

## 📊 Diagnostics and Monitoring

### Enable Debug Logging
```python
import streamware
streamware.enable_diagnostics(level="DEBUG")

# Detailed Camel-style logging
flow("http://api.example.com/data") \
    .with_diagnostics(trace=True) \
    | "transform://json" \
    | "file://write"
```

### Metrics Collection
```python
from streamware import flow, metrics

# Track pipeline metrics
with metrics.track("pipeline_name"):
    flow("kafka://consume?topic=events") \
        | "process://handler" \
        | "postgres://insert"
        
# Access metrics
print(metrics.get_stats("pipeline_name"))
# {'processed': 1000, 'errors': 2, 'avg_time': 0.034}
```

## 🔧 Creating Custom Components

```python
from streamware import Component, register

@register("mycustom")
class MyCustomComponent(Component):
    input_mime = "application/json"
    output_mime = "application/json"
    
    def process(self, data):
        # Synchronous processing
        return transform_data(data)
    
    async def process_async(self, data):
        # Async processing
        return await async_transform(data)
    
    def stream(self, input_stream):
        # Streaming processing
        for item in input_stream:
            yield process_item(item)

# Use your custom component
flow("http://api.example.com/data") \
    | "mycustom://transform?param=value" \
    | "file://write"
```

## 🌐 System Protocol Handler

Install system-wide `stream://` protocol:

```bash
# Install handler
streamware install-protocol

# Now you can use in terminal:
curl stream://http/get?url=https://api.example.com

# Or in browser:
stream://curllm/browse?url=https://example.com
```

## 🧪 Testing

```python
import pytest
from streamware import flow, mock_component

def test_pipeline():
    # Mock external components
    with mock_component("http://api.example.com/data", returns={"items": [1, 2, 3]}):
        result = (
            flow("http://api.example.com/data")
            | "transform://jsonpath?query=$.items"
            | "transform://sum"
        ).run()
        
        assert result == 6
```

## 📚 Examples

### Web Scraping Pipeline
```python
# Extract product data with CurLLM
(
    flow("curllm://browse?url=https://shop.example.com&stealth=true")
    | "curllm://extract?instruction=Find all products under $50"
    | "transform://enrich_with_metadata"
    | "postgres://upsert?table=products&key=sku"
    | "kafka://produce?topic=price-updates"
).run()
```

### Real-time Data Processing
```python
# Process IoT sensor data
(
    flow("mqtt://subscribe?topic=sensors/+/temperature")
    | "transform://celsius_to_fahrenheit"
    | "filter://threshold?min=32&max=100"
    | "aggregate://average?window=5m"
    | "influxdb://write?measurement=temperature"
).run_forever()
```

### ETL Pipeline
```python
# Daily ETL job
(
    flow("postgres://query?sql=SELECT * FROM raw_events WHERE date=TODAY()")
    | "transform://clean_data"
    | "transform://validate"
    | "split://batch?size=1000"
    | "s3://upload?bucket=processed-events&prefix=daily/"
    | "notify://slack?channel=data-team"
).schedule(cron="0 2 * * *")
```

## 🔗 Component Reference

### Core Components
- **HTTP/REST**: HTTP client, REST API, webhooks, GraphQL
- **File**: Read, write, watch, delete files
- **Transform**: JSON, CSV, JSONPath, templates, base64, regex
- **CurLLM**: Web automation, browsing, extraction, form filling

### Communication Components
- **Email**: SMTP/IMAP, send, receive, watch, filter emails
- **Telegram**: Bot API, send messages, photos, documents, commands
- **WhatsApp**: Business API, Twilio, templates, media
- **Discord**: Bot API, webhooks, embeds, threads
- **Slack**: Web API, events, slash commands, file uploads
- **SMS**: Twilio, Vonage, Plivo, bulk messaging, verification

### Message Queue Components
- **Kafka**: Producer, consumer, topics, partitions
- **RabbitMQ**: Publish, subscribe, RPC, exchanges
- **Redis**: Pub/sub, queues, caching

### Database Components
- **PostgreSQL**: Query, insert, update, upsert, streaming
- **MongoDB**: CRUD operations, aggregation
- **Elasticsearch**: Search, index, aggregation

## 📡 Multi-Channel Communication

### Unified Messaging
```python
# Send notification to all user's preferred channels
user_preferences = get_user_preferences(user_id)

notification = "Important: Your order has been shipped!"

flow("choose://") \
    .when(f"'email' in {user_preferences}", 
          f"email://send?to={{user_email}}") \
    .when(f"'sms' in {user_preferences}", 
          f"sms://send?to={{user_phone}}") \
    .when(f"'telegram' in {user_preferences}", 
          f"telegram://send?chat_id={{telegram_id}}") \
    .run(notification)
```

### Customer Support Hub
```python
# Centralized support system handling all channels
support_hub = (
    flow("multicast://sources")
    .add_source("email-watch://folder=support")
    .add_source("telegram-bot://commands=/help,/support")
    .add_source("whatsapp-webhook://")
    .add_source("slack-events://channel=customer-support")
    | "transform://normalize_message"
    | "curllm://analyze?instruction=Categorize issue and suggest response"
    | "postgres://insert?table=support_tickets"
    | "auto_respond://template={{suggested_response}}"
)

# Run support hub
support_hub.run_forever()
```

### Marketing Automation
```python
# Personalized campaign across channels
campaign = (
    flow("postgres://query?sql=SELECT * FROM subscribers")
    | "split://parallel"
    | "enrich://behavioral_data"
    | "curllm://personalize?instruction=Create personalized message"
    | "choose://"
      .when("$.engagement_score > 80", [
          "email://send?template=vip_offer",
          "sms://send?priority=high"
      ])
      .when("$.engagement_score > 50", 
            "email://send?template=standard_offer")
      .when("$.last_interaction > '30 days'", [
          "email://send?template=win_back",
          "wait://days=3",
          "sms://send?message=We miss you! 20% off"
      ])
)
```

### Incident Response System
```python
# Multi-tier escalation with failover
incident_response = (
    flow("monitoring://alerts?severity=critical")
    | "create_incident://pagerduty"
    | "notify://tier1"
    .add_channel("slack://send?channel=oncall")
    .add_channel("sms://send?to={{oncall_primary}}")
    .add_channel("telegram://send?chat_id={{oncall_chat}}")
    | "wait://minutes=5"
    | "check://acknowledged"
    | "choose://"
      .when("$.acknowledged == false", [
          "notify://tier2",
          "phone://call?to={{oncall_secondary}}",
          "email://send?to=managers@company.com&priority=urgent"
      ])
    | "wait://minutes=10"
    | "choose://"
      .when("$.acknowledged == false", [
          "notify://tier3",
          "sms://send?to={{cto_phone}}",
          "create_conference://zoom?participants={{emergency_team}}"
      ])
)
```

## 📖 Documentation

- [Communication Components Guide](docs/COMMUNICATION.md) - Detailed guide for email, chat, and SMS
- [API Reference](https://streamware.readthedocs.io/api) - Complete API documentation
- [Examples](examples/) - Full example implementations
- [Advanced Examples](examples_advanced_communication.py) - Production-ready communication patterns

| Component | URI Pattern | Description |
|-----------|------------|-------------|
| HTTP | `http://host/path` | HTTP requests |
| File | `file://operation?path=...` | File operations |
| Transform | `transform://type?params` | Data transformation |
| CurLLM | `curllm://action?params` | Web automation with LLM |
| Kafka | `kafka://operation?params` | Kafka integration |
| RabbitMQ | `rabbitmq://operation?params` | RabbitMQ integration |
| PostgreSQL | `postgres://operation?params` | PostgreSQL operations |
| Split | `split://pattern` | Split data into parts |
| Join | `join://strategy` | Join split data |
| Multicast | `multicast://` | Send to multiple destinations |
| Choose | `choose://` | Conditional routing |
| Filter | `filter://condition` | Filter data |
| Aggregate | `aggregate://function` | Aggregate over window |

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Development setup
git clone https://github.com/softreck/streamware.git
cd streamware
pip install -e ".[dev]"
pytest
```

## 📄 License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- Apache Camel for inspiration
- CurLLM for web automation capabilities
- The Python streaming community

## 📞 Support

- 📧 Email: info@softreck.com
- 🐛 Issues: [GitHub Issues](https://github.com/softreck/streamware/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/softreck/streamware/discussions)

---

Built with ❤️ by [Softreck](https://softreck.com)

⭐ Star us on [GitHub](https://github.com/softreck/streamware)!
