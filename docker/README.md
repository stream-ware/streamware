# Streamware Docker Environment

Kompletne środowisko Docker do testowania Streamware ze wszystkimi zależnościami.

## 🚀 Quick Start

### 1. Zbuduj i uruchom

```bash
# Zbuduj obrazy
docker-compose build

# Uruchom wszystkie serwisy
docker-compose up -d

# Sprawdź status
docker-compose ps
```

### 2. Wejdź do kontenera

```bash
# Interaktywny shell
docker-compose exec streamware bash

# Teraz możesz używać streamware i sq!
sq get mock-api:8080/users --json
```

### 3. Zatrzymaj

```bash
docker-compose down
```

## 📦 Zawarte Serwisy

| Serwis | Port | Opis |
|--------|------|------|
| **streamware** | - | Główny kontener z Streamware |
| **mock-api** | 8080 | Mock REST API (Mockoon) |
| **rtsp-server** | 8554, 1935 | RTSP server dla video |
| **kafka** | 9092 | Apache Kafka |
| **zookeeper** | 2181 | Zookeeper dla Kafki |
| **postgres** | 5432 | PostgreSQL database |
| **redis** | 6379 | Redis cache |
| **rabbitmq** | 5672, 15672 | RabbitMQ + Management UI |
| **jupyter** | 8888 | Jupyter Lab |

## 🎯 Przykłady Użycia

### HTTP Requests

```bash
# Wejdź do kontenera
docker-compose exec streamware bash

# GET request
sq get mock-api:8080/users --json

# GET i zapisz
sq get mock-api:8080/products --json --save /data/products.json

# POST request
sq post mock-api:8080/users \
  --data '{"name":"New User","email":"new@example.com"}' \
  --json
```

### PostgreSQL

```bash
# Query bazy
sq postgres "SELECT * FROM users WHERE active=true" --json

# Export do CSV
sq postgres "SELECT * FROM products" --csv --save /data/products.csv

# Insert danych
echo '{"name":"Test Product","price":99.99}' | \
  streamware "postgres://insert?table=products" --data @-
```

### Kafka Streaming

```bash
# Produce message
echo '{"event":"test","data":"hello"}' | \
  streamware "kafka://produce?topic=events" --data @-

# Consume messages
streamware "kafka://consume?topic=events&group=test" --stream

# With sq
sq kafka events --produce --data '{"test":"data"}'
sq kafka events --consume --json --stream
```

### Video Processing

```bash
# Process RTSP stream
streamware "rtsp://rtsp-server:8554/stream" \
  --pipe "transcode://mp4?codec=h264" \
  --pipe "detect://faces" \
  --pipe "file://write?path=/data/output.mp4"
```

### File Operations

```bash
# JSON to CSV
sq file /data/products.json --json --csv --save /data/products.csv

# Base64 encoding
sq file /data/image.png --base64 --save /data/encoded.txt

# Base64 decoding
sq file /data/encoded.txt --base64 --decode --save /data/decoded.png
```

## 🔬 Python Examples

### W kontenerze Streamware

```bash
docker-compose exec streamware python
```

```python
from streamware import Pipeline, flow, quick

# Fluent API
result = (
    Pipeline()
    .http_get("http://mock-api:8080/users")
    .to_json()
    .filter(lambda x: x['active'])
    .to_csv()
    .save("/data/active_users.csv")
    .run()
)

# Quick shortcuts
quick("http://mock-api:8080/data").json().save("/data/data.json")

# Original DSL
result = (
    flow("http://mock-api:8080/products")
    | "transform://json"
    | "transform://csv"
    | "file://write?path=/data/products.csv"
).run()
```

### Jupyter Notebook

```bash
# Otwórz Jupyter Lab
open http://localhost:8888

# Lub z kontenera
docker-compose logs jupyter | grep "http://127.0.0.1"
```

W notebooku:

```python
from streamware import *

# Test connection
result = Pipeline().http_get("http://mock-api:8080/health").to_json().run()
print(result)

# Process data
users = (
    Pipeline()
    .http_get("http://mock-api:8080/users")
    .to_json()
    .filter(lambda u: u['age'] > 25)
    .run()
)
```

## 📊 Monitoring

### RabbitMQ Management

```bash
# Otwórz w przeglądarce
open http://localhost:15672

# Login: streamware / streamware
```

### PostgreSQL

```bash
# Connect z hosta
psql -h localhost -U streamware -d streamware

# Lub z kontenera
docker-compose exec postgres psql -U streamware -d streamware

# Przykładowe query
SELECT * FROM users WHERE active=true;
```

### Kafka

```bash
# List topics
docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Create topic
docker-compose exec kafka kafka-topics \
  --create --topic test \
  --bootstrap-server localhost:9092 \
  --partitions 1 --replication-factor 1

# Consume messages
docker-compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic events --from-beginning
```

## 🧪 Test Scripts

### 1. Basic Pipeline Test

```bash
# Run test script
docker-compose exec streamware bash /app/docker/test-basic.sh
```

### 2. ETL Pipeline Test

```bash
# Run ETL test
docker-compose exec streamware bash /app/docker/test-etl.sh
```

### 3. Video Processing Test

```bash
# Run video test
docker-compose exec streamware bash /app/docker/test-video.sh
```

### 4. Streaming Test

```bash
# Run streaming test
docker-compose exec streamware bash /app/docker/test-streaming.sh
```

## 🐛 Debugging

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f streamware
docker-compose logs -f kafka
docker-compose logs -f postgres
```

### Execute Commands

```bash
# Run command in streamware container
docker-compose exec streamware sq --help

# Run Python script
docker-compose exec streamware python /app/examples/basic_usage.py

# Run tests
docker-compose exec streamware pytest tests/ -v
```

### Network Debugging

```bash
# Check network
docker-compose exec streamware ping mock-api
docker-compose exec streamware curl http://mock-api:8080/health

# Test connections
docker-compose exec streamware nc -zv kafka 9092
docker-compose exec streamware nc -zv postgres 5432
```

## 📁 Data Persistence

Dane są przechowywane w voluminach:

```bash
# List volumes
docker volume ls | grep streamware

# Inspect volume
docker volume inspect streamware_postgres-data

# Backup volume
docker run --rm -v streamware_postgres-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/postgres-backup.tar.gz /data
```

## 🔄 Rebuild

```bash
# Rebuild specific service
docker-compose build streamware

# Rebuild without cache
docker-compose build --no-cache

# Restart service
docker-compose restart streamware
```

## 🧹 Cleanup

```bash
# Stop and remove containers
docker-compose down

# Remove volumes (deletes data!)
docker-compose down -v

# Remove images
docker-compose down --rmi all

# Complete cleanup
docker-compose down -v --rmi all --remove-orphans
```

## 🎓 Tutoriale

### Tutorial 1: Pierwszy Request

```bash
# 1. Uruchom środowisko
docker-compose up -d

# 2. Wejdź do kontenera
docker-compose exec streamware bash

# 3. Test connection
sq get mock-api:8080/health --json

# 4. Pobierz użytkowników
sq get mock-api:8080/users --json --save /data/users.json

# 5. Sprawdź wynik
cat /data/users.json
```

### Tutorial 2: ETL Pipeline

```bash
# W kontenerze streamware

# Extract
sq postgres "SELECT * FROM users WHERE active=true" \
  --json --save /data/active_users.json

# Transform
sq file /data/active_users.json --json --csv \
  --save /data/active_users.csv

# Load (do Kafki)
sq kafka user-exports --produce \
  --data @/data/active_users.json
```

### Tutorial 3: Real-time Streaming

Terminal 1 (Producer):
```bash
docker-compose exec streamware bash
# Produce messages
while true; do
  echo "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"value\":$RANDOM}" | \
    streamware "kafka://produce?topic=metrics" --data @-
  sleep 1
done
```

Terminal 2 (Consumer):
```bash
docker-compose exec streamware bash
# Consume and process
streamware "kafka://consume?topic=metrics&group=processor" \
  --pipe "transform://json" \
  --stream
```

## 📚 Więcej Informacji

- [Streamware Docs](../docs/)
- [Quick CLI Guide](../docs/QUICK_CLI.md)
- [DSL Examples](../docs/DSL_EXAMPLES.md)
- [Examples](../examples/)

## 🆘 Troubleshooting

### Problem: Cannot connect to services

```bash
# Sprawdź czy wszystkie serwisy działają
docker-compose ps

# Restart problematic service
docker-compose restart <service-name>

# Check logs
docker-compose logs <service-name>
```

### Problem: Port already in use

```bash
# Change ports in docker-compose.yml
# For example, change 8080:8080 to 8081:8080
```

### Problem: Out of memory

```bash
# Increase Docker memory limit in Docker Desktop
# Settings -> Resources -> Memory -> Increase limit
```

### Problem: No space left on device

```bash
# Clean up Docker
docker system prune -a --volumes

# Remove unused images
docker image prune -a
```

## 🎉 Gotowe!

Teraz masz pełne środowisko testowe dla Streamware!

```bash
# Start
docker-compose up -d

# Test
docker-compose exec streamware sq get mock-api:8080/users --json

# Happy streaming! 🚀
```
