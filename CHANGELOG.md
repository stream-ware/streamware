# Changelog

All notable changes to Streamware will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2024-12-11

### 🔧 Major Refactoring - Complete Configuration System (BREAKING CHANGES)

**🎯 Core Achievement:** Eliminated all hardcoded values and implemented comprehensive configuration system.

#### ✅ Refactored Components

**smart_detector.py:**

- All YOLO detection thresholds now configurable (`SQ_YOLO_CONFIDENCE_THRESHOLD`, `SQ_YOLO_CONFIDENCE_THRESHOLD_HIGH`)
- HOG person detection parameters configurable (`SQ_HOG_SCALE`, `SQ_HOG_WINSTRIDE`, `SQ_HOG_PADDING`, `SQ_HOG_SCALE_FACTOR`)
- Motion detection thresholds configurable (`SQ_MOTION_DIFF_THRESHOLD`, `SQ_MOTION_BLUR_KERNEL`, `SQ_MOTION_CONTOUR_MIN_AREA`)
- Motion classification thresholds configurable (`SQ_MOTION_MIN_PERCENT`, `SQ_MOTION_LOW_PERCENT`, `SQ_MOTION_MEDIUM_PERCENT`, `SQ_MOTION_HIGH_PERCENT`)

**live_narrator.py:**

- All vision model prompts configurable through environment variables
- Vision model confidence thresholds configurable (`SQ_VISION_ASSUME_PRESENT`, `SQ_VISION_CONFIDENT_PRESENT`, `SQ_VISION_CONFIDENT_ABSENT`)
- Image optimization parameters configurable (`SQ_IMAGE_PRESET`, `SQ_IMAGE_MAX_SIZE`, `SQ_IMAGE_QUALITY`)
- Frame processing parameters configurable (`SQ_FRAME_SCALE`, `SQ_LLM_MIN_MOTION_PERCENT`)

**response_filter.py:**

- All timeout values configurable (`SQ_GUARDER_TIMEOUT`, `SQ_QUICK_PERSON_TIMEOUT`, `SQ_QUICK_CHANGE_TIMEOUT`, `SQ_SUMMARIZE_TIMEOUT`, `SQ_VALIDATE_TIMEOUT`, `SQ_ANALYZE_TIMEOUT`, `SQ_ANALYZE_TRACKING_TIMEOUT`)
- Guarder model configuration (`SQ_GUARDER_MODEL`, `SQ_ANALYSIS_MODEL`)
- Improved track mode logic to prevent false negatives

#### 🛠️ Code Quality Improvements

**Modularity Enhancements:**

- Added `_fallback_summary()` helper function to eliminate 3x code duplication
- Added `_get_confidence_threshold()` helper function to eliminate 6x code duplication
- Improved error handling with configurable fallback values
- Better separation of concerns in response filtering

**Linting Fixes:**

- Fixed all regex linting issues in response_filter.py
- Fixed f-string warnings in config.py
- Improved code readability and maintainability

#### 🐛 Bug Fixes

**Critical Fixes:**

- Fixed guarder filter blocking track mode responses
- Resolved `NameError: name 'config' is not defined` in default function arguments
- Improved TTS system to announce scene descriptions instead of "No person visible"
- Enhanced error handling for vision model failures

#### 📚 Documentation Updates

**New Documentation:**

- **CONFIGURATION.md** - Complete configuration reference with all new parameters
- Updated **LLM_INTEGRATION.md** with timeout configuration and custom prompts
- Updated **PERFORMANCE.md** with configuration-based performance tuning
- Updated **MOTION_ANALYSIS.md** with configurable motion thresholds

**Enhanced README.md:**

- Added comprehensive refactoring section
- Added configuration examples for different use cases
- Updated documentation index with new configuration guide

#### ⚙️ New Configuration Options

**Total New Environment Variables:** 25+

**Key Categories:**

- **Detection Thresholds:** YOLO, HOG, motion detection sensitivity
- **Timeout Configuration:** All LLM operation timeouts
- **Performance Tuning:** Frame processing, memory optimization
- **Model Configuration:** Vision models, guarder models, analysis models
- **Custom Prompts:** All LLM prompts now customizable
- **Resource Management:** RAM disk, concurrent operations, queue sizes

#### 🔄 Migration Guide

**For Existing Users:**

```bash
# Your existing .env file will work with defaults
# But you can now fine-tune these parameters:

# Example: High sensitivity detection
SQ_YOLO_CONFIDENCE_THRESHOLD=0.1
SQ_VISION_CONFIDENT_PRESENT=0.8

# Example: Fast performance mode
SQ_MODEL=moondream
SQ_IMAGE_PRESET=fast
SQ_LLM_MIN_MOTION_PERCENT=50
```

**Breaking Changes:**

- None - all existing configurations remain compatible
- New parameters use sensible defaults
- Backward compatibility maintained

#### 🧪 Testing & Validation

**System Testing:**

- ✅ Vision LLM person detection working correctly
- ✅ Guarder filter processing responses in track mode
- ✅ TTS announcing scene descriptions properly
- ✅ All configuration parameters loading correctly
- ✅ Error handling with fallback values working
- ✅ Performance improvements validated

**Performance Impact:**

- No performance degradation from refactoring
- Improved configurability allows better optimization
- Better error handling reduces system hangs

---

## [0.2.1] - 2024-12-10

### 🎥 Real-time Visualizer (NEW!)

New `sq visualize` command for real-time motion detection with web UI:

- **Video Modes** - `ws` (WebSocket), `hls`, `meta` (metadata-only), `webrtc`
- **Transport Options** - `tcp` (stable) or `udp` (lower latency)
- **Capture Backends** - `opencv`, `gstreamer`, `pyav` (direct API)
- **SVG Overlay** - Motion detection bounding boxes in real-time
- **DSL Metadata** - Structured motion events with timestamps
- **Latency Display** - Real-time latency measurement in browser

```bash
sq visualize --url "rtsp://camera/stream" --port 8080
sq visualize --url "rtsp://camera/stream" --video-mode meta --backend pyav --transport udp
```

### 📡 MQTT DSL Publisher (NEW!)

New `sq mqtt` command to publish motion events to MQTT broker:

- **Topics** - motion, events, frame, dsl, preview, status
- **QoS Levels** - Configurable per topic type
- **Motion Threshold** - Publish events only above threshold
- **Home Assistant** - Ready for integration

```bash
sq mqtt --url "rtsp://camera/stream" --broker localhost --topic home/camera/front
```

### ⚡ CLI Startup Optimization

**66x faster CLI startup** (4s → 0.06s):

- Lazy imports in `streamware/__init__.py`
- Modules loaded only when accessed
- No impact on functionality

### 🔧 RTSP Capture Improvements

- **Buffer Flush** - Automatic flush at startup to remove stale frames
- **Minimal Buffering** - 64KB buffer (down from 2MB)
- **Low Delay Flags** - `max_delay=0`, `fflags=nobuffer`
- **Multiple Backends** - opencv, gstreamer, pyav support

### 📚 Documentation

- [docs/REALTIME_VISUALIZER.md](docs/REALTIME_VISUALIZER.md) - Visualizer guide
- [docs/MQTT_PUBLISHER.md](docs/MQTT_PUBLISHER.md) - MQTT integration
- [examples/media-processing/realtime_visualizer_examples.sh](examples/media-processing/realtime_visualizer_examples.sh)
- [examples/media-processing/mqtt_integration.py](examples/media-processing/mqtt_integration.py)

---

## [0.2.0] - 2024-12-10

### ⚡ Performance Optimizations

Major performance improvements for Live Narrator real-time video analysis:

- **FastCapture** - Persistent RTSP connection (4000ms → 0ms capture time)
  
  - OpenCV backend with auto-fallback to FFmpeg
  - GPU acceleration (NVDEC) support
  - Frame buffering (10 frames) for slow processing
  
- **Model Optimization** - Default to fast models
  
  - `moondream` as default vision model (~1.5s vs llava:13b ~4s)
  - `gemma:2b` as default guarder (text-only, ~250ms)
  
- **RAM Disk** - `/dev/shm/streamware` for fast frame I/O
- **Smart Caching** - Avoid redundant LLM calls for similar frames
- **Parallel Processing** - 8 workers for I/O tasks

### 🎯 Intelligent Movement Tracking

New `--mode track` with movement direction analysis:

- Detects entering/exiting from frame edges
- Tracks horizontal (left/right) and vertical (approaching/leaving) movement
- Identifies stationary vs moving subjects
- Position history for trajectory analysis

### 🛠️ Bug Fixes

- **Fixed:** `gemma:2b` incorrectly used as vision model in SmartDetector
  
  - Now properly detected as text-only model
  - Falls back to main vision LLM for image analysis
  
- **Fixed:** LLM returning template examples instead of descriptions
  
  - Simplified prompts without copyable examples
  - Added preamble stripping ("Sure, here is...")
  
- **Fixed:** Model matching in setup (gemma: vs gemma2:)
  
  - Precise model name matching
  - Auto-installation of missing models

### 📚 Documentation Improvements

- New: `docs/LIVE_NARRATOR_ARCHITECTURE.md` - Full system architecture
- Updated: README with performance optimization guide
- Updated: `.env.example` with optimal settings

### 🔧 Configuration Changes

**New defaults:**

```ini
SQ_MODEL=moondream
SQ_GUARDER_MODEL=gemma:2b
SQ_STREAM_MODE=track
SQ_STREAM_FOCUS=person
SQ_FAST_CAPTURE=true
```

**New install script:**

```bash
./install_fast_model.sh  # Auto-installs moondream + gemma:2b
```

---

## [0.1.0] - 2024-01-20

### Added
- Initial release of Streamware framework
- Core pipeline engine with pipe operator (`|`) support
- URI-based component configuration
- MIME type validation system
- Camel-style diagnostics and logging

### Components
- **CurLLM** - Web automation with LLM integration
  - Browse, extract, fill forms, take screenshots
  - BQL (Browser Query Language) support
  - Session management
  
- **File Operations**
  - Read, write, append, delete
  - Directory watching
  - Line-by-line streaming
  
- **Data Transformation**
  - JSON/CSV conversion
  - JSONPath queries
  - Jinja2 templates
  - Base64 encoding/decoding
  - Regex operations
  
- **HTTP/REST**
  - Full HTTP methods support
  - GraphQL queries
  - Webhook handling
  - File downloads
  
- **Message Queues**
  - Kafka producer/consumer
  - RabbitMQ publish/subscribe
  - RPC pattern support
  
- **Database**
  - PostgreSQL CRUD operations
  - Query, insert, update, upsert
  - Batch operations
  
- **Communication Channels**
  - Email (SMTP/IMAP) with attachments
  - Telegram bot with commands
  - WhatsApp (Business API, Twilio)
  - Discord bot and webhooks
  - Slack Web API and events
  - SMS (Twilio, Vonage, Plivo)
  - Microsoft Teams webhooks

### Patterns
- Split/Join for parallel processing
- Multicast for broadcasting
- Choose for conditional routing
- Filter for stream filtering
- Aggregate for windowed operations

### Features
- Async/await support
- Generator-based streaming
- CLI interface
- Component auto-registration
- Rate limiting
- Error handling with fallbacks
- Comprehensive test suite
- Rich documentation and examples

### Documentation
- Main README with quick start
- Communication components guide
- 50+ usage examples
- Production-ready patterns

## [0.2.0] - 2025-11-28

### Added
- **Setup Component** - Auto-install dependencies on-the-fly
  - Check installed dependencies
  - Install Python packages automatically
  - Install system packages (apt, brew)
  - Setup Ollama and pull models
  - Component-specific dependency resolution
  
- **Template Component** - Quick project generation
  - Generate projects from templates
  - Templates: video-captioning, text2streamware, api-pipeline, monitoring
  - Auto-install dependencies when generating
  - List and inspect available templates
  
- **Registry Component** - Centralized resource management
  - Register and lookup components
  - Model configurations
  - Template definitions
  - Pipeline presets
  - Configuration sharing
  
- **Video Component** - Real-time video processing
  - RTSP stream reading
  - YOLO object detection
  - Frame analysis with OpenCV
  - AI caption generation
  
- **LLM Component** - Multi-provider LLM operations
  - OpenAI, Anthropic, Ollama support
  - Natural language to SQL conversion
  - Text analysis and summarization
  - Translation capabilities
  
- **Text2Streamware Component** - Natural language to commands
  - Convert text to sq commands using Qwen2.5 14B
  - Command explanation
  - Command optimization
  - Validation
  
- **Deploy Component** - Multi-platform deployment
  - Kubernetes (apply, scale, update, rollback)
  - Docker Compose
  - Docker Swarm
  - Complete CI/CD integration
  
- **SSH Component** - Secure file transfer and execution
  - Upload/download files
  - Execute remote commands
  - Application deployment
  - Supports paramiko and system SSH

### Enhanced
- **Quick CLI (sq)** - New commands added
  - `sq setup` - Dependency management
  - `sq template` - Project generation
  - `sq registry` - Resource management
  - `sq deploy` - Deployment operations
  - `sq llm` - LLM operations
  - `sq ssh` - SSH operations
  
- **Documentation** - Comprehensive updates
  - REFACTORING.md - Architecture and migration guide
  - Component-specific docs with inline menus
  - 100+ real-world examples
  - Complete API references

### Changed
- **Version** - Bumped from 0.1.0 to 0.2.0
- **Status** - Alpha → Beta (Development Status :: 4)
- **License Classifier** - Removed deprecated classifier (keeping Apache-2.0 license)
- **Component Structure** - Standardized with menus and examples

### Projects
- **video-captioning** - Complete RTSP + YOLO + LLM web application
- **text2streamware-demo** - Natural language command generation
- Automated installation scripts
- Docker environments
- CI/CD integration examples

### Infrastructure
- Auto-install system for dependencies
- Template-based project generation
- Local registry at `~/.streamware/registry.json`
- Component dependency tracking
- Smart package management

## [Unreleased]

### Planned
- Redis component
- MongoDB component
- Elasticsearch component
- WebSocket support
- gRPC support
- Apache Pulsar integration
- NATS messaging
- Visual workflow designer
- Kubernetes operator
- Prometheus metrics export
- OpenTelemetry tracing
- Additional LLM providers
- Voice/audio processing
- Video stream processing
- ML model serving
- Workflow orchestration
- DAG visualization
- Web UI for monitoring
- Plugin system
- Custom component SDK

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
