#!/bin/bash
# =============================================================================
# Multi-Camera Monitor Script
# Monitor all cameras discovered on network
# =============================================================================

source "$(dirname "$0")/common.sh"

print_header "📷 Multi-Camera Monitor"

setup_dirs

print_step "🔍 Discovering cameras..."

# Get all cameras
CAMERAS_JSON=$(sq network find "cameras" --json 2>/dev/null)
CAMERA_COUNT=$(echo "$CAMERAS_JSON" | jq -r '.devices | length')

if [ "$CAMERA_COUNT" -eq 0 ]; then
    print_error "No cameras found on network"
    exit 1
fi

print_success "Found $CAMERA_COUNT camera(s)"
echo ""

# List cameras
echo "Cameras to monitor:"
echo "$CAMERAS_JSON" | jq -r '.devices[] | "  📷 \(.ip) - \(.vendor // "Unknown")"'
echo ""

print_step "🎥 Analyzing all cameras..."

TOTAL_ALERTS=0
RESULTS=()

# Process each camera
while IFS='|' read -r IP VENDOR RTSP_URL; do
    if [ -z "$RTSP_URL" ]; then
        print_warning "Skipping $IP - no RTSP URL"
        continue
    fi
    
    echo ""
    echo "📹 Camera: $IP ($VENDOR)"
    echo "   URL: ${RTSP_URL:0:50}..."
    
    # Run analysis
    RESULT=$(sq stream rtsp \
        --url "$RTSP_URL" \
        --mode diff \
        --focus "$FOCUS" \
        --sensitivity "$SENSITIVITY" \
        --duration 30 \
        --interval 10 \
        --json 2>/dev/null || echo '{"significant_changes": 0}')
    
    CHANGES=$(echo "$RESULT" | jq -r '.significant_changes // 0')
    
    if [ "$CHANGES" -gt 0 ]; then
        echo "   🔴 ACTIVITY: $CHANGES changes"
        TOTAL_ALERTS=$((TOTAL_ALERTS + 1))
        
        # Generate report
        REPORT_FILE="$REPORTS_DIR/camera_${IP//./_}_$(get_file_timestamp).html"
        sq stream rtsp \
            --url "$RTSP_URL" \
            --mode diff \
            --focus "$FOCUS" \
            --duration 30 \
            --file "$REPORT_FILE" \
            --quiet 2>/dev/null
        
        echo "   📄 Report: $REPORT_FILE"
        
        log_message "ALERT" "Camera $IP: $CHANGES changes"
    else
        echo "   ✅ No activity"
    fi
    
done < <(echo "$CAMERAS_JSON" | jq -r '.devices[] | "\(.ip)|\(.vendor // "Unknown")|\(.connection.rtsp[0] // "")"')

print_step "📊 Summary"

echo "Cameras checked: $CAMERA_COUNT"
echo "Cameras with activity: $TOTAL_ALERTS"
echo "Reports: $REPORTS_DIR/"
echo ""

# Send summary alert
if [ "$TOTAL_ALERTS" -gt 0 ]; then
    send_alert "📷 Multi-camera scan: $TOTAL_ALERTS/$CAMERA_COUNT cameras with activity"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💡 Run continuously:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "while true; do ./13_multi_camera.sh; sleep 300; done"
echo ""
