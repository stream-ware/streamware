# SSH Component - Quick Guide

Komponent SSH dla Streamware - bezpieczne operacje na zdalnych serwerach.

## 🚀 Quick Start

### Instalacja

SSH component działa out-of-the-box! Opcjonalnie możesz zainstalować `paramiko` dla lepszej wydajności:

```bash
pip install paramiko
```

Bez `paramiko` używany jest systemowy `ssh`/`scp`.

## 📝 Podstawowe Użycie

### 1. Upload File (Quick Style)

```bash
# Najprostszy sposób
sq ssh prod.company.com --upload myapp.tar.gz --remote /app/

# Z kluczem SSH
sq ssh prod.company.com \
  --upload myapp.tar.gz \
  --user deploy \
  --key ~/.ssh/deploy_key \
  --remote /app/myapp.tar.gz

# Z portem
sq ssh prod.company.com \
  --upload file.txt \
  --user deploy \
  --port 2222 \
  --remote /data/file.txt
```

### 2. Download File

```bash
# Download
sq ssh prod.company.com \
  --download /data/backup.tar.gz \
  --local /tmp/backup.tar.gz \
  --user backup

# Z kluczem
sq ssh prod.company.com \
  --download /app/logs.txt \
  --local ./logs.txt \
  --key ~/.ssh/id_rsa
```

### 3. Execute Command

```bash
# Proste polecenie
sq ssh prod.company.com --exec "df -h" --user admin

# Multiple commands
sq ssh prod.company.com \
  --exec "systemctl status myapp && journalctl -u myapp -n 20" \
  --user admin

# With output capture
result=$(sq ssh prod.company.com --exec "uptime" --user monitor)
echo "Server uptime: $result"
```

### 4. Deploy Application

```bash
# Deploy z auto-restart
sq ssh prod.company.com \
  --deploy myapp.tar.gz \
  --user deploy \
  --remote /app/ \
  --restart myapp

# Deploy multiple files
for file in *.py; do
  sq ssh prod.company.com \
    --deploy "$file" \
    --remote /app/src/ \
    --user deploy
done
```

## 🎯 Python API

### Flow Style

```python
from streamware import flow

# Upload
result = flow("ssh://upload?host=prod.com&user=deploy&remote=/app/file.txt").run("local_file.txt")

# Download
data = flow("ssh://download?host=prod.com&user=deploy&remote=/data/file.txt&local=/tmp/file.txt").run()

# Execute
result = flow("ssh://exec?host=prod.com&user=admin&command=systemctl restart app").run()

# Deploy
result = flow("ssh://deploy?host=prod.com&user=deploy&path=/app/&restart=myapp").run("app.tar.gz")
```

### Helper Functions

```python
from streamware.components.ssh import ssh_upload, ssh_download, ssh_exec, ssh_deploy

# Upload
result = ssh_upload("prod.com", "local_file.txt", "/remote/path/file.txt", user="deploy")

# Download
data = ssh_download("prod.com", "/remote/file.txt", "/local/file.txt", user="deploy")

# Execute
result = ssh_exec("prod.com", "systemctl status app", user="admin")

# Deploy
result = ssh_deploy("prod.com", "app.tar.gz", "/app/", user="deploy", restart="myapp")
```

## 💡 Real-world Examples

### Example 1: Email Attachments → SSH Deployment

```bash
#!/bin/bash
# Service: email-to-ssh-deploy.sh

while true; do
    # Check for deployment emails
    sq email imap.company.com \
        --user deploy@company.com \
        --password "$EMAIL_PASSWORD" \
        --subject "DEPLOY:" \
        --attachments \
        --save /tmp/deployments/
    
    # Deploy each attachment
    for file in /tmp/deployments/*; do
        if [ -f "$file" ]; then
            # Upload to server
            sq ssh prod.company.com \
                --deploy "$file" \
                --user deploy \
                --key ~/.ssh/deploy_key \
                --remote /app/ \
                --restart myapp
            
            # Log
            sq postgres "INSERT INTO deployments (file, timestamp) 
                VALUES ('$(basename $file)', NOW())"
            
            # Notify
            sq slack deployments \
                --message "✓ Deployed $(basename $file)"
            
            rm "$file"
        fi
    done
    
    sleep 60
done
```

### Example 2: Multi-server Backup

```bash
# Backup to multiple servers
servers=("backup1.com" "backup2.com" "backup3.com")

# Create backup
sq postgres "SELECT * FROM critical_data" --csv > backup.csv
tar czf backup_$(date +%Y%m%d).tar.gz backup.csv

# Upload to all servers in parallel
for server in "${servers[@]}"; do
    sq ssh "$server" \
        --upload backup_*.tar.gz \
        --user backup \
        --remote /backups/daily/ &
done

wait
echo "✓ Backup uploaded to ${#servers[@]} servers"

# Notify
sq slack backups --message "✓ Backup completed on all servers"
```

### Example 3: Secure Deployment with Password

```bash
#!/bin/bash
# deploy-secure.sh

# Password check
read -sp "Deployment password: " password
echo

hash=$(echo -n "$password" | sha256sum | cut -d' ' -f1)
expected="5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"

if [[ "$hash" != "$expected" ]]; then
    echo "✗ Access denied"
    sq postgres "INSERT INTO auth_failures (timestamp, user) VALUES (NOW(), '$USER')"
    exit 1
fi

echo "✓ Authenticated"

# Deploy
sq ssh prod.company.com \
    --deploy "$1" \
    --user deploy \
    --key ~/.ssh/deploy_key \
    --remote /app/ \
    --restart myapp

# Log success
sq postgres "INSERT INTO deployments (file, user, timestamp, status) 
    VALUES ('$1', '$USER', NOW(), 'success')"

# Notify
sq slack deployments \
    --message "✓ $USER deployed $1 to production"
```

### Example 4: Monitoring Service

```bash
#!/bin/bash
# ssh-monitor.sh - Background monitoring

while true; do
    # Check disk space
    disk_usage=$(sq ssh prod.company.com \
        --exec "df -h / | tail -1 | awk '{print \$5}'" \
        --user monitor)
    
    if [[ "${disk_usage%?}" -gt 90 ]]; then
        sq slack alerts \
            --message "🚨 Disk usage on prod.company.com: $disk_usage"
    fi
    
    # Check service
    status=$(sq ssh prod.company.com \
        --exec "systemctl is-active myapp" \
        --user monitor)
    
    if [[ "$status" != "active" ]]; then
        sq slack alerts \
            --message "🚨 Service myapp is down!"
        
        # Auto-restart
        sq ssh prod.company.com \
            --exec "systemctl restart myapp" \
            --user admin
        
        sq postgres "INSERT INTO incidents (type, action, timestamp) 
            VALUES ('service_down', 'auto_restarted', NOW())"
    fi
    
    sleep 300  # Check every 5 minutes
done
```

### Example 5: CI/CD Pipeline

```bash
#!/bin/bash
# cicd-pipeline.sh

set -e

echo "Starting deployment pipeline..."

# 1. Build
docker build -t myapp:${GIT_COMMIT} .
docker save myapp:${GIT_COMMIT} | gzip > myapp.tar.gz

# 2. Upload to staging
sq ssh staging.company.com \
    --upload myapp.tar.gz \
    --user deploy \
    --remote /tmp/

# 3. Deploy on staging
sq ssh staging.company.com \
    --exec "cd /app && docker load < /tmp/myapp.tar.gz && docker-compose up -d" \
    --user deploy

# 4. Run health check
sleep 10
if sq get https://staging.company.com/health --json | jq -e '.status == "ok"'; then
    echo "✓ Staging tests passed"
    
    # 5. Deploy to production servers
    prod_servers=("prod1.com" "prod2.com" "prod3.com")
    
    for server in "${prod_servers[@]}"; do
        echo "Deploying to $server..."
        
        sq ssh "$server" \
            --deploy myapp.tar.gz \
            --user deploy \
            --remote /tmp/ &&
        
        sq ssh "$server" \
            --exec "cd /app && docker load < /tmp/myapp.tar.gz && docker-compose up -d" \
            --user deploy
    done
    
    # 6. Log and notify
    sq postgres "INSERT INTO deployments (version, servers, timestamp, status) 
        VALUES ('${GIT_COMMIT}', '${prod_servers[*]}', NOW(), 'success')"
    
    sq slack deployments \
        --message "✓ Deployed ${GIT_COMMIT} to production (${#prod_servers[@]} servers)"
    
    echo "✓ Deployment complete!"
else
    echo "✗ Staging tests failed"
    sq slack alerts --message "🚨 Deployment failed - staging tests"
    exit 1
fi
```

## 🔐 Security Best Practices

### 1. Use SSH Keys (Not Passwords)

```bash
# Generate key
ssh-keygen -t ed25519 -C "deploy@company.com" -f ~/.ssh/deploy_key

# Copy to server
ssh-copy-id -i ~/.ssh/deploy_key.pub deploy@prod.company.com

# Use in commands
sq ssh prod.company.com --upload file.txt --key ~/.ssh/deploy_key
```

### 2. Limit User Permissions

```bash
# On server: /etc/ssh/sshd_config
Match User deploy
    ForceCommand internal-sftp
    ChrootDirectory /app
    PermitTunnel no
    AllowTcpForwarding no
```

### 3. Use Jump Hosts

```bash
# SSH through bastion
sq ssh prod.company.com \
    --upload file.txt \
    --proxy bastion.company.com \
    --user deploy
```

### 4. Log All Actions

```bash
# Wrapper script
ssh_deploy_logged() {
    local file=$1
    local server=$2
    
    sq ssh "$server" --deploy "$file" --user deploy
    
    sq postgres "INSERT INTO ssh_actions (action, file, server, user, timestamp) 
        VALUES ('deploy', '$file', '$server', '$USER', NOW())"
}
```

## 🛠️ Configuration

### Environment Variables

```bash
# Default SSH settings
export SSH_USER=deploy
export SSH_KEY=~/.ssh/deploy_key
export SSH_PORT=22

# Now you can omit these in commands
sq ssh prod.company.com --upload file.txt
```

### Configuration File

```bash
# ~/.streamware/ssh.conf
[defaults]
user = deploy
key = ~/.ssh/deploy_key
port = 22
strict_host_key = false

[prod]
host = prod.company.com
user = deploy
key = ~/.ssh/prod_key

[staging]
host = staging.company.com
user = deploy
key = ~/.ssh/staging_key
```

## 📊 URI Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `host` | Remote hostname | `prod.company.com` |
| `user` | SSH user | `deploy` |
| `key` | SSH key path | `~/.ssh/id_rsa` |
| `password` | SSH password (not recommended) | `secret` |
| `port` | SSH port | `22` |
| `remote` | Remote path | `/app/file.txt` |
| `local` | Local path | `/tmp/file.txt` |
| `command` | Command to execute | `systemctl restart app` |
| `restart` | Service to restart | `myapp` |
| `permissions` | File permissions | `755` |
| `backup` | Backup before deploy | `true` |
| `strict` | Strict host key checking | `false` |
| `timeout` | Operation timeout | `30` |

## 🐛 Troubleshooting

### Permission Denied

```bash
# Check key permissions
chmod 600 ~/.ssh/deploy_key

# Test connection
ssh -i ~/.ssh/deploy_key deploy@prod.company.com

# Debug
sq ssh prod.company.com --upload file.txt --debug
```

### Connection Timeout

```bash
# Increase timeout
sq ssh prod.company.com \
    --upload large_file.tar.gz \
    --timeout 300

# Check network
ping prod.company.com
telnet prod.company.com 22
```

### Host Key Verification Failed

```bash
# Disable strict checking (not recommended for production)
sq ssh prod.company.com \
    --upload file.txt \
    --strict false

# Or add to known_hosts
ssh-keyscan prod.company.com >> ~/.ssh/known_hosts
```

## 📚 More Examples

See:
- `examples/ssh_examples.py` - 10 Python examples
- `docker/services/email-to-ssh.sh` - Production service
- `docker/examples-advanced.sh` - Advanced patterns

---

**Quick Commands:**

```bash
# Upload
sq ssh HOST --upload FILE --remote PATH

# Download
sq ssh HOST --download REMOTE --local LOCAL

# Execute
sq ssh HOST --exec COMMAND

# Deploy
sq ssh HOST --deploy FILE --remote PATH --restart SERVICE
```

Happy SSH operations! 🚀
