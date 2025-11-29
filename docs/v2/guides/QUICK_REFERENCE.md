# Streamware Quick Reference - Cheat Sheet

Szybkie komendy i wzorce dla najczęstszych zadań.

## 🚀 Quick CLI (`sq`) - Podstawy

```bash
# HTTP
sq get api.com/data --json --save data.json
sq post api.com/users --data '{"name":"Alice"}' --json

# Files
sq file input.json --json --csv --save output.csv
sq file image.png --base64 --save encoded.txt

# Kafka
sq kafka events --consume --json --stream
sq kafka events --produce --data '{"test":"data"}'

# PostgreSQL
sq postgres "SELECT * FROM users" --csv --save users.csv

# Email
sq email user@example.com --subject "Test" --body "Hello"

# Slack
sq slack channel --message "Deploy complete!" --token TOKEN
```

## 📦 Docker - Quick Start

```bash
# Start wszystko
docker-compose up -d

# Wejdź do kontenera
docker-compose exec streamware bash

# Test z Mock API
sq get mock-api:8080/users --json

# Usługi w tle
docker-compose -f docker-compose-extended.yml up -d
```

## 🔄 Przykłady Mieszane (Service Mixing)

### 1. Email → FTP
```bash
# Pobierz załączniki i wyślij na FTP
sq email imap.gmail.com \
  --user user@example.com \
  --password secret \
  --attachments \
  --save /tmp/attachments/

for file in /tmp/attachments/*; do
  curl -T "$file" ftp://ftp.example.com/ --user user:pass
done
```

### 2. API → PostgreSQL + Slack
```bash
# ETL pipeline z notyfikacją
sq get api.company.com/data --json --save /tmp/data.json

sq postgres "COPY table FROM '/tmp/data.json' CSV"

sq slack data-team \
  --message "Imported $(cat /tmp/data.json | jq length) records" \
  --token $SLACK_TOKEN
```

### 3. Kafka → Transform → Multiple Outputs
```bash
# Stream processing
streamware "kafka://consume?topic=events&group=processor" --stream | \
while read event; do
  # Save to PostgreSQL
  echo "$event" | sq postgres "INSERT INTO events VALUES (...)"
  
  # Upload to FTP
  echo "$event" > /tmp/event_$(date +%s).json
  curl -T /tmp/event_*.json ftp://backup.com/events/
  
  # Notify if critical
  if echo "$event" | jq -e '.severity == "critical"'; then
    sq slack alerts --message "Critical event!" --token $TOKEN
  fi
done
```

### 4. Email → SSH Deployment (Secure)
```bash
#!/bin/bash
# Protected deployment from email attachments

PASSWORD="your_secret_password"
PASSWORD_HASH=$(echo -n "$PASSWORD" | sha256sum | cut -d' ' -f1)

# Check email for deployment files
sq email deploy@company.com \
  --password secret \
  --subject "DEPLOY:" \
  --attachments \
  --save /tmp/deploy/

# Verify and deploy
for file in /tmp/deploy/*; do
  # Verify hash in filename or metadata
  if verify_hash "$file" "$PASSWORD_HASH"; then
    # Deploy via SSH
    scp -i ~/.ssh/deploy_key "$file" deploy@prod.com:/app/
    
    # Log
    sq postgres "INSERT INTO deployments (file, timestamp) 
      VALUES ('$(basename $file)', NOW())"
    
    # Notify
    sq slack deployments \
      --message "✓ Deployed $(basename $file)" \
      --token $SLACK_TOKEN
  fi
done
```

### 5. Multi-source Data Aggregation
```bash
# Combine HTTP + PostgreSQL + Kafka
sq get api.com/metrics --json > /tmp/api.json
sq postgres "SELECT * FROM metrics" --json > /tmp/db.json
timeout 5s streamware "kafka://consume?topic=metrics" > /tmp/kafka.json

# Merge
jq -s 'add' /tmp/{api,db,kafka}.json > /tmp/combined.json

# Store and notify
sq postgres "INSERT INTO aggregated SELECT * FROM json..."
sq email report@company.com \
  --subject "Daily Metrics" \
  --attach /tmp/combined.json
```

## 🎯 Usługi w Tle (Background Services)

### Start Service (Docker)
```bash
# Email → FTP service
docker run -d \
  --name email-ftp \
  -e EMAIL_USER=user@example.com \
  -e EMAIL_PASSWORD=secret \
  -e FTP_HOST=ftp.example.com \
  -v $(pwd)/logs:/logs \
  streamware bash /app/services/email-to-ftp.sh
```

### Start Service (Shell script as daemon)
```bash
# Create service
cat > /tmp/my-service.sh << 'EOF'
#!/bin/bash
while true; do
  sq get api.com/health || sq slack alerts --message "API down!"
  sleep 60
done
EOF

# Run in background
nohup bash /tmp/my-service.sh > /logs/service.log 2>&1 &
echo $! > /tmp/service.pid

# Stop later
kill $(cat /tmp/service.pid)
```

### Start Service (Systemd)
```bash
# Create service file
sudo tee /etc/systemd/system/my-monitor.service << EOF
[Unit]
Description=My Monitoring Service

[Service]
ExecStart=/app/monitor.sh
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Start
sudo systemctl daemon-reload
sudo systemctl start my-monitor
sudo systemctl enable my-monitor
```

## 🔐 Secure Patterns

### Password Protected Action
```bash
#!/bin/bash
read -sp "Password: " password
hash=$(echo -n "$password" | sha256sum | cut -d' ' -f1)

if [[ "$hash" == "expected_hash_here" ]]; then
  # Perform secure action
  scp -i ~/.ssh/key sensitive_data.json deploy@prod.com:/secure/
else
  echo "Access denied"
  exit 1
fi
```

### Token-based Authentication
```bash
# .env file
TOKEN="your_secret_token_here"

# Use in scripts
if [[ "$INPUT_TOKEN" == "$TOKEN" ]]; then
  sq postgres "SELECT * FROM sensitive_data"
else
  echo "Unauthorized"
fi
```

## 📊 Monitoring Patterns

### Health Check Loop
```bash
while true; do
  status=$(sq get api.com/health --json | jq -r '.status')
  
  if [[ "$status" != "ok" ]]; then
    sq slack alerts --message "🚨 Health check failed!"
    sq email oncall@company.com --subject "ALERT" --body "Check system"
  fi
  
  sleep 60
done
```

### Log Aggregation
```bash
# Collect logs from multiple sources
sq postgres "SELECT * FROM app_logs WHERE date = CURRENT_DATE" > /tmp/db_logs.txt
ssh server1.com "tail -100 /var/log/app.log" > /tmp/server1_logs.txt
ssh server2.com "tail -100 /var/log/app.log" > /tmp/server2_logs.txt

# Combine and analyze
cat /tmp/*_logs.txt | grep ERROR > /tmp/errors.txt

# Report
sq email dev-team@company.com \
  --subject "Daily Error Report" \
  --attach /tmp/errors.txt
```

## 🔄 Pipeline Patterns

### Sequential Pipeline
```bash
# Step by step
sq get api.com/data --json --save /tmp/1.json
sq file /tmp/1.json --json --transform --save /tmp/2.json
sq postgres "COPY table FROM '/tmp/2.json'"
sq slack data --message "Pipeline complete!"
```

### Parallel Pipeline
```bash
# Run in parallel
sq get api1.com/data --json --save /tmp/source1.json &
sq get api2.com/data --json --save /tmp/source2.json &
sq get api3.com/data --json --save /tmp/source3.json &
wait

# Merge
jq -s 'add' /tmp/source*.json > /tmp/merged.json
```

### Conditional Pipeline
```bash
data=$(sq get api.com/data --json)
count=$(echo "$data" | jq length)

if [[ $count -gt 100 ]]; then
  # High volume - use Kafka
  echo "$data" | sq kafka high-volume --produce --data @-
else
  # Low volume - direct to DB
  echo "$data" | sq postgres "INSERT INTO data VALUES (...)"
fi
```

## 📁 File Operations

### Batch Processing
```bash
for file in /data/incoming/*.json; do
  # Validate
  if sq file "$file" --json --validate; then
    # Upload to multiple destinations
    curl -T "$file" ftp://backup.com/
    scp "$file" remote.com:/data/
    sq postgres "COPY table FROM '$file'"
    
    mv "$file" /data/processed/
  fi
done
```

### Archive and Compress
```bash
# Create backup
sq postgres "SELECT * FROM important_data" --json --save backup.json
tar czf backup_$(date +%Y%m%d).tar.gz backup.json

# Upload
curl -T backup_*.tar.gz ftp://backup.com/archives/
scp backup_*.tar.gz backup@remote.com:/backups/
```

## 🎨 Complex Examples

### CI/CD Pipeline
```bash
#!/bin/bash
# Automated deployment

# Fetch latest code
git pull origin main

# Run tests
if make test; then
  # Build
  docker build -t app:latest .
  
  # Deploy
  ssh deploy@prod.com << 'REMOTE'
    docker stop app
    docker rm app
    docker run -d --name app app:latest
  REMOTE
  
  # Notify success
  sq slack deployments --message "✓ Deployed successfully"
  sq postgres "INSERT INTO deployments (status, timestamp) 
    VALUES ('success', NOW())"
else
  # Notify failure
  sq slack alerts --message "❌ Tests failed"
  sq email dev@company.com --subject "Deployment Failed"
fi
```

### Data Sync Service
```bash
#!/bin/bash
# Continuous data synchronization

while true; do
  # Source: API
  sq get api.company.com/updates --json --save /tmp/updates.json
  
  # Destinations: Multiple
  # 1. Primary database
  sq postgres "COPY updates FROM '/tmp/updates.json'"
  
  # 2. Backup FTP
  curl -T /tmp/updates.json ftp://backup.com/daily/
  
  # 3. Remote SSH
  scp /tmp/updates.json sync@remote.com:/data/
  
  # 4. Message queue
  sq kafka updates --produce --data @/tmp/updates.json
  
  # 5. Cache
  redis-cli SET "latest_update" "$(cat /tmp/updates.json)"
  
  sleep 300  # Every 5 minutes
done
```

## 🛠️ Debugging

### Verbose Mode
```bash
# Add --debug to any sq command
sq get api.com/data --json --debug

# Or use streamware directly
streamware "http://api.com/data" \
  --pipe "transform://json" \
  --debug
```

### Test Connections
```bash
# Test HTTP
curl -v http://api.com/health

# Test FTP
curl -v ftp://ftp.com/ --user user:pass

# Test SSH
ssh -v user@remote.com

# Test PostgreSQL
psql -h localhost -U user -d dbname -c "SELECT 1"

# Test Kafka
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092
```

## 📚 Resources

- **[Docker Quick Start](DOCKER_QUICKSTART.md)** - Docker setup
- **[Services README](docker/SERVICES_README.md)** - Background services
- **[Quick CLI Guide](docs/QUICK_CLI.md)** - Full CLI docs
- **[DSL Examples](docs/DSL_EXAMPLES.md)** - Python DSL
- **[Advanced Examples](docker/examples-advanced.sh)** - 10 real examples

---

**Tip:** Zapisz najczęściej używane komendy jako aliasy w `~/.bashrc`!

```bash
alias sq-health='sq get mock-api:8080/health --json'
alias sq-users='sq get mock-api:8080/users --json'
alias sq-db='sq postgres'
```
