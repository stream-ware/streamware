#!/bin/bash
# Quick Fix for X11 Display Issues

echo "🔧 Streamware Automation Quick Fix"
echo "=================================="
echo ""

# Check if running in graphical session
if [ -z "$DISPLAY" ]; then
    echo "❌ DISPLAY not set"
    echo "Setting DISPLAY=:0"
    export DISPLAY=:0
else
    echo "✓ DISPLAY=$DISPLAY"
fi

# Fix X11 authorization
echo ""
echo "Fixing X11 authorization..."
xhost +local: 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ X11 authorization fixed"
else
    echo "⚠️  Could not fix X11 (xhost not available or not in graphical session)"
    echo ""
    echo "If running via SSH, use:"
    echo "  ssh -X user@host"
    echo ""
    echo "If running in terminal:"
    echo "  xhost +local:"
fi

# Test if we can connect to display
echo ""
echo "Testing display connection..."
python3 -c "
try:
    import pyautogui
    pos = pyautogui.position()
    print(f'✓ Display works! Mouse at: {pos}')
except Exception as e:
    print(f'❌ Display test failed: {e}')
    print('')
    print('Solutions:')
    print('1. Run: xhost +local:')
    print('2. Use SSH with: ssh -X user@host')
    print('3. For headless: xvfb-run sq auto ...')
" 2>&1

echo ""
echo "=================================="
echo "Now try:"
echo "  sq auto screenshot --text test.png"
echo "  sq auto click --x 100 --y 200"
echo ""
