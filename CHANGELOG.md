# Changelog

All notable changes to Streamware will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

### 📚 Documentation

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
