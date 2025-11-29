#!/bin/bash
# =============================================================================
# Trigger-Based Alerts - Watch for specific conditions
# "Alert when person appears", "Alert when door opens"
# =============================================================================

source "$(dirname "$0")/common.sh"

print_header "🎯 Trigger-Based Alerts"

CAMERA_URL="${1:-$CAMERA_URL}"
ensure_camera_url

print_step "Configuration"
echo ""
echo "Triggers to watch for:"
echo "  - person appears"
echo "  - someone enters the room"
echo "  - door opens"
echo "  - package delivered"
echo ""

# Define triggers (comma-separated)
TRIGGERS="${TRIGGERS:-person appears,someone enters,door opens}"

print_step "👁️ Watching for triggers..."
echo "Triggers: $TRIGGERS"
echo "Duration: ${DURATION:-60}s"
echo ""

# Check for espeak
if command -v espeak &> /dev/null; then
    TTS_FLAG="--tts"
else
    TTS_FLAG=""
fi

sq live watch \
    --url "$CAMERA_URL" \
    --trigger "$TRIGGERS" \
    $TTS_FLAG \
    --interval 2 \
    --duration "${DURATION:-60}" \
    --yaml

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💡 Custom Triggers:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "# Watch for person:"
echo "sq live watch --url \"\$URL\" --trigger \"person appears\""
echo ""
echo "# Watch for multiple conditions:"
echo "sq live watch --url \"\$URL\" --trigger \"person,car,dog\""
echo ""
echo "# With webhook:"
echo "sq live watch --url \"\$URL\" --trigger \"intruder\" --webhook \"\$SLACK_WEBHOOK\""
echo ""
echo "# Custom .env:"
echo 'TRIGGERS="person at door,package on porch,car in driveway"'
echo ""
