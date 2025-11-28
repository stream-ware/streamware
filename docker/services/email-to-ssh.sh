#!/bin/bash
# Email Attachments to SSH Service - SIMPLIFIED with sq
# Automatically uploads email attachments to remote server via SSH

set -e

SERVICE_NAME="streamware-email-ssh"
LOG_FILE="/logs/${SERVICE_NAME}.log"
PID_FILE="/tmp/${SERVICE_NAME}.pid"

# Configuration from environment
EMAIL_HOST="${EMAIL_HOST:-imap.gmail.com}"
EMAIL_USER="${EMAIL_USER}"
EMAIL_PASSWORD="${EMAIL_PASSWORD}"
SSH_HOST="${SSH_HOST:-remote.example.com}"
SSH_USER="${SSH_USER:-deploy}"
SSH_KEY="${SSH_KEY:-~/.ssh/id_rsa}"
SSH_PORT="${SSH_PORT:-22}"
REMOTE_PATH="${REMOTE_PATH:-/data/uploads}"
CHECK_INTERVAL="${CHECK_INTERVAL:-60}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

process_emails() {
    log "Checking for email attachments..."
    
    # Get emails with attachments (using sq quick style)
    sq email "$EMAIL_HOST" \
        --user "$EMAIL_USER" \
        --password "$EMAIL_PASSWORD" \
        --attachments \
        --save /tmp/attachments/ || {
            log "No new attachments"
            return 0
        }
    
    # Upload each attachment using SSH component
    for file in /tmp/attachments/*; do
        if [ -f "$file" ]; then
            filename=$(basename "$file")
            log "Uploading $filename..."
            
            # Use sq ssh for simple upload
            sq ssh "$SSH_HOST" \
                --upload "$file" \
                --user "$SSH_USER" \
                --key "$SSH_KEY" \
                --port "$SSH_PORT" \
                --remote "$REMOTE_PATH/$filename" && {
                    log "✓ Uploaded: $filename"
                    rm "$file"
                } || {
                    log "✗ Failed: $filename"
                }
        fi
    done
}

main() {
    log "Starting $SERVICE_NAME"
    log "Email: $EMAIL_HOST"
    log "SSH: ${SSH_USER}@${SSH_HOST}:${SSH_PORT}"
    log "Remote path: $REMOTE_PATH"
    log "Check interval: ${CHECK_INTERVAL}s"
    
    mkdir -p /tmp/attachments /logs
    echo $$ > "$PID_FILE"
    
    # Main loop
    while true; do
        process_emails || log "Error processing emails"
        sleep "$CHECK_INTERVAL"
    done
}

cleanup() {
    log "Stopping $SERVICE_NAME"
    rm -f "$PID_FILE"
    exit 0
}

trap cleanup SIGTERM SIGINT

main
