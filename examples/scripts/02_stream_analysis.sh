#!/bin/bash
# =============================================================================
# Stream Analysis Script
# Analyze camera stream for activity detection
# =============================================================================

# Configuration - change these for your setup
CAMERA_URL="${1:-rtsp://admin:admin@192.168.1.100:554/stream}"
DURATION="${2:-30}"
FOCUS="${3:-person}"

echo "========================================"
echo "🎥 Stream Analysis"
echo "========================================"
echo ""
echo "Camera: $CAMERA_URL"
echo "Duration: ${DURATION}s"
echo "Focus: $FOCUS"
echo ""

# Basic analysis
echo "📊 Running analysis..."
echo ""

sq stream rtsp \
    --url "$CAMERA_URL" \
    --mode diff \
    --focus "$FOCUS" \
    --sensitivity low \
    --duration "$DURATION" \
    --interval 5 \
    --yaml

echo ""
echo "========================================"
echo "💡 More Options:"
echo "========================================"
echo ""
echo "# Different focus targets:"
echo "sq stream rtsp --url '...' --focus person          # Track people"
echo "sq stream rtsp --url '...' --focus vehicle         # Track vehicles"
echo "sq stream rtsp --url '...' --focus animal          # Track animals"
echo "sq stream rtsp --url '...' --focus 'person,vehicle'  # Multiple"
echo ""
echo "# Sensitivity levels:"
echo "sq stream rtsp --url '...' --sensitivity low       # Less false alarms"
echo "sq stream rtsp --url '...' --sensitivity medium    # Balanced"
echo "sq stream rtsp --url '...' --sensitivity high      # Catch everything"
echo ""
echo "# Output formats:"
echo "sq stream rtsp --url '...' --yaml   # YAML (default)"
echo "sq stream rtsp --url '...' --json   # JSON"
echo "sq stream rtsp --url '...' --table  # ASCII table"
echo ""
