# Data Pipeline Examples

ETL, data transformation, and stream processing.

## 📁 Examples

| File | Description |
|------|-------------|
| [api_to_database.py](api_to_database.py) | Fetch API → Transform → Save to DB |
| [csv_processor.py](csv_processor.py) | CSV transformation pipeline |
| [kafka_consumer.py](kafka_consumer.py) | Kafka stream processing |
| [etl_with_ai.py](etl_with_ai.py) | AI-powered data extraction |
| [file_watcher.py](file_watcher.py) | Watch files and process changes |

## 🚀 Quick Start

```bash
# API to JSON
sq get https://api.example.com/users --json

# Transform CSV
sq file data.csv | sq transform --csv --delimiter ";"

# Kafka consume
sq kafka consume --topic events --group my-app

# PostgreSQL query
sq postgres "SELECT * FROM users" --json

# File pipeline
sq file input.json | sq transform --jsonpath "$.items[*].name" > output.txt
```

## 🔧 Configuration

```bash
# PostgreSQL
export POSTGRES_URL=postgresql://user:pass@host/db

# Kafka
export KAFKA_BROKERS=localhost:9092

# RabbitMQ
export RABBITMQ_URL=amqp://user:pass@host:5672
```

## 📚 Related Documentation

- [DSL Examples](../../docs/v2/components/DSL_EXAMPLES.md)
- [Usage Guide](../../docs/v2/components/USAGE_GUIDE.md)
- [Quick CLI](../../docs/v2/components/QUICK_CLI.md)

## 🔗 Related Examples

- [LLM AI](../llm-ai/) - AI data extraction
- [Communication](../communication/) - Pipeline alerts

## 🔗 Source Code

- [streamware/components/transform.py](../../streamware/components/transform.py)
- [streamware/components/file.py](../../streamware/components/file.py)
- [streamware/components/kafka.py](../../streamware/components/kafka.py)
- [streamware/components/postgres.py](../../streamware/components/postgres.py)
