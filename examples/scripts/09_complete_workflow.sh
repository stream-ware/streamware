#!/bin/bash
# =============================================================================
# Complete Workflow: Camera Discovery → Analysis → Alert → Report
# End-to-end security monitoring example
# =============================================================================

set -e

echo "========================================"
echo "🚀 Complete Security Workflow"
echo "========================================"
echo ""
echo "This script demonstrates the full workflow:"
echo "  1. Discover cameras on network"
echo "  2. Select first camera"
echo "  3. Analyze for motion"
echo "  4. Generate HTML report"
echo "  5. Display results"
echo ""
echo "Press Enter to start or Ctrl+C to cancel..."
read

# =============================================================================
# Step 1: Discover cameras
# =============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 1: 🔍 Discovering cameras..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

CAMERAS=$(sq network find "cameras" --json 2>/dev/null)
CAMERA_COUNT=$(echo "$CAMERAS" | jq -r '.devices | length')

if [ "$CAMERA_COUNT" -eq 0 ]; then
    echo "❌ No cameras found on network."
    echo ""
    echo "Make sure you have cameras connected and try:"
    echo "  sq network scan --yaml"
    exit 1
fi

echo "Found $CAMERA_COUNT camera(s):"
echo ""
echo "$CAMERAS" | jq -r '.devices[] | "  📷 \(.ip) - \(.vendor // "Unknown")"'
echo ""

# =============================================================================
# Step 2: Select camera
# =============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 2: 📷 Selecting camera..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

CAMERA_IP=$(echo "$CAMERAS" | jq -r '.devices[0].ip')
CAMERA_VENDOR=$(echo "$CAMERAS" | jq -r '.devices[0].vendor // "Unknown"')
RTSP_URL=$(echo "$CAMERAS" | jq -r '.devices[0].connection.rtsp[0] // ""')

if [ -z "$RTSP_URL" ]; then
    echo "❌ No RTSP URL found for camera $CAMERA_IP"
    exit 1
fi

echo "Selected: $CAMERA_IP ($CAMERA_VENDOR)"
echo "RTSP URL: ${RTSP_URL:0:50}..."
echo ""

# =============================================================================
# Step 3: Analyze stream
# =============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 3: 🎥 Analyzing stream (30 seconds)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

REPORT_DIR="./reports"
REPORT_FILE="$REPORT_DIR/security_$(date +%Y%m%d_%H%M%S).html"
mkdir -p "$REPORT_DIR"

echo "Focus: person"
echo "Sensitivity: low"
echo "Duration: 30 seconds"
echo ""

RESULT=$(sq stream rtsp \
    --url "$RTSP_URL" \
    --mode diff \
    --focus person \
    --sensitivity low \
    --duration 30 \
    --interval 10 \
    --file "$REPORT_FILE" \
    --json 2>/dev/null)

CHANGES=$(echo "$RESULT" | jq -r '.significant_changes // 0')
FRAMES=$(echo "$RESULT" | jq -r '.frames_analyzed // 0')

echo ""

# =============================================================================
# Step 4: Display results
# =============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 4: 📊 Results"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ "$CHANGES" -gt 0 ]; then
    echo "🔴 ACTIVITY DETECTED!"
    echo ""
    echo "   Changes: $CHANGES"
    echo "   Frames: $FRAMES"
    echo ""
    
    echo "Timeline:"
    echo "$RESULT" | jq -r '.timeline[] | "   [\(.timestamp)] \(.type)"'
else
    echo "✅ No activity detected"
    echo ""
    echo "   Changes: 0"
    echo "   Frames: $FRAMES"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 5: 📄 Report"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "📂 Report saved: $REPORT_FILE"
echo ""
echo "To view:"
echo "  xdg-open $REPORT_FILE     # Linux"
echo "  open $REPORT_FILE         # macOS"
echo ""

# =============================================================================
# Summary
# =============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Workflow Complete"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Commands used:"
echo "  1. sq network find 'cameras' --json"
echo "  2. sq stream rtsp --url '...' --focus person --file report.html"
echo ""
echo "Run continuously:"
echo "  while true; do"
echo "    sq stream rtsp --url '$RTSP_URL' --mode diff --focus person --duration 60 --yaml"
echo "    sleep 60"
echo "  done"
echo ""
