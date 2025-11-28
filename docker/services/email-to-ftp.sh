#!/bin/bash
# Email Attachments to FTP Service
# Continuously monitors email and uploads attachments to FTP

set -e

SERVICE_NAME="streamware-email-ftp"
LOG_FILE="/logs/${SERVICE_NAME}.log"
PID_FILE="/tmp/${SERVICE_NAME}.pid"

# Configuration from environment variables
EMAIL_HOST="${EMAIL_HOST:-imap.gmail.com}"
EMAIL_USER="${EMAIL_USER:-user@example.com}"
EMAIL_PASSWORD="${EMAIL_PASSWORD:-password}"
FTP_HOST="${FTP_HOST:-ftp.example.com}"
FTP_USER="${FTP_USER:-ftpuser}"
FTP_PASSWORD="${FTP_PASSWORD:-ftppass}"
CHECK_INTERVAL="${CHECK_INTERVAL:-60}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Process email and upload attachments
process_emails() {
    log "Checking for new emails with attachments..."
    
    # Read emails with attachments
    sq email-read "$EMAIL_HOST" \
        --user "$EMAIL_USER" \
        --password "$EMAIL_PASSWORD" \
        --filter "has:attachment" \
        --save /tmp/emails.json
    
    # Extract attachments
    python3 << 'EOF'
import json
import base64
import os

with open('/tmp/emails.json', 'r') as f:
    emails = json.load(f)

for email in emails:
    if 'attachments' in email:
        for attachment in email['attachments']:
            filename = attachment['filename']
            content = base64.b64decode(attachment['content'])
            
            filepath = f"/tmp/attachments/{filename}"
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'wb') as f:
                f.write(content)
            
            print(f"Extracted: {filename}")
EOF
    
    # Upload to FTP
    for file in /tmp/attachments/*; do
        if [ -f "$file" ]; then
            filename=$(basename "$file")
            log "Uploading $filename to FTP..."
            
            curl -T "$file" \
                "ftp://${FTP_HOST}/" \
                --user "${FTP_USER}:${FTP_PASSWORD}" \
                >> "$LOG_FILE" 2>&1
            
            log "✓ Uploaded: $filename"
            rm "$file"
        fi
    done
}

# Main loop
main() {
    log "Starting $SERVICE_NAME"
    log "Email: $EMAIL_HOST"
    log "FTP: $FTP_HOST"
    log "Check interval: ${CHECK_INTERVAL}s"
    
    # Create directories
    mkdir -p /tmp/attachments /logs
    
    # Save PID
    echo $$ > "$PID_FILE"
    
    while true; do
        process_emails || log "Error processing emails"
        sleep "$CHECK_INTERVAL"
    done
}

# Signal handling
cleanup() {
    log "Stopping $SERVICE_NAME"
    rm -f "$PID_FILE"
    exit 0
}

trap cleanup SIGTERM SIGINT

# Run
main
