# Changelog

All notable changes to Streamware will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
