#!/bin/bash
# =============================================================================
# Network Scanning Script
# Discover all devices on your network
# =============================================================================

echo "========================================"
echo "🌐 Network Scan"
echo "========================================"
echo ""

# Full network scan
echo "🔍 Scanning network..."
echo ""

sq network scan --yaml

echo ""
echo "========================================"
echo "🔎 Device Discovery Examples"
echo "========================================"
echo ""

echo "# Find specific device types:"
echo ""

echo "📷 Cameras:"
sq network find "cameras" --yaml 2>/dev/null | head -15
echo ""

echo "🖨️ Printers:"
sq network find "printers" --yaml 2>/dev/null | head -10
echo ""

echo "🍓 Raspberry Pi:"
sq network find "raspberry pi" --yaml 2>/dev/null | head -10
echo ""

echo "========================================"
echo "💡 More Commands:"
echo "========================================"
echo ""
echo "# Identify specific IP:"
echo "sq network identify --ip 192.168.1.1"
echo ""
echo "# Scan specific subnet:"
echo "sq network scan --subnet 192.168.1.0/24"
echo ""
echo "# Deep scan (more info, slower):"
echo "sq network scan --deep"
echo ""
echo "# Export to JSON:"
echo "sq network scan --json > devices.json"
echo ""
echo "# Find by custom query:"
echo "sq network find 'GPU servers'"
echo "sq network find 'storage devices'"
echo "sq network find 'smart TV'"
echo ""
