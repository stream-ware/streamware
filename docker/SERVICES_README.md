# Streamware Services - Running as Daemons

Przewodnik po uruchamianiu usług Streamware w tle jako trwałe serwisy.

## 🚀 Quick Start - Uruchom Usługi

### Option 1: Docker Compose (Rekomendowane)

```bash
# Uruchom wszystkie usługi
docker-compose -f docker-compose-extended.yml up -d

# Sprawdź status
docker-compose -f docker-compose-extended.yml ps

# Logi usług
docker-compose -f docker-compose-extended.yml logs -f email-ftp-service
```

### Option 2: Systemd (Na hoście)

```bash
# Skopiuj service files
sudo cp docker/services/systemd/*.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Uruchom usługę
sudo systemctl start streamware-email-ftp
sudo systemctl enable streamware-email-ftp

# Sprawdź status
sudo systemctl status streamware-email-ftp

# Logi
sudo journalctl -u streamware-email-ftp -f
```

## 📦 Dostępne Usługi

### 1. Email → FTP Service

**Automatycznie pobiera załączniki z emaila i wysyła na FTP.**

```bash
# Docker
docker-compose -f docker-compose-extended.yml up -d email-ftp-service

# Lub bezpośrednio
docker run -d \
  --name email-ftp \
  -e EMAIL_HOST=imap.gmail.com \
  -e EMAIL_USER=user@example.com \
  -e EMAIL_PASSWORD=secret \
  -e FTP_HOST=ftp.example.com \
  -e FTP_USER=ftpuser \
  -e FTP_PASSWORD=ftppass \
  -v $(pwd)/logs:/logs \
  streamware bash /app/services/email-to-ftp.sh
```

**Konfiguracja (`.env` file):**
```bash
EMAIL_HOST=imap.gmail.com
EMAIL_USER=notifications@company.com
EMAIL_PASSWORD=your_password_here
FTP_HOST=ftp.company.com
FTP_USER=upload_user
FTP_PASSWORD=upload_pass
CHECK_INTERVAL=60
```

### 2. Email → SSH Service

**Bezpieczne wysyłanie załączników przez SSH/SFTP.**

```bash
# Docker
docker-compose -f docker-compose-extended.yml up -d email-ssh-service

# Konfiguracja
EMAIL_HOST=imap.gmail.com
EMAIL_USER=secure@company.com
EMAIL_PASSWORD=secret
SSH_HOST=remote.company.com
SSH_USER=deploy
SSH_KEY=/root/.ssh/id_rsa
SSH_PORT=22
REMOTE_PATH=/data/uploads
```

### 3. Kafka → PostgreSQL Service

**Stream Kafka messages do PostgreSQL.**

```bash
# Docker
docker-compose -f docker-compose-extended.yml up -d kafka-postgres-service

# Konfiguracja
KAFKA_TOPIC=events
KAFKA_GROUP=db-writer
POSTGRES_TABLE=events
```

## 🎯 Przykłady Użycia - Quick Style

### Przykład 1: Email Attachments → FTP

```bash
# Quick command (one-time)
sq email imap.gmail.com \
  --user user@example.com \
  --password secret \
  --attachments \
  --foreach "curl -T {} ftp://ftp.example.com/ --user ftpuser:ftppass"
```

### Przykład 2: Email Attachments → SSH

```bash
# Quick command (one-time)
sq email imap.gmail.com \
  --user user@example.com \
  --password secret \
  --attachments \
  --foreach "scp -i ~/.ssh/key {} user@remote.com:/data/"
```

### Przykład 3: API → FTP + SSH + Database

```bash
# Pobierz dane
sq get api.company.com/export --json --save /tmp/data.json

# Upload do FTP
curl -T /tmp/data.json ftp://backup.com/ --user user:pass

# Upload przez SSH
scp -i ~/.ssh/key /tmp/data.json deploy@prod.com:/backups/

# Zapisz w bazie
sq postgres "INSERT INTO backups (filename, timestamp) 
  VALUES ('data.json', NOW())"
```

### Przykład 4: Secure Deployment (z hasłem)

```bash
#!/bin/bash
# deploy.sh - Protected deployment

# Funkcja autentykacji
authenticate() {
    local password=$1
    local hash=$(echo "$password" | sha256sum)
    
    if [[ "$hash" == "$(cat /secrets/deploy.hash)" ]]; then
        return 0
    fi
    return 1
}

# Użycie
read -sp "Password: " password
echo

if authenticate "$password"; then
    echo "✓ Authenticated"
    
    # Deploy file via SSH
    scp -i /secrets/deploy_key "$1" deploy@prod.com:/app/
    
    # Log deployment
    sq postgres "INSERT INTO deployments 
      (file, user, timestamp) 
      VALUES ('$1', '$USER', NOW())"
    
    # Notify
    sq slack deployments \
      --message "✓ Deployed $1 by $USER" \
      --token "$SLACK_TOKEN"
else
    echo "✗ Authentication failed"
    exit 1
fi
```

**Uruchom:**
```bash
chmod +x deploy.sh
./deploy.sh myapp.tar.gz
```

### Przykład 5: Monitoring Service (działa w tle)

```bash
#!/bin/bash
# monitor.sh - Background monitoring service

# Uruchom jako daemon
nohup bash << 'EOF' > /logs/monitor.log 2>&1 &

while true; do
    # Check API
    status=$(sq get api.company.com/health --json | jq -r '.status')
    
    if [[ "$status" != "healthy" ]]; then
        # Alert via multiple channels
        sq slack alerts --message "🚨 API down!" --token "$SLACK_TOKEN"
        sq email oncall@company.com --subject "ALERT: API Down" --body "Immediate action required"
        sq postgres "INSERT INTO incidents (type, severity) VALUES ('api_down', 'critical')"
    fi
    
    sleep 60
done
EOF

echo "Monitor started in background (PID: $!)"
```

### Przykład 6: File Watcher Service

```bash
#!/bin/bash
# watch-and-distribute.sh

# Background service
nohup bash << 'EOF' > /logs/file-watcher.log 2>&1 &

while inotifywait -e create /data/incoming/; do
    for file in /data/incoming/*.json; do
        # Validate
        if sq file "$file" --json --validate; then
            
            # Distribute to multiple destinations
            # FTP
            curl -T "$file" ftp://backup.com/ --user user:pass
            
            # SSH
            scp -i ~/.ssh/key "$file" deploy@prod.com:/data/
            
            # Database
            sq postgres "COPY data_table FROM '$file' CSV"
            
            # S3
            aws s3 cp "$file" s3://bucket/data/
            
            # Move to processed
            mv "$file" /data/processed/
        fi
    done
done
EOF

echo "File watcher started"
```

## 🔐 Secure Authentication Example

### Protected Service with Password

```bash
#!/bin/bash
# secure-service.sh

PASSWORD_HASH="5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"  # "password" hashed

authenticate() {
    local input_hash=$(echo -n "$1" | sha256sum | cut -d' ' -f1)
    [[ "$input_hash" == "$PASSWORD_HASH" ]]
}

# API endpoint
while true; do
    read -r request
    
    password=$(echo "$request" | jq -r '.password')
    action=$(echo "$request" | jq -r '.action')
    data=$(echo "$request" | jq -r '.data')
    
    if authenticate "$password"; then
        case "$action" in
            "deploy")
                scp -i ~/.ssh/deploy "$data" prod.com:/app/
                echo '{"status":"deployed"}'
                ;;
            "backup")
                curl -T "$data" ftp://backup.com/
                echo '{"status":"backed_up"}'
                ;;
            *)
                echo '{"error":"unknown_action"}'
                ;;
        esac
        
        # Log access
        sq postgres "INSERT INTO access_log (action, timestamp) 
          VALUES ('$action', NOW())"
    else
        echo '{"error":"unauthorized"}'
        
        # Log failed attempt
        sq postgres "INSERT INTO auth_failures (timestamp) VALUES (NOW())"
    fi
done
```

**Użycie:**
```bash
# Start service
nohup ./secure-service.sh > /logs/secure-service.log 2>&1 &

# Call service
echo '{"password":"password","action":"deploy","data":"app.tar.gz"}' | \
  nc localhost 9999
```

## 🛠️ Zarządzanie Usługami

### Start/Stop Services

```bash
# Docker Compose
docker-compose -f docker-compose-extended.yml start email-ftp-service
docker-compose -f docker-compose-extended.yml stop email-ftp-service
docker-compose -f docker-compose-extended.yml restart email-ftp-service

# Systemd
sudo systemctl start streamware-email-ftp
sudo systemctl stop streamware-email-ftp
sudo systemctl restart streamware-email-ftp
```

### View Logs

```bash
# Docker
docker-compose -f docker-compose-extended.yml logs -f email-ftp-service

# Systemd
sudo journalctl -u streamware-email-ftp -f

# File logs
tail -f /logs/streamware-email-ftp.log
```

### Check Status

```bash
# Docker
docker-compose -f docker-compose-extended.yml ps

# Systemd
sudo systemctl status streamware-*

# Process
ps aux | grep streamware
```

## 📊 Monitorowanie

### Health Check Script

```bash
#!/bin/bash
# health-check.sh

services=("email-ftp" "email-ssh" "kafka-postgres")

for service in "${services[@]}"; do
    if docker ps | grep -q "streamware-$service"; then
        echo "✓ $service: Running"
    else
        echo "✗ $service: Stopped"
        # Alert
        sq slack ops \
          --message "Service $service is down!" \
          --token "$SLACK_TOKEN"
    fi
done
```

## 🔄 Auto-restart on Failure

### Systemd (automatic)
```bash
# Już skonfigurowane w .service files:
# Restart=always
# RestartSec=10
```

### Docker Compose (automatic)
```yaml
# Już skonfigurowane:
restart: unless-stopped
```

### Manual restart script
```bash
#!/bin/bash
# auto-restart.sh

while true; do
    if ! docker ps | grep -q streamware-email-ftp; then
        echo "Restarting email-ftp service..."
        docker-compose -f docker-compose-extended.yml up -d email-ftp-service
    fi
    sleep 30
done
```

## 📚 Więcej Przykładów

Zobacz:
- `docker/examples-advanced.sh` - 10 zaawansowanych przykładów
- `docker/test-basic.sh` - Podstawowe testy
- `docker/test-streaming.sh` - Testy streamingu

## 🆘 Troubleshooting

### Service nie startuje

```bash
# Check logs
docker logs streamware-email-ftp

# Check configuration
docker exec streamware-email-ftp env

# Test manually
docker exec -it streamware-email-ftp bash
bash /app/services/email-to-ftp.sh
```

### Authentication issues

```bash
# Test SSH connection
ssh -i ~/.ssh/key user@host

# Test FTP connection
curl ftp://host/ --user user:pass

# Test credentials
echo "password" | sha256sum
```

---

**Happy streaming! 🚀**

Wszystkie usługi działają w tle, są trwałe i restartują się automatycznie!
