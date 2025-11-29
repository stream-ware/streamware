#!/bin/bash
# =============================================================================
# People Counting Script
# Count people over time and generate statistics
# =============================================================================

# Configuration
CAMERA_URL="${1:-rtsp://admin:admin@192.168.1.100:554/stream}"
DURATION="${2:-300}"  # 5 minutes default
INTERVAL="${3:-30}"   # Check every 30 seconds

echo "========================================"
echo "👥 People Counting"
echo "========================================"
echo ""
echo "Camera: $CAMERA_URL"
echo "Duration: ${DURATION}s ($(($DURATION / 60)) minutes)"
echo "Check interval: ${INTERVAL}s"
echo ""

# Run counting
echo "📊 Counting people..."
echo ""

sq tracking count \
    --url "$CAMERA_URL" \
    --objects person \
    --duration "$DURATION" \
    --interval "$INTERVAL" \
    --yaml

echo ""
echo "========================================"
echo "💡 Usage Examples:"
echo "========================================"
echo ""
echo "# Count for 1 hour:"
echo "sq tracking count --url '...' --duration 3600 --interval 60"
echo ""
echo "# Count people and vehicles:"
echo "sq tracking count --url '...' --objects 'person,vehicle'"
echo ""
echo "# Save to JSON for processing:"
echo "sq tracking count --url '...' --json > occupancy.json"
echo ""
echo "# Get average occupancy:"
echo "sq tracking count --url '...' --json | jq '.statistics.person.avg'"
echo ""
