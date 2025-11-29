#!/bin/bash
# =============================================================================
# Live Narrator - Real-time description with TTS
# Describes what's happening on camera in real-time
# =============================================================================

source "$(dirname "$0")/common.sh"

print_header "🎙️ Live Narrator (TTS)"

CAMERA_URL="${1:-$CAMERA_URL}"
MODE="${2:-full}"  # full, diff, track
ensure_camera_url

print_step "Available modes:"
echo "  full  - Describe entire scene each time"
echo "  diff  - Describe only what changed"
echo "  track - Track specific object (e.g., person)"
echo ""
echo "Selected: $MODE"
echo ""

# Check for espeak
if command -v espeak &> /dev/null; then
    TTS_FLAG="--tts"
    echo "📢 TTS enabled (espeak)"
else
    TTS_FLAG=""
    print_warning "espeak not installed - TTS disabled"
    echo "Install: sudo apt install espeak"
fi
echo ""

print_step "🎬 Live narration ($MODE mode)..."
echo ""

sq live narrator \
    --url "$CAMERA_URL" \
    --mode "$MODE" \
    $TTS_FLAG \
    --interval 3 \
    --duration 30 \
    --focus "${FOCUS:-person}" \
    --yaml

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💡 Mode Examples:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "# FULL mode - describe everything:"
echo "sq live narrator --url \"\$URL\" --mode full --tts"
echo ""
echo "# DIFF mode - only describe changes:"
echo "sq live narrator --url \"\$URL\" --mode diff --tts"
echo ""
echo "# TRACK mode - track person:"
echo "sq live narrator --url \"\$URL\" --mode track --focus person --tts"
echo ""
echo "# Track with JSON output:"
echo "sq live narrator --url \"\$URL\" --mode track --focus person --json"
echo ""
