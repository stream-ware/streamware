#!/bin/bash
# =============================================================================
# Zone-Based Security Monitoring
# Define specific zones to watch (door, window, parking, etc.)
# =============================================================================

source "$(dirname "$0")/common.sh"

print_header "🔲 Zone-Based Security"

CAMERA_URL="${1:-$CAMERA_URL}"
ensure_camera_url

setup_dirs

# Define zones (name:x,y,width,height in 0-100 scale)
# Adjust these for your camera view!
DOOR_ZONE="${DOOR_ZONE:-door:0,40,25,60}"
WINDOW_ZONE="${WINDOW_ZONE:-window:75,30,25,40}"
PARKING_ZONE="${PARKING_ZONE:-parking:30,60,40,40}"

ALL_ZONES="$DOOR_ZONE|$WINDOW_ZONE|$PARKING_ZONE"

print_step "🗺️ Zone Configuration"
echo ""
echo "Zones defined (0-100 coordinate scale):"
echo "  🚪 Door:    $DOOR_ZONE"
echo "  🪟 Window:  $WINDOW_ZONE"
echo "  🚗 Parking: $PARKING_ZONE"
echo ""
echo "┌────────────────────────────────────────┐"
echo "│            Camera View                 │"
echo "│  ┌─────┐              ┌─────┐          │"
echo "│  │Door │              │ Win │          │"
echo "│  │     │              │     │          │"
echo "│  └─────┘              └─────┘          │"
echo "│         ┌────────────┐                 │"
echo "│         │  Parking   │                 │"
echo "│         └────────────┘                 │"
echo "└────────────────────────────────────────┘"
echo ""

print_step "👁️ Monitoring zones..."

sq smart zones \
    --url "$CAMERA_URL" \
    --zones "$ALL_ZONES" \
    --threshold 20 \
    --min-interval 1 \
    --max-interval 5 \
    --focus "person,vehicle" \
    --duration "$DURATION" \
    --file "$REPORTS_DIR/zones_$(get_file_timestamp).html" \
    --yaml

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💡 Customize Zones in .env:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "# Zone format: name:x,y,width,height (0-100 scale)"
echo 'DOOR_ZONE="door:0,40,25,60"'
echo 'WINDOW_ZONE="window:75,30,25,40"'
echo 'PARKING_ZONE="parking:30,60,40,40"'
echo ""
echo "# Custom zones for your setup:"
echo 'CUSTOM_ZONES="entrance:0,0,100,30|backyard:0,70,100,30"'
echo ""
