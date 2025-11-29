#!/bin/bash
# =============================================================================
# Continuous Monitor Script
# 24/7 monitoring with alerts and logging
# =============================================================================

source "$(dirname "$0")/common.sh"

print_header "👁️ Continuous Monitor (24/7)"

# Use camera URL from .env or argument
CAMERA_URL="${1:-$CAMERA_URL}"
ensure_camera_url

show_config

setup_dirs

# Alert counters
ALERT_COUNT=0
LAST_ALERT_HOUR=$(date +%H)
ALERTS_THIS_HOUR=0
MAX_ALERTS="${MAX_ALERTS_PER_HOUR:-10}"

print_step "🚀 Starting continuous monitoring..."
echo ""
echo "Check interval: ${MONITOR_INTERVAL}s"
echo "Max alerts/hour: $MAX_ALERTS"
echo "Press Ctrl+C to stop"
echo ""

log_message "INFO" "Continuous monitoring started for $CAMERA_URL"

CHECK_COUNT=0

while true; do
    CHECK_COUNT=$((CHECK_COUNT + 1))
    CURRENT_HOUR=$(date +%H)
    
    # Reset hourly counter
    if [ "$CURRENT_HOUR" != "$LAST_ALERT_HOUR" ]; then
        ALERTS_THIS_HOUR=0
        LAST_ALERT_HOUR=$CURRENT_HOUR
    fi
    
    TIMESTAMP=$(get_timestamp)
    echo "[$TIMESTAMP] Check #$CHECK_COUNT"
    
    # Run quick analysis
    RESULT=$(sq stream rtsp \
        --url "$CAMERA_URL" \
        --mode diff \
        --focus "$FOCUS" \
        --sensitivity "$SENSITIVITY" \
        --duration 30 \
        --interval 15 \
        --json 2>/dev/null || echo '{"significant_changes": 0}')
    
    CHANGES=$(echo "$RESULT" | jq -r '.significant_changes // 0')
    
    if [ "$CHANGES" -gt 0 ]; then
        echo "   🔴 MOTION DETECTED: $CHANGES changes"
        log_message "ALERT" "Motion detected: $CHANGES changes"
        
        # Generate report
        REPORT_FILE="$REPORTS_DIR/motion_$(get_file_timestamp).html"
        sq stream rtsp \
            --url "$CAMERA_URL" \
            --mode diff \
            --focus "$FOCUS" \
            --duration 30 \
            --file "$REPORT_FILE" \
            --quiet 2>/dev/null
        
        echo "   📄 Report: $REPORT_FILE"
        
        # Send alert (rate limited)
        if [ "$ALERTS_THIS_HOUR" -lt "$MAX_ALERTS" ] || [ "$MAX_ALERTS" -eq 0 ]; then
            send_alert "🚨 Motion detected! $CHANGES change(s) at $TIMESTAMP. Report: $REPORT_FILE"
            ALERTS_THIS_HOUR=$((ALERTS_THIS_HOUR + 1))
            ALERT_COUNT=$((ALERT_COUNT + 1))
        else
            echo "   ⚠️ Alert rate limit reached ($MAX_ALERTS/hour)"
        fi
    else
        echo "   ✅ No motion"
        log_message "INFO" "Check #$CHECK_COUNT - No motion"
    fi
    
    echo ""
    sleep "$MONITOR_INTERVAL"
done
