#!/usr/bin/env python3
"""
Voice Mouse - Control mouse with voice + AI vision

How it works:
    1. You say "click on Submit button"
    2. AI takes screenshot
    3. LLaVA finds the button coordinates
    4. Mouse clicks at that position

Requirements:
    sudo apt-get install xdotool scrot
    ollama pull llava

Related:
    - docs/v2/guides/VOICE_MOUSE_GUIDE.md
    - streamware/components/voice_mouse.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from streamware import flow
from streamware.components.voice_mouse import voice_click, listen_and_click


def demo_click():
    """Demo voice-controlled clicking"""
    print("=" * 60)
    print("VOICE MOUSE DEMO")
    print("AI Vision + Voice Control")
    print("=" * 60)
    
    # Example commands
    commands = [
        "kliknij w przycisk OK",
        "click on the close button",
        "kliknij w menu File",
    ]
    
    print("\n📋 Example commands:")
    for cmd in commands:
        print(f"   🎤 '{cmd}'")
    
    print("\n🔄 To test, run with a command:")
    print("   python voice_mouse.py 'click on button OK'")
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        print(f"\n🎯 Executing: {command}")
        try:
            result = voice_click(command)
            print(f"✅ Result: {result}")
        except Exception as e:
            print(f"❌ Error: {e}")


def interactive_mode():
    """Interactive voice mouse mode"""
    print("\n" + "=" * 60)
    print("INTERACTIVE VOICE MOUSE")
    print("Say where to click, AI will find and click!")
    print("=" * 60)
    
    try:
        listen_and_click(iterations=10)
    except KeyboardInterrupt:
        print("\n👋 Exiting...")


def main():
    if "--interactive" in sys.argv or "-i" in sys.argv:
        interactive_mode()
    elif len(sys.argv) > 1 and sys.argv[1] not in ["--help", "-h"]:
        # Direct command
        command = sys.argv[1]
        result = voice_click(command)
        print(result)
    else:
        demo_click()
        print("\n💡 Run with --interactive for continuous mode")


if __name__ == "__main__":
    main()
