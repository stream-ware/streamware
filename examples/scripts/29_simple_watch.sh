#!/bin/bash
# =============================================================================
# Simple Watch - Intuitive parameters
# Uses qualitative settings instead of numeric values
# =============================================================================

source "$(dirname "$0")/common.sh"

print_header "🎯 Simple Watch (Qualitative Parameters)"

CAMERA_URL="${1:-$CAMERA_URL}"
DETECT="${2:-person}"
SENSITIVITY="${3:-high}"
ensure_camera_url

print_step "Intuitive vs Technical parameters"
echo ""
echo "❌ OLD WAY (technical):"
echo "   sq motion --threshold 8 --min-region 50 --interval 2"
echo ""
echo "✅ NEW WAY (intuitive):"
echo "   sq watch --detect person --sensitivity high --speed fast"
echo ""

print_step "Available options:"
echo ""
echo "Sensitivity: ultra, high, medium, low, minimal"
echo "Detect: person, people, vehicle, animal, package, motion, any"
echo "Speed: realtime, fast, normal, slow, thorough"
echo "Alert: none, log, sound, speak, slack, telegram"
echo ""

print_step "Watching with: detect=$DETECT, sensitivity=$SENSITIVITY"
echo ""

sq watch \
    --url "$CAMERA_URL" \
    --detect "$DETECT" \
    --sensitivity "$SENSITIVITY" \
    --speed fast \
    --duration "${DURATION:-30}"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💡 Quick examples:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "# Watch for person with high sensitivity:"
echo "sq watch --url \"\$URL\" --detect person --sensitivity high"
echo ""
echo "# Watch for vehicle, send Slack alert:"
echo "sq watch --url \"\$URL\" --detect vehicle --alert slack"
echo ""
echo "# Watch for any motion, speak alerts:"
echo "sq watch --url \"\$URL\" --detect motion --sensitivity ultra --alert speak"
echo ""
echo "# Realtime motion detection (high CPU):"
echo "sq watch --url \"\$URL\" --detect motion --speed realtime"
echo ""
