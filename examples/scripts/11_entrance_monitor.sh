#!/bin/bash
# =============================================================================
# Entrance Monitor Script
# Monitor entrance/exit with zone detection
# =============================================================================

source "$(dirname "$0")/common.sh"

print_header "🚪 Entrance Monitor"

# Zone configuration (adjust for your camera view)
# Format: name:x,y,width,height (coordinates 0-100 scale)
ENTRANCE_ZONE="${ENTRANCE_ZONE:-entrance:0,30,30,40}"
EXIT_ZONE="${EXIT_ZONE:-exit:70,30,30,40}"
ZONES="$ENTRANCE_ZONE|$EXIT_ZONE"

# Use camera URL from .env or argument
CAMERA_URL="${1:-$CAMERA_URL}"
ensure_camera_url

show_config

echo "Zones configured:"
echo "  Entrance: $ENTRANCE_ZONE"
echo "  Exit: $EXIT_ZONE"
echo ""

setup_dirs

print_step "👁️ Monitoring zones..."

# Run zone monitoring
RESULT=$(sq tracking zones \
    --url "$CAMERA_URL" \
    --zones "$ZONES" \
    --duration "$DURATION" \
    --interval "$INTERVAL" \
    --json 2>/dev/null)

# Parse events
EVENTS=$(echo "$RESULT" | jq -r '.events | length')
ENTRIES=$(echo "$RESULT" | jq -r '[.events[] | select(.type == "zone_enter")] | length')
EXITS=$(echo "$RESULT" | jq -r '[.events[] | select(.type == "zone_exit")] | length')

print_step "📊 Results"

echo "Total events: $EVENTS"
echo "  Entries: $ENTRIES"
echo "  Exits: $EXITS"
echo ""

# Show events timeline
if [ "$EVENTS" -gt 0 ]; then
    echo "Event Timeline:"
    echo "$RESULT" | jq -r '.events[] | "  [\(.timestamp)] \(.object_type) \(.type) \(.zone)"'
    echo ""
fi

# Save results
REPORT_FILE="$REPORTS_DIR/entrance_$(get_file_timestamp).json"
echo "$RESULT" | jq '.' > "$REPORT_FILE"
print_success "Results saved to $REPORT_FILE"

# Alert if entries detected
if [ "$ENTRIES" -gt 0 ]; then
    send_alert "🚪 Entrance activity: $ENTRIES entry(ies), $EXITS exit(s)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💡 Zone Configuration:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Zones use coordinates on 0-100 scale:"
echo "  Top-left: (0,0)"
echo "  Bottom-right: (100,100)"
echo ""
echo "Example zones in .env:"
echo '  ENTRANCE_ZONE="entrance:0,30,30,40"   # Left side'
echo '  EXIT_ZONE="exit:70,30,30,40"          # Right side'
echo ""
