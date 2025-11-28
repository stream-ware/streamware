#!/bin/bash
# Advanced Streamware Examples with Service Mixing
# Demonstrates complex real-world scenarios

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() {
    echo -e "${BLUE}→ $1${NC}"
}

success() {
    echo -e "${GREEN}✓ $1${NC}"
}

example() {
    echo -e "${YELLOW}$1${NC}"
}

echo "=========================================="
echo "ADVANCED STREAMWARE EXAMPLES"
echo "Service Mixing & Real-world Scenarios"
echo "=========================================="
echo ""

# Example 1: Email → PostgreSQL → Slack
echo "=== Example 1: Email Notifications Pipeline ==="
info "Email → PostgreSQL → Slack notification"
echo ""
example "# Monitor emails and log to database, then notify Slack"
cat << 'EOF'
# Read emails
sq email imap.gmail.com \
  --user notifications@company.com \
  --password "${EMAIL_PASSWORD}" \
  --unread \
  --json --save /tmp/new_emails.json

# Store in database
sq postgres "INSERT INTO email_log (sender, subject, received_at) 
  SELECT sender, subject, NOW() FROM json_populate_recordset(null::email_log, 
  (SELECT json_agg(t) FROM json_each('/tmp/new_emails.json') t))" \
  --json

# Notify Slack
sq slack alerts \
  --message "Received $(cat /tmp/new_emails.json | jq length) new emails" \
  --token "${SLACK_TOKEN}"
EOF
success "Email → DB → Slack pipeline ready"
echo ""

# Example 2: HTTP API → Transform → Kafka → PostgreSQL
echo "=== Example 2: API Data ETL Pipeline ==="
info "HTTP API → Transform → Kafka → PostgreSQL"
echo ""
example "# Full ETL pipeline"
cat << 'EOF'
# Fetch from API
sq get api.example.com/transactions --json --save /tmp/transactions.json

# Transform data
sq file /tmp/transactions.json \
  --json \
  --transform "SELECT id, amount, status WHERE amount > 1000" \
  --save /tmp/large_transactions.json

# Publish to Kafka (for streaming consumers)
sq kafka large-transactions --produce \
  --data @/tmp/large_transactions.json

# Also save to PostgreSQL (for reporting)
streamware "file://read?path=/tmp/large_transactions.json" \
  --pipe "transform://json" \
  --pipe "postgres://insert?table=large_transactions"
EOF
success "ETL pipeline with dual output"
echo ""

# Example 3: File Watcher → Process → Multiple Destinations
echo "=== Example 3: File Monitoring with Multiple Outputs ==="
info "Watch folder → Process → FTP + SSH + Database"
echo ""
example "# Monitor and distribute files"
cat << 'EOF'
#!/bin/bash
# Service: File distributor
while inotifywait -e create /data/incoming/; do
  for file in /data/incoming/*.json; do
    filename=$(basename "$file")
    
    # Parse and validate
    sq file "$file" --json --validate --save "/tmp/validated_${filename}"
    
    # Upload to FTP
    curl -T "/tmp/validated_${filename}" \
      "ftp://backup.company.com/archives/" \
      --user "${FTP_USER}:${FTP_PASS}"
    
    # Copy via SSH to production
    scp -i ~/.ssh/deploy_key "/tmp/validated_${filename}" \
      deploy@prod.company.com:/data/processed/
    
    # Log to database
    sq postgres "INSERT INTO file_log (filename, processed_at) 
      VALUES ('${filename}', NOW())"
    
    # Move to processed
    mv "$file" /data/processed/
  done
done
EOF
success "Multi-destination file distributor"
echo ""

# Example 4: PostgreSQL → Transform → Email Report
echo "=== Example 4: Automated Daily Reports ==="
info "PostgreSQL query → Transform → Email as PDF"
echo ""
example "# Daily report generator"
cat << 'EOF'
# Query database
sq postgres "
  SELECT 
    DATE(created_at) as date,
    COUNT(*) as orders,
    SUM(amount) as revenue
  FROM orders
  WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
  GROUP BY DATE(created_at)
  ORDER BY date DESC
" --csv --save /tmp/weekly_report.csv

# Convert to formatted HTML
sq file /tmp/weekly_report.csv \
  --csv \
  --template report_template.html \
  --save /tmp/report.html

# Send via email
sq email manager@company.com \
  --subject "Weekly Sales Report - $(date +%Y-%m-%d)" \
  --html /tmp/report.html \
  --attach /tmp/weekly_report.csv
EOF
success "Automated reporting pipeline"
echo ""

# Example 5: Kafka Stream → Real-time Processing → Multiple Outputs
echo "=== Example 5: Real-time Event Processing ==="
info "Kafka stream → Filter → Route to multiple destinations"
echo ""
example "# Real-time event router"
cat << 'EOF'
# Consume and route events
streamware "kafka://consume?topic=events&group=router" --stream | \
while read event; do
  event_type=$(echo "$event" | jq -r '.type')
  
  case $event_type in
    "critical")
      # Send to Slack immediately
      echo "$event" | sq slack incidents \
        --message "Critical event: $(echo $event | jq -r '.message')" \
        --token "${SLACK_TOKEN}"
      
      # Log to high-priority table
      echo "$event" | sq postgres "INSERT INTO critical_events VALUES (...)"
      ;;
    
    "user_action")
      # Send to analytics
      echo "$event" | sq kafka user-analytics --produce --data @-
      ;;
    
    "system")
      # Store in time-series database
      echo "$event" | sq postgres "INSERT INTO metrics VALUES (...)"
      ;;
  esac
done
EOF
success "Real-time event routing"
echo ""

# Example 6: Secure File Transfer with Authentication
echo "=== Example 6: Protected Deployment Service ==="
info "Secure file deployment with password protection and logging"
echo ""
example "# Protected deployment service"
cat << 'EOF'
#!/bin/bash
# Service: Secure Deployment

SERVICE_NAME="secure-deploy"
PASSWORD_FILE="/secrets/deploy.password"
ALLOWED_USERS="/config/allowed_users.txt"

authenticate() {
    local user=$1
    local password=$2
    
    # Verify user
    grep -q "^${user}$" "$ALLOWED_USERS" || return 1
    
    # Verify password
    echo "$password" | sha256sum | grep -qf "$PASSWORD_FILE"
}

deploy_file() {
    local user=$1
    local file=$2
    local target=$3
    
    # Log access
    sq postgres "INSERT INTO deployment_log 
      (user, file, target, timestamp) 
      VALUES ('${user}', '${file}', '${target}', NOW())"
    
    # Deploy via SSH
    scp -i /secrets/deploy_key "$file" "${target}"
    
    # Notify
    sq slack deployments \
      --message "✓ ${user} deployed ${file} to ${target}" \
      --token "${SLACK_TOKEN}"
}

# API endpoint (simplified)
while true; do
    read -r request
    
    user=$(echo "$request" | jq -r '.user')
    password=$(echo "$request" | jq -r '.password')
    file=$(echo "$request" | jq -r '.file')
    target=$(echo "$request" | jq -r '.target')
    
    if authenticate "$user" "$password"; then
        deploy_file "$user" "$file" "$target"
        echo '{"status":"success"}'
    else
        echo '{"status":"unauthorized"}'
        sq postgres "INSERT INTO auth_failures 
          (user, timestamp) VALUES ('${user}', NOW())"
    fi
done
EOF
success "Secure deployment service"
echo ""

# Example 7: Multi-source Data Aggregation
echo "=== Example 7: Data Aggregation from Multiple Sources ==="
info "HTTP + PostgreSQL + Kafka → Combine → Store + Notify"
echo ""
example "# Aggregate data from multiple sources"
cat << 'EOF'
# Fetch from REST API
sq get api.company.com/metrics --json --save /tmp/api_data.json

# Query database
sq postgres "SELECT * FROM local_metrics WHERE date = CURRENT_DATE" \
  --json --save /tmp/db_data.json

# Consume recent Kafka messages
timeout 5s streamware "kafka://consume?topic=metrics&group=aggregator" \
  --pipe "transform://json" > /tmp/kafka_data.json

# Combine all sources
python3 << 'PYTHON'
import json

data = []
for source in ['api_data', 'db_data', 'kafka_data']:
    try:
        with open(f'/tmp/{source}.json') as f:
            data.extend(json.load(f))
    except:
        pass

# Aggregate
result = {
    'total_count': len(data),
    'total_value': sum(d.get('value', 0) for d in data),
    'sources': ['api', 'database', 'kafka']
}

with open('/tmp/aggregated.json', 'w') as f:
    json.dump(result, f)

print(f"Aggregated {len(data)} records")
PYTHON

# Store result
sq postgres "INSERT INTO aggregated_metrics 
  SELECT * FROM json_populate_record(null::aggregated_metrics, 
  '/tmp/aggregated.json')"

# Send summary
sq email reporting@company.com \
  --subject "Daily Metrics Summary" \
  --body "Total: $(cat /tmp/aggregated.json | jq -r '.total_count') records" \
  --attach /tmp/aggregated.json
EOF
success "Multi-source aggregation complete"
echo ""

# Example 8: Automated Backup Pipeline
echo "=== Example 8: Automated Multi-destination Backup ==="
info "Database → Export → FTP + SSH + S3"
echo ""
example "# Comprehensive backup strategy"
cat << 'EOF'
#!/bin/bash
# Daily backup service

BACKUP_DATE=$(date +%Y%m%d)
BACKUP_FILE="backup_${BACKUP_DATE}.sql"

# Export database
sq postgres "COPY (SELECT * FROM important_data) TO STDOUT" \
  --format csv > "/tmp/${BACKUP_FILE}"

# Compress
gzip "/tmp/${BACKUP_FILE}"
BACKUP_FILE="${BACKUP_FILE}.gz"

# Upload to FTP (primary backup)
curl -T "/tmp/${BACKUP_FILE}" \
  "ftp://backup1.company.com/daily/" \
  --user "${FTP_USER}:${FTP_PASS}"

# Copy to remote SSH (secondary backup)
scp -i ~/.ssh/backup_key "/tmp/${BACKUP_FILE}" \
  backup@backup2.company.com:/backups/daily/

# Upload to S3 (cloud backup)
aws s3 cp "/tmp/${BACKUP_FILE}" \
  "s3://company-backups/daily/${BACKUP_FILE}"

# Log success
sq postgres "INSERT INTO backup_log 
  (filename, size, destinations, timestamp) 
  VALUES 
  ('${BACKUP_FILE}', 
   $(stat -f%z "/tmp/${BACKUP_FILE}"), 
   'ftp,ssh,s3', 
   NOW())"

# Notify team
sq slack backups \
  --message "✓ Daily backup completed: ${BACKUP_FILE}" \
  --token "${SLACK_TOKEN}"

# Cleanup old backups (keep last 7 days)
find /tmp -name "backup_*.sql.gz" -mtime +7 -delete
EOF
success "Multi-destination backup pipeline"
echo ""

# Example 9: Monitoring & Alerting System
echo "=== Example 9: System Monitoring with Alerts ==="
info "Monitor services → Detect issues → Multi-channel alerts"
echo ""
example "# Comprehensive monitoring service"
cat << 'EOF'
#!/bin/bash
# Monitoring daemon

while true; do
  # Check API health
  http_status=$(sq get api.company.com/health --json | jq -r '.status')
  
  # Check database
  db_check=$(sq postgres "SELECT 1" --json 2>&1)
  
  # Check Kafka
  kafka_check=$(timeout 5s sq kafka test-topic --consume --json 2>&1)
  
  # Evaluate health
  if [[ "$http_status" != "healthy" ]] || \
     [[ "$db_check" == *"error"* ]] || \
     [[ "$kafka_check" == *"error"* ]]; then
    
    # Critical alert
    sq slack alerts \
      --message "🚨 CRITICAL: Service health check failed!" \
      --token "${SLACK_TOKEN}"
    
    sq email oncall@company.com \
      --subject "URGENT: System Alert" \
      --body "Health check failed. Immediate attention required."
    
    # Log incident
    sq postgres "INSERT INTO incidents 
      (type, severity, message, timestamp) 
      VALUES ('health_check', 'critical', 'Service down', NOW())"
  fi
  
  sleep 60
done
EOF
success "Monitoring system ready"
echo ""

# Example 10: CI/CD Deployment Pipeline
echo "=== Example 10: Automated CI/CD Pipeline ==="
info "Git webhook → Build → Test → Deploy → Notify"
echo ""
example "# CI/CD automation"
cat << 'EOF'
#!/bin/bash
# Deployment pipeline triggered by webhook

deploy() {
    local branch=$1
    local commit=$2
    
    # Fetch code
    git clone https://github.com/company/app.git /tmp/deploy
    cd /tmp/deploy
    git checkout "$commit"
    
    # Run tests
    if ! make test; then
        sq slack deployments \
          --message "❌ Tests failed for ${commit}" \
          --token "${SLACK_TOKEN}"
        return 1
    fi
    
    # Build
    docker build -t app:${commit} .
    
    # Deploy via SSH
    ssh deploy@prod.company.com << REMOTE
        docker pull app:${commit}
        docker stop app || true
        docker run -d --name app app:${commit}
REMOTE
    
    # Log deployment
    sq postgres "INSERT INTO deployments 
      (branch, commit, timestamp, status) 
      VALUES ('${branch}', '${commit}', NOW(), 'success')"
    
    # Notify team
    sq slack deployments \
      --message "✓ Deployed ${branch}@${commit} to production" \
      --token "${SLACK_TOKEN}"
    
    # Cleanup
    rm -rf /tmp/deploy
}

# Webhook listener (simplified)
while true; do
    read -r webhook
    branch=$(echo "$webhook" | jq -r '.ref')
    commit=$(echo "$webhook" | jq -r '.after')
    
    if [[ "$branch" == "refs/heads/main" ]]; then
        deploy "main" "$commit"
    fi
done
EOF
success "CI/CD pipeline configured"
echo ""

echo "=========================================="
echo "SUMMARY"
echo "=========================================="
echo ""
success "10 Advanced examples created!"
echo ""
echo "Key patterns demonstrated:"
echo "  • Multi-service integration"
echo "  • Secure authentication & authorization"
echo "  • Real-time stream processing"
echo "  • Automated backups & deployments"
echo "  • Monitoring & alerting"
echo "  • ETL pipelines"
echo "  • File distribution"
echo "  • Report generation"
echo ""
echo "All examples use 'sq' (quick CLI) for simplicity!"
echo ""
