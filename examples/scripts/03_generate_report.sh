#!/bin/bash
# =============================================================================
# Generate HTML Report with Images
# Creates detailed report with captured frames
# =============================================================================

# Configuration
CAMERA_URL="${1:-rtsp://admin:admin@192.168.1.100:554/stream}"
DURATION="${2:-60}"
REPORTS_DIR="${3:-./reports}"
REPORT_NAME="camera_report_$(date +%Y%m%d_%H%M%S).html"

echo "========================================"
echo "📄 Generate HTML Report"
echo "========================================"
echo ""
echo "Camera: $CAMERA_URL"
echo "Duration: ${DURATION}s"
echo "Output: $REPORTS_DIR/$REPORT_NAME"
echo ""

# Create reports directory
mkdir -p "$REPORTS_DIR"

# Run analysis and save report
echo "📊 Analyzing stream and generating report..."
echo ""

sq stream rtsp \
    --url "$CAMERA_URL" \
    --mode diff \
    --focus person \
    --sensitivity low \
    --duration "$DURATION" \
    --interval 10 \
    --file "$REPORTS_DIR/$REPORT_NAME" \
    --yaml

echo ""
echo "========================================"
echo "✅ Report Generated"
echo "========================================"
echo ""
echo "📂 Location: $REPORTS_DIR/$REPORT_NAME"
echo ""
echo "# Open report in browser:"
echo "xdg-open $REPORTS_DIR/$REPORT_NAME    # Linux"
echo "open $REPORTS_DIR/$REPORT_NAME        # macOS"
echo ""
echo "# List all reports:"
echo "ls -la $REPORTS_DIR/*.html"
echo ""
