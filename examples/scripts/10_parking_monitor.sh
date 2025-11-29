#!/bin/bash
# =============================================================================
# Parking Monitor Script
# Monitor parking lot for vehicle activity
# =============================================================================

source "$(dirname "$0")/common.sh"

print_header "🚗 Parking Monitor"

# Override focus for vehicles
FOCUS="vehicle"
OBJECTS="car,truck,bike,vehicle"

# Use camera URL from .env or argument
CAMERA_URL="${1:-$CAMERA_URL}"
ensure_camera_url

show_config

setup_dirs

print_step "🔍 Monitoring parking area..."

echo "Detecting: $OBJECTS"
echo "Duration: ${DURATION}s"
echo ""

# Run vehicle detection
RESULT=$(sq tracking detect \
    --url "$CAMERA_URL" \
    --objects "$OBJECTS" \
    --duration "$DURATION" \
    --interval "$INTERVAL" \
    --json 2>/dev/null)

# Parse results
TOTAL=$(echo "$RESULT" | jq -r '.summary.total_objects // 0')
CARS=$(echo "$RESULT" | jq -r '.summary.by_type.car // 0')
TRUCKS=$(echo "$RESULT" | jq -r '.summary.by_type.truck // 0')

print_step "📊 Results"

echo "Total vehicles: $TOTAL"
echo "  Cars: $CARS"
echo "  Trucks: $TRUCKS"
echo ""

# Generate report
REPORT_FILE="$REPORTS_DIR/parking_$(get_file_timestamp).html"
echo "$RESULT" | jq '.' > "$REPORTS_DIR/parking_$(get_file_timestamp).json"

print_success "Results saved to $REPORTS_DIR/"

# Alert if vehicles detected
if [ "$TOTAL" -gt 0 ]; then
    send_alert "🚗 Parking activity: $TOTAL vehicle(s) detected"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💡 Usage:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "# Monitor specific camera:"
echo "./10_parking_monitor.sh 'rtsp://camera/parking'"
echo ""
echo "# Set in .env:"
echo "CAMERA_URL='rtsp://your-parking-camera/stream'"
echo "FOCUS='vehicle'"
echo ""
