#!/bin/bash
# =============================================================================
# Full Security Pipeline
# Discovery → Quick Check → Smart Analysis → Alert → Report
# =============================================================================

source "$(dirname "$0")/common.sh"

set -e

print_header "🔒 Full Security Pipeline"

setup_dirs

# =============================================================================
# Stage 1: Discovery
# =============================================================================
print_step "Stage 1: 🔍 Camera Discovery"

CAMERAS_JSON=$(sq network find "cameras" --json 2>/dev/null || echo '{"devices":[]}')
CAMERA_COUNT=$(echo "$CAMERAS_JSON" | jq -r '.devices | length')

if [ "$CAMERA_COUNT" -eq 0 ]; then
    print_warning "No cameras found. Using CAMERA_URL from .env"
    ensure_camera_url
    CAMERA_COUNT=1
else
    print_success "Found $CAMERA_COUNT camera(s)"
    echo ""
    echo "$CAMERAS_JSON" | jq -r '.devices[] | "  📷 \(.ip) - \(.vendor // "Unknown")"'
fi
echo ""

# =============================================================================
# Stage 2: Quick Scan (All Cameras)
# =============================================================================
print_step "Stage 2: ⚡ Quick Motion Scan"

CAMERAS_WITH_MOTION=()
TOTAL_SCANNED=0

if [ "$CAMERA_COUNT" -gt 0 ] && [ -n "$(echo "$CAMERAS_JSON" | jq -r '.devices[0].ip // empty')" ]; then
    # Scan discovered cameras
    while IFS='|' read -r IP RTSP_URL; do
        if [ -z "$RTSP_URL" ]; then continue; fi
        
        TOTAL_SCANNED=$((TOTAL_SCANNED + 1))
        echo "  ⚡ Quick scan: $IP"
        
        # Quick pixel diff (no AI)
        RESULT=$(sq smart watch \
            --url "$RTSP_URL" \
            --min-interval 0.5 \
            --duration 10 \
            --no-ai \
            --json 2>/dev/null || echo '{"frames_with_changes": 0}')
        
        CHANGES=$(echo "$RESULT" | jq -r '.frames_with_changes // 0')
        
        if [ "$CHANGES" -gt 0 ]; then
            echo "     🔴 Motion detected ($CHANGES changes)"
            CAMERAS_WITH_MOTION+=("$IP|$RTSP_URL")
        else
            echo "     ✅ Stable"
        fi
        
    done < <(echo "$CAMERAS_JSON" | jq -r '.devices[] | "\(.ip)|\(.connection.rtsp[0] // "")"')
else
    # Use single camera from .env
    echo "  ⚡ Quick scan: $CAMERA_URL"
    RESULT=$(sq smart watch \
        --url "$CAMERA_URL" \
        --min-interval 0.5 \
        --duration 10 \
        --no-ai \
        --json 2>/dev/null || echo '{"frames_with_changes": 0}')
    
    CHANGES=$(echo "$RESULT" | jq -r '.frames_with_changes // 0')
    TOTAL_SCANNED=1
    
    if [ "$CHANGES" -gt 0 ]; then
        echo "     🔴 Motion detected"
        CAMERAS_WITH_MOTION+=("single|$CAMERA_URL")
    else
        echo "     ✅ Stable"
    fi
fi

echo ""
echo "Quick scan complete: ${#CAMERAS_WITH_MOTION[@]}/$TOTAL_SCANNED cameras with motion"
echo ""

if [ ${#CAMERAS_WITH_MOTION[@]} -eq 0 ]; then
    print_success "No motion detected on any camera"
    exit 0
fi

# =============================================================================
# Stage 3: Smart Analysis (Only cameras with motion)
# =============================================================================
print_step "Stage 3: 🎯 Smart Analysis"

ALERTS=()

for CAM in "${CAMERAS_WITH_MOTION[@]}"; do
    IFS='|' read -r IP RTSP_URL <<< "$CAM"
    
    echo ""
    echo "📹 Analyzing: $IP"
    
    REPORT_FILE="$REPORTS_DIR/alert_${IP//./_}_$(get_file_timestamp).html"
    
    # Full smart analysis with AI
    RESULT=$(sq smart monitor \
        --url "$RTSP_URL" \
        --min-interval 1 \
        --max-interval 5 \
        --threshold 20 \
        --focus "$FOCUS" \
        --duration 30 \
        --file "$REPORT_FILE" \
        --json 2>/dev/null)
    
    CHANGES=$(echo "$RESULT" | jq -r '.frames_with_changes // 0')
    
    if [ "$CHANGES" -gt 0 ]; then
        echo "   🔴 Confirmed: $CHANGES significant changes"
        echo "   📄 Report: $REPORT_FILE"
        
        # Get analysis summary
        SUMMARY=$(echo "$RESULT" | jq -r '.timeline[] | select(.type == "change") | .analysis' | head -1)
        
        ALERTS+=("$IP|$CHANGES|$REPORT_FILE|${SUMMARY:0:100}")
        
        log_message "ALERT" "Camera $IP: $CHANGES changes - $REPORT_FILE"
    else
        echo "   ✅ False positive - no significant activity"
    fi
done

echo ""

# =============================================================================
# Stage 4: Send Alerts
# =============================================================================
if [ ${#ALERTS[@]} -gt 0 ]; then
    print_step "Stage 4: 🚨 Sending Alerts"
    
    for ALERT in "${ALERTS[@]}"; do
        IFS='|' read -r IP CHANGES REPORT SUMMARY <<< "$ALERT"
        
        MSG="🚨 Security Alert!
Camera: $IP
Changes: $CHANGES
Summary: $SUMMARY
Report: $REPORT"
        
        echo "Alerting for $IP..."
        send_alert "$MSG"
    done
    echo ""
fi

# =============================================================================
# Summary
# =============================================================================
print_step "📊 Pipeline Summary"

echo "Cameras scanned: $TOTAL_SCANNED"
echo "Cameras with motion: ${#CAMERAS_WITH_MOTION[@]}"
echo "Confirmed alerts: ${#ALERTS[@]}"
echo "Reports directory: $REPORTS_DIR/"
echo ""

if [ ${#ALERTS[@]} -gt 0 ]; then
    echo "⚠️  ALERTS:"
    for ALERT in "${ALERTS[@]}"; do
        IFS='|' read -r IP CHANGES REPORT SUMMARY <<< "$ALERT"
        echo "  - $IP: $CHANGES changes"
    done
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💡 Run continuously:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "while true; do ./23_full_pipeline.sh; sleep 60; done"
echo ""
