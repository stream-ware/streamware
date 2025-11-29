#!/bin/bash
# Install all dependencies for VSCode Bot

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Installing VSCode Bot Dependencies                  ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# 1. System packages
echo -e "${YELLOW}=== Installing System Packages ===${NC}"
sudo apt-get update -qq
sudo apt-get install -y -qq gnome-screenshot scrot imagemagick xclip xdotool
echo -e "${GREEN}✓ System packages installed${NC}"

# 2. Python packages
echo ""
echo -e "${YELLOW}=== Installing Python Packages ===${NC}"

# Upgrade pip first
python3 -m pip install --upgrade pip -q

# Install Pillow with correct version
python3 -m pip install "Pillow>=9.2.0" -q
echo -e "${GREEN}✓ Pillow installed${NC}"

# Install pyautogui stack
python3 -m pip install pyscreeze pyautogui -q
echo -e "${GREEN}✓ PyAutoGUI installed${NC}"

# Install optional voice
python3 -m pip install SpeechRecognition pyttsx3 -q 2>/dev/null || echo "⚠️  Voice packages optional"

# Install media
python3 -m pip install opencv-python -q 2>/dev/null || echo "⚠️  OpenCV optional"

# 3. Fix X11
echo ""
echo -e "${YELLOW}=== Fixing X11 Permissions ===${NC}"
export DISPLAY=:0
xhost +local: 2>/dev/null && echo -e "${GREEN}✓ X11 permissions set${NC}" || echo -e "${YELLOW}⚠️  X11 fix failed (run in graphical session)${NC}"

# 4. Test installation
echo ""
echo -e "${YELLOW}=== Testing Installation ===${NC}"

python3 << 'EOF'
import sys

# Test pyautogui
try:
    import pyautogui
    print("✓ pyautogui imported")
except Exception as e:
    print(f"✗ pyautogui error: {e}")
    sys.exit(1)

# Test Pillow
try:
    from PIL import Image
    print("✓ Pillow imported")
except Exception as e:
    print(f"✗ Pillow error: {e}")
    sys.exit(1)

# Test pyscreeze
try:
    import pyscreeze
    print("✓ pyscreeze imported")
except Exception as e:
    print(f"✗ pyscreeze error: {e}")
    sys.exit(1)

# Test screenshot capability
try:
    # This will work if gnome-screenshot is installed
    import subprocess
    result = subprocess.run(['which', 'gnome-screenshot'], capture_output=True)
    if result.returncode == 0:
        print("✓ gnome-screenshot available")
    else:
        result = subprocess.run(['which', 'scrot'], capture_output=True)
        if result.returncode == 0:
            print("✓ scrot available")
        else:
            print("⚠️  No screenshot tool found")
except:
    print("⚠️  Could not check screenshot tools")

print("\n✓ All critical dependencies installed!")
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              ✓ Installation Complete!                   ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Now you can use:${NC}"
    echo "  sq bot continue_work --iterations 5"
    echo "  sq auto screenshot --text test.png"
    echo "  sq auto click --x 100 --y 200"
else
    echo ""
    echo -e "${RED}✗ Installation failed!${NC}"
    echo "Please check the errors above"
    exit 1
fi
