#!/bin/bash
# Quick Voice Keyboard Test

echo "🎤 Voice Keyboard Quick Test"
echo "============================"
echo ""

# Test 1: Type with voice
echo "Test 1: Voice typing"
echo "Command: wpisz hello world"
python3 << 'EOF'
from streamware import flow
result = flow("voice_keyboard://type?command=wpisz hello world").run()
print(f"✓ {result}")
EOF

sleep 1

# Test 2: Press key
echo ""
echo "Test 2: Key press"
echo "Command: naciśnij enter"
python3 << 'EOF'
from streamware import flow
result = flow("voice_keyboard://press?command=naciśnij enter").run()
print(f"✓ {result}")
EOF

echo ""
echo "✅ Quick test complete!"
echo ""
echo "For full demo run:"
echo "  python3 test_voice_keyboard_demo.py"
