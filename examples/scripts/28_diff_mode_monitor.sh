#!/bin/bash
# =============================================================================
# Diff Mode Monitor - Only describe changes
# Instead of describing entire scene, only reports what changed
# =============================================================================

source "$(dirname "$0")/common.sh"

print_header "🔄 Diff Mode Monitor"

CAMERA_URL="${1:-$CAMERA_URL}"
ensure_camera_url

print_step "Diff mode describes ONLY changes"
echo ""
echo "Instead of:"
echo "  'The room has a desk, computer, and person sitting...'"
echo ""
echo "You get:"
echo "  'Person moved from left to right'"
echo "  'Person stood up'"
echo "  'No changes'"
echo ""

# Check for TTS
if command -v espeak &> /dev/null; then
    TTS_FLAG="--tts"
    echo "📢 TTS enabled"
else
    TTS_FLAG=""
fi
echo ""

print_step "Starting diff mode monitoring..."
echo ""

sq live narrator \
    --url "$CAMERA_URL" \
    --mode diff \
    --focus person \
    $TTS_FLAG \
    --interval 5 \
    --duration "${DURATION:-60}"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💡 Mode comparison:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "# FULL mode (default) - describe everything:"
echo "sq live narrator --url \"\$URL\" --mode full"
echo ""
echo "# DIFF mode - only changes:"
echo "sq live narrator --url \"\$URL\" --mode diff"
echo ""
echo "# TRACK mode - track specific object:"
echo "sq live narrator --url \"\$URL\" --mode track --focus person"
echo ""
