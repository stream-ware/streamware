#!/bin/bash
# =============================================================================
# Smart Monitor - Buffered adaptive monitoring
# Frame capture continues even when AI is processing
# =============================================================================

source "$(dirname "$0")/common.sh"

print_header "🎯 Smart Monitor (Buffered)"

# Use camera URL from .env or argument
CAMERA_URL="${1:-$CAMERA_URL}"
ensure_camera_url

show_config

setup_dirs

print_step "Configuration"

echo "Min interval: ${MIN_INTERVAL:-1}s (capture faster when activity)"
echo "Max interval: ${MAX_INTERVAL:-10}s (capture slower when stable)"
echo "Buffer size: ${BUFFER_SIZE:-50} frames"
echo "Threshold: ${THRESHOLD:-25}"
echo ""

print_step "🚀 Starting smart monitoring..."
echo ""

# Run smart monitor
sq smart monitor \
    --url "$CAMERA_URL" \
    --min-interval "${MIN_INTERVAL:-1}" \
    --max-interval "${MAX_INTERVAL:-10}" \
    --buffer-size "${BUFFER_SIZE:-50}" \
    --threshold "${THRESHOLD:-25}" \
    --focus "$FOCUS" \
    --duration "$DURATION" \
    --file "$REPORTS_DIR/smart_$(get_file_timestamp).html" \
    --yaml

echo ""
print_success "Monitoring complete"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💡 Key Features:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. FRAME BUFFERING"
echo "   Frames are captured independently of AI processing"
echo "   If AI is slow, frames wait in buffer instead of being skipped"
echo ""
echo "2. ADAPTIVE RATE"
echo "   More activity → faster capture (min_interval)"
echo "   Less activity → slower capture (max_interval)"
echo ""
echo "3. REGION UPSCALING"
echo "   Small regions are upscaled before AI analysis"
echo "   Better accuracy on distant objects"
echo ""
