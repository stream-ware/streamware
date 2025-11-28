# Streamware

<p align="center">
  <img src="https://img.shields.io/pypi/v/streamware.svg" alt="PyPI version">
  <img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/license-Apache%202.0-green.svg" alt="License">
</p>

**Modern Python stream processing framework inspired by Apache Camel**

Streamware is a lightweight, Pythonic stream processing framework that brings the power of Apache Camel-style workflows to Python. It features native support for streaming data, protocol handlers, and integrations with popular message brokers and databases.

## ✨ Features

- 🚀 **Camel-style URI routing** with native Python operators
- 🔄 **Streaming data pipelines** with generator-based processing
- 🎯 **Component registry** with automatic MIME type validation
- 🌊 **Advanced workflow patterns**: split/join, multicast, switch
- 🔌 **Rich integrations**: Kafka, RabbitMQ, PostgreSQL, CurLLM
- 📊 **Built-in diagnostics** and structured logging
- 🎬 **Multimedia support**: RTSP, MP4, audio transcription
- 🌐 **Protocol handlers**: `stream://`, `chat://` system protocols

## 📦 Installation

### Option 1: pip install (Basic)
```bash
pip install streamware
```

### Option 2: pip install (Full)
```bash
# For CurLLM integration (web automation with LLM)
pip install streamware[curllm]

# For message brokers
pip install streamware[kafka,rabbitmq]

# For database support
pip install streamware[postgres]

# For multimedia processing
pip install streamware[multimedia]

# Everything
pip install streamware[all]
```

### Option 3: Docker (Recommended for Testing) 🐳

```bash
# Clone and start
git clone https://github.com/softreck/streamware.git
cd streamware
docker-compose up -d

# Enter container
docker-compose exec streamware bash

# Start using!
sq get mock-api:8080/users --json
```

See [DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md) for complete Docker guide.

## 🚀 Quick Start

### Simple Pipeline
```python
from streamware import flow

# Basic data transformation pipeline
result = (
    flow("http://api.example.com/data")
    | "transform://jsonpath?query=$.items[*]"
    | "file://write?path=/tmp/output.json"
).run()
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
