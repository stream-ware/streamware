#!/bin/bash
# =============================================================================
# Full Security Pipeline
# Complete workflow: Discover cameras -> Analyze -> Alert -> Report
# =============================================================================

set -e  # Exit on error

# Configuration
REPORTS_DIR="./security_reports"
ALERTS_FILE="./alerts.log"
CHECK_DURATION=30
CHECK_INTERVAL=10

echo "========================================"
echo "🔒 Full Security Pipeline"
echo "========================================"
echo ""
echo "Duration per camera: ${CHECK_DURATION}s"
echo "Reports directory: $REPORTS_DIR"
echo ""

# Create directories
mkdir -p "$REPORTS_DIR"

# =============================================================================
# Step 1: Discover Cameras
# =============================================================================
echo "========================================"
echo "Step 1: 🔍 Discovering Cameras"
echo "========================================"
echo ""

# Get cameras as JSON
CAMERAS_JSON=$(sq network find "cameras" --json 2>/dev/null)

# Count cameras
CAMERA_COUNT=$(echo "$CAMERAS_JSON" | jq -r '.devices | length')
echo "Found $CAMERA_COUNT camera(s)"
echo ""

if [ "$CAMERA_COUNT" -eq 0 ]; then
    echo "❌ No cameras found. Exiting."
    exit 1
fi

# Show cameras
echo "$CAMERAS_JSON" | jq -r '.devices[] | "  📷 \(.ip) - \(.vendor // "Unknown")"'
echo ""

# =============================================================================
# Step 2: Analyze Each Camera
# =============================================================================
echo "========================================"
echo "Step 2: 🎥 Analyzing Cameras"
echo "========================================"
echo ""

ALERT_COUNT=0

# Process each camera
echo "$CAMERAS_JSON" | jq -r '.devices[] | "\(.ip)|\(.connection.rtsp[0] // "")"' | while IFS='|' read -r IP RTSP_URL; do
    
    if [ -z "$RTSP_URL" ]; then
        echo "⚠️  Skipping $IP - no RTSP URL"
        continue
    fi
    
    echo "📹 Checking $IP..."
    
    # Generate report filename
    REPORT_FILE="$REPORTS_DIR/camera_${IP//./_}_$(date +%Y%m%d_%H%M%S).html"
    
    # Run analysis
    RESULT=$(sq stream rtsp \
        --url "$RTSP_URL" \
        --mode diff \
        --focus person \
        --sensitivity low \
        --duration "$CHECK_DURATION" \
        --interval "$CHECK_INTERVAL" \
        --file "$REPORT_FILE" \
        --json 2>/dev/null || echo '{"significant_changes": 0}')
    
    # Check for activity
    CHANGES=$(echo "$RESULT" | jq -r '.significant_changes // 0')
    
    if [ "$CHANGES" -gt 0 ]; then
        echo "   🔴 ACTIVITY DETECTED: $CHANGES changes"
        echo "   📄 Report: $REPORT_FILE"
        
        # Log alert
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ALERT: Camera $IP - $CHANGES changes - $REPORT_FILE" >> "$ALERTS_FILE"
        
        ALERT_COUNT=$((ALERT_COUNT + 1))
    else
        echo "   ✅ No activity"
    fi
    
    echo ""
done

echo "========================================"
echo "Step 3: 📊 Summary"
echo "========================================"
echo ""
echo "Cameras checked: $CAMERA_COUNT"
echo "Reports saved to: $REPORTS_DIR/"
echo "Alerts logged to: $ALERTS_FILE"
echo ""

# Show recent alerts
if [ -f "$ALERTS_FILE" ]; then
    RECENT_ALERTS=$(tail -5 "$ALERTS_FILE" 2>/dev/null | wc -l)
    if [ "$RECENT_ALERTS" -gt 0 ]; then
        echo "Recent alerts:"
        tail -5 "$ALERTS_FILE"
    fi
fi

echo ""
echo "========================================"
echo "💡 Next Steps:"
echo "========================================"
echo ""
echo "# View reports:"
echo "ls -la $REPORTS_DIR/*.html"
echo ""
echo "# Open latest report:"
echo "xdg-open \$(ls -t $REPORTS_DIR/*.html | head -1)"
echo ""
echo "# Run continuously (every 5 minutes):"
echo "while true; do bash $0; sleep 300; done"
echo ""
