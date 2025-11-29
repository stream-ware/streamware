#!/usr/bin/env python3
"""
Mouse Control - Clicks, movement, and automation

Related:
    - streamware/components/automation.py
    - docs/v2/guides/VOICE_AUTOMATION_GUIDE.md
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from streamware import flow
from streamware.components.automation import click, type_text


def demo():
    print("=" * 60)
    print("MOUSE CONTROL DEMO")
    print("=" * 60)
    
    examples = [
        ("Click at 100, 200", "automation://click?x=100&y=200"),
        ("Move to 500, 300", "automation://move?x=500&y=300"),
        ("Double click", "automation://click?x=200&y=200&clicks=2"),
        ("Right click", "automation://click?x=200&y=200&button=right"),
    ]
    
    print("\n📋 Available operations:")
    for desc, uri in examples:
        print(f"   {desc}")
        print(f"   └─ {uri}")
    
    print("\n💡 Quick CLI examples:")
    print("   sq auto click --x 100 --y 200")
    print("   sq auto move --x 500 --y 300")
    print("   sq auto screenshot --text /tmp/screen.png")
    
    # Demo click if coordinates provided
    if len(sys.argv) >= 3:
        x, y = int(sys.argv[1]), int(sys.argv[2])
        print(f"\n🖱️ Clicking at ({x}, {y})...")
        result = click(x, y)
        print(f"✅ {result}")


if __name__ == "__main__":
    demo()
