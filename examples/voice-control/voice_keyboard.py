#!/usr/bin/env python3
"""
Voice Keyboard - Type with voice commands

Commands:
    "wpisz hello world" -> types "hello world"
    "naciśnij enter" -> presses Enter
    "naciśnij tab" -> presses Tab

Requirements:
    sudo apt-get install xdotool espeak

Related:
    - docs/v2/guides/VOICE_AUTOMATION_GUIDE.md
    - streamware/components/voice_keyboard.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from streamware import flow
from streamware.components.voice_keyboard import voice_type, voice_press, dictate


def demo_typing():
    """Demo voice typing"""
    print("=" * 60)
    print("VOICE KEYBOARD DEMO")
    print("=" * 60)
    
    # Example commands
    commands = [
        ("wpisz hello world", "Types: hello world"),
        ("napisz Python is great", "Types: Python is great"),
        ("naciśnij enter", "Presses: Enter"),
        ("naciśnij tab", "Presses: Tab"),
    ]
    
    for cmd, description in commands:
        print(f"\n🎤 Command: '{cmd}'")
        print(f"📝 {description}")
        
        try:
            if "wpisz" in cmd or "napisz" in cmd:
                result = voice_type(cmd)
            else:
                result = voice_press(cmd)
            print(f"✅ Result: {result}")
        except Exception as e:
            print(f"❌ Error: {e}")


def interactive_mode():
    """Interactive voice typing mode"""
    print("\n" + "=" * 60)
    print("INTERACTIVE MODE")
    print("Say commands or type 'exit' to quit")
    print("=" * 60)
    
    try:
        dictate(iterations=10)
    except KeyboardInterrupt:
        print("\n👋 Exiting...")


def main():
    if "--interactive" in sys.argv or "-i" in sys.argv:
        interactive_mode()
    else:
        demo_typing()
        print("\n💡 Run with --interactive for voice input mode")


if __name__ == "__main__":
    main()
