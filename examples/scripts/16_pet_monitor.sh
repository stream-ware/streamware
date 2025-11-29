#!/bin/bash
# =============================================================================
# Pet Monitor Script
# Monitor pets at home while away
# =============================================================================

source "$(dirname "$0")/common.sh"

print_header "🐾 Pet Monitor"

# Override focus for animals
FOCUS="animal"
OBJECTS="dog,cat,animal"

# Use camera URL from .env or argument
CAMERA_URL="${1:-$CAMERA_URL}"
ensure_camera_url

show_config

setup_dirs

print_step "🐕 Monitoring for pet activity..."

echo "Detecting: $OBJECTS"
echo "Duration: ${DURATION}s"
echo ""

# Run detection
RESULT=$(sq tracking detect \
    --url "$CAMERA_URL" \
    --objects "$OBJECTS" \
    --duration "$DURATION" \
    --interval "$INTERVAL" \
    --json 2>/dev/null)

TOTAL=$(echo "$RESULT" | jq -r '.summary.total_objects // 0')
DOGS=$(echo "$RESULT" | jq -r '.summary.by_type.dog // 0')
CATS=$(echo "$RESULT" | jq -r '.summary.by_type.cat // 0')

print_step "📊 Results"

echo "Animals detected: $TOTAL"
if [ "$DOGS" -gt 0 ]; then
    echo "  🐕 Dogs: $DOGS"
fi
if [ "$CATS" -gt 0 ]; then
    echo "  🐱 Cats: $CATS"
fi
echo ""

# Show detected objects
if [ "$TOTAL" -gt 0 ]; then
    echo "Activity:"
    echo "$RESULT" | jq -r '.summary.objects[] | "  \(.type) - \(.direction) direction, visible \(.frames_visible) frames"'
    echo ""
fi

# Save results
REPORT_FILE="$REPORTS_DIR/pet_$(get_file_timestamp).json"
echo "$RESULT" | jq '.' > "$REPORT_FILE"
print_success "Results saved: $REPORT_FILE"

# Optional: Take snapshot when pet detected
if [ "$TOTAL" -gt 0 ]; then
    SNAPSHOT="$FRAMES_DIR/pet_$(get_file_timestamp).jpg"
    ffmpeg -y -rtsp_transport tcp -i "$CAMERA_URL" -frames:v 1 -q:v 2 "$SNAPSHOT" 2>/dev/null
    if [ -f "$SNAPSHOT" ]; then
        print_success "Snapshot: $SNAPSHOT"
    fi
    
    send_alert "🐾 Pet activity detected! $TOTAL animal(s) visible"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💡 Check on pets regularly:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "# Check every 30 minutes"
echo "*/30 * * * * cd $(pwd) && ./16_pet_monitor.sh"
echo ""
