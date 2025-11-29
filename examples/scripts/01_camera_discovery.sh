#!/bin/bash
# =============================================================================
# Camera Discovery Script
# Find all cameras on your network and display their RTSP URLs
# =============================================================================

echo "========================================"
echo "📷 Camera Discovery"
echo "========================================"
echo ""

# Find all cameras on network
echo "🔍 Scanning network for cameras..."
echo ""

sq network find "cameras" --yaml

echo ""
echo "========================================"
echo "💡 Tips:"
echo "========================================"
echo ""
echo "# Save results to file:"
echo "sq network find 'cameras' --json > cameras.json"
echo ""
echo "# Get just IPs:"
echo "sq network find 'cameras' --json | jq -r '.devices[].ip'"
echo ""
echo "# Get RTSP URLs:"
echo "sq network find 'cameras' --json | jq -r '.devices[].connection.rtsp[0]'"
echo ""
