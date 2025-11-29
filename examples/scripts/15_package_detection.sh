#!/bin/bash
# =============================================================================
# Package Detection Script
# Monitor for package deliveries at doorstep
# =============================================================================

source "$(dirname "$0")/common.sh"

print_header "📦 Package Detection"

# Override focus for package detection
FOCUS="package"

# Use camera URL from .env or argument
CAMERA_URL="${1:-$CAMERA_URL}"
ensure_camera_url

show_config

setup_dirs

print_step "👁️ Monitoring for deliveries..."

echo "Focus: package, person"
echo "Duration: ${DURATION}s"
echo ""

# Run detection
RESULT=$(sq stream rtsp \
    --url "$CAMERA_URL" \
    --mode diff \
    --focus "package" \
    --sensitivity "medium" \
    --duration "$DURATION" \
    --interval "$INTERVAL" \
    --json 2>/dev/null)

CHANGES=$(echo "$RESULT" | jq -r '.significant_changes // 0')
FRAMES=$(echo "$RESULT" | jq -r '.frames_analyzed // 0')

print_step "📊 Results"

if [ "$CHANGES" -gt 0 ]; then
    echo "📦 DELIVERY ACTIVITY DETECTED!"
    echo ""
    echo "Changes: $CHANGES"
    echo "Frames analyzed: $FRAMES"
    echo ""
    
    # Show timeline
    echo "Timeline:"
    echo "$RESULT" | jq -r '.timeline[] | select(.type == "change") | "  [\(.timestamp)] \(.changes[:100])..."'
    echo ""
    
    # Generate report
    REPORT_FILE="$REPORTS_DIR/package_$(get_file_timestamp).html"
    sq stream rtsp \
        --url "$CAMERA_URL" \
        --mode diff \
        --focus "package" \
        --duration 30 \
        --file "$REPORT_FILE" \
        --quiet 2>/dev/null
    
    print_success "Report: $REPORT_FILE"
    
    # Send alert
    send_alert "📦 Package activity detected! Check $REPORT_FILE"
    
    log_message "ALERT" "Package activity: $CHANGES changes"
else
    echo "✅ No delivery activity"
    echo "Frames analyzed: $FRAMES"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💡 Continuous monitoring:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "# Monitor every 5 minutes"
echo "while true; do ./15_package_detection.sh; sleep 300; done"
echo ""
echo "# Set up in cron (check every 10 min during delivery hours)"
echo "*/10 8-18 * * * cd $(pwd) && ./15_package_detection.sh"
echo ""
