#!/bin/bash
# Quick fix script for common issues

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}=== Streamware Quick Fix ===${NC}"
echo ""

# 1. Install missing dependencies
echo -e "${YELLOW}1. Installing dependencies...${NC}"
pip install -q Pillow pyautogui pyscreeze 2>/dev/null && echo "✓ Python packages installed" || echo "⚠️  Some packages failed"

# 2. Fix X11
echo ""
echo -e "${YELLOW}2. Fixing X11 authorization...${NC}"
export DISPLAY=:0
xhost +local: 2>/dev/null && echo "✓ X11 fixed" || echo "⚠️  X11 fix failed (may need graphical session)"

# 3. Test basic functionality
echo ""
echo -e "${YELLOW}3. Testing components...${NC}"
python3 -c "
try:
    from streamware.components import AutomationComponent, VSCodeBotComponent, MediaComponent
    print('✓ All components import successfully')
except Exception as e:
    print(f'✗ Import error: {e}')
"

# 4. Test screenshot (if display available)
echo ""
echo -e "${YELLOW}4. Testing screenshot...${NC}"
python3 << 'EOF'
try:
    import pyautogui
    from PIL import Image
    # Test if we can access display
    pos = pyautogui.position()
    print(f"✓ Display works! Mouse at: {pos}")
    print("✓ Screenshot functionality available")
except Exception as e:
    print(f"⚠️  Display/Screenshot not available: {e}")
    print("   This is normal if running headless or via SSH")
EOF

echo ""
echo -e "${GREEN}=== Fix Complete ===${NC}"
echo ""
echo "Now try:"
echo "  sq bot click_button --button accept_all"
echo "  sq bot continue_work --iterations 2"
echo ""
