#!/bin/bash
# =============================================================================
# Live Narrator - Real-time description with TTS
# Describes what's happening on camera in real-time
# =============================================================================

source "$(dirname "$0")/common.sh"

print_header "🎙️ Live Narrator (TTS)"

CAMERA_URL="${1:-$CAMERA_URL}"
ensure_camera_url

print_step "Starting live narration..."
echo ""
echo "The system will:"
echo "  1. Capture frames every 3 seconds"
echo "  2. Detect if there are changes (skip if stable)"
echo "  3. Describe what it sees using AI"
echo "  4. Speak the description aloud (if --tts)"
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

print_step "🎬 Live narration starting..."
echo ""

sq live narrator \
    --url "$CAMERA_URL" \
    $TTS_FLAG \
    --interval 3 \
    --duration 30 \
    --focus "$FOCUS" \
    --yaml

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💡 Examples:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "# Describe once:"
echo "sq live describe --url \"\$CAMERA_URL\" --tts"
echo ""
echo "# Watch for 5 minutes with TTS:"
echo "sq live narrator --url \"\$CAMERA_URL\" --tts --duration 300"
echo ""
echo "# Focus on people:"
echo "sq live narrator --url \"\$CAMERA_URL\" --tts --focus person"
echo ""
