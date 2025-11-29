#!/bin/bash
# =============================================================================
# Motion Alert Script
# Monitor camera and send alert on activity
# =============================================================================

# Configuration
CAMERA_URL="${1:-rtsp://admin:admin@192.168.1.100:554/stream}"
CHECK_INTERVAL="${2:-60}"  # Seconds between checks
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"
TELEGRAM_TOKEN="${TELEGRAM_TOKEN:-}"
TELEGRAM_CHAT="${TELEGRAM_CHAT:-}"

echo "========================================"
echo "🚨 Motion Alert Monitor"
echo "========================================"
echo ""
echo "Camera: $CAMERA_URL"
echo "Check every: ${CHECK_INTERVAL}s"
echo ""

# Check configuration
if [ -n "$SLACK_WEBHOOK" ]; then
    echo "✅ Slack alerts enabled"
fi
if [ -n "$TELEGRAM_TOKEN" ] && [ -n "$TELEGRAM_CHAT" ]; then
    echo "✅ Telegram alerts enabled"
fi
echo ""

# Function to send Slack alert
send_slack_alert() {
    local message="$1"
    if [ -n "$SLACK_WEBHOOK" ]; then
        curl -s -X POST "$SLACK_WEBHOOK" \
            -H 'Content-Type: application/json' \
            -d "{\"text\": \"$message\"}" > /dev/null
        echo "   📱 Slack alert sent"
    fi
}

# Function to send Telegram alert
send_telegram_alert() {
    local message="$1"
    if [ -n "$TELEGRAM_TOKEN" ] && [ -n "$TELEGRAM_CHAT" ]; then
        curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_TOKEN/sendMessage" \
            -d "chat_id=$TELEGRAM_CHAT" \
            -d "text=$message" > /dev/null
        echo "   📱 Telegram alert sent"
    fi
}

# Monitor loop
echo "👁️ Starting monitoring (Ctrl+C to stop)..."
echo ""

CHECK_COUNT=0

while true; do
    CHECK_COUNT=$((CHECK_COUNT + 1))
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo "[$TIMESTAMP] Check #$CHECK_COUNT"
    
    # Run quick analysis (30 seconds)
    RESULT=$(sq stream rtsp \
        --url "$CAMERA_URL" \
        --mode diff \
        --focus person \
        --sensitivity low \
        --duration 30 \
        --interval 15 \
        --json 2>/dev/null || echo '{"significant_changes": 0}')
    
    CHANGES=$(echo "$RESULT" | jq -r '.significant_changes // 0')
    
    if [ "$CHANGES" -gt 0 ]; then
        echo "   🔴 MOTION DETECTED: $CHANGES changes"
        
        # Send alerts
        ALERT_MSG="🚨 Motion detected on camera! $CHANGES change(s) at $TIMESTAMP"
        send_slack_alert "$ALERT_MSG"
        send_telegram_alert "$ALERT_MSG"
        
        # Generate report
        REPORT_FILE="motion_$(date +%Y%m%d_%H%M%S).html"
        sq stream rtsp \
            --url "$CAMERA_URL" \
            --mode diff \
            --focus person \
            --duration 30 \
            --file "$REPORT_FILE" \
            --quiet 2>/dev/null
        echo "   📄 Report: $REPORT_FILE"
    else
        echo "   ✅ No motion"
    fi
    
    echo ""
    
    # Wait for next check
    sleep "$CHECK_INTERVAL"
done
