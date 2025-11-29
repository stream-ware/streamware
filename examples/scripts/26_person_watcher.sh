#!/bin/bash
# =============================================================================
# Person Watcher - Detect and describe people
# "Alert when person appears and describe how they look"
# =============================================================================

source "$(dirname "$0")/common.sh"

print_header "👤 Person Watcher"

CAMERA_URL="${1:-$CAMERA_URL}"
ensure_camera_url

print_step "This script will:"
echo ""
echo "  1. Watch the camera for people"
echo "  2. Alert when a person appears"
echo "  3. Describe how the person looks"
echo "  4. Track when person enters/leaves"
echo ""

setup_dirs

REPORT_FILE="$REPORTS_DIR/person_watch_$(get_file_timestamp).txt"

print_step "👁️ Watching for people..."
echo "Output: $REPORT_FILE"
echo ""

# Run with triggers for person detection
sq live watch \
    --url "$CAMERA_URL" \
    --trigger "person appears,person visible,someone enters,person leaves" \
    --tts \
    --interval 2 \
    --duration "${DURATION:-120}" \
    --focus "person clothing face" \
    --json | tee "$REPORT_FILE"

echo ""

# Parse and show summary
if [ -f "$REPORT_FILE" ]; then
    ALERTS=$(cat "$REPORT_FILE" | jq -r '.alerts | length // 0' 2>/dev/null || echo "0")
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📊 Summary"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Alerts: $ALERTS"
    echo "Report: $REPORT_FILE"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💡 Advanced Usage:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "# Watch all day (8 hours):"
echo "sq live watch --url \"\$URL\" --trigger \"person\" --duration 28800"
echo ""
echo "# With Slack alerts:"
echo "sq live watch --url \"\$URL\" --trigger \"intruder\" --webhook \"\$SLACK_WEBHOOK\""
echo ""
echo "# Describe person in detail:"
echo "sq live describe --url \"\$URL\" --focus \"person clothing age gender\""
echo ""
