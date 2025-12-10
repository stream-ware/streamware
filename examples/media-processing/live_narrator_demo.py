#!/usr/bin/env python3
"""
Live Narrator Demo - Real-time stream description with TTS

This example demonstrates:
1. Continuous stream analysis with AI
2. Text-to-speech narration
3. Trigger-based alerts ("alert when person appears")
4. Change detection to skip stable frames

Usage:
    python live_narrator_demo.py
    python live_narrator_demo.py "rtsp://user:pass@camera/stream"

Requirements:
    pip install streamware
    # For TTS: sudo apt install espeak
"""

import os
import sys
from datetime import datetime

# Example URLs - replace with your camera
EXAMPLE_CAMERAS = [
    "rtsp://admin:admin@192.168.1.100:554/h264Preview_01_main",
    "rtsp://user:pass@192.168.1.100:554/stream",
]


def demo_describe_once(url: str):
    """Describe what's currently visible (single shot)"""
    print("\n" + "="*60)
    print("📸 DESCRIBE ONCE")
    print("="*60)
    
    from streamware.components import describe_now
    
    description = describe_now(url, tts=False)
    
    print(f"\n📝 Description:\n{description}")
    
    return description


def demo_live_narrator(url: str, duration: int = 30, tts: bool = False):
    """Run live narration for specified duration"""
    print("\n" + "="*60)
    print("🎙️ LIVE NARRATOR")
    print("="*60)
    print(f"URL: {url[:50]}...")
    print(f"Duration: {duration}s")
    print(f"TTS: {'ON' if tts else 'OFF'}")
    print()
    
    from streamware.components import live_narrator
    
    result = live_narrator(
        source=url,
        duration=duration,
        tts=tts,
        interval=3,  # Check every 3 seconds
        focus="person activity",  # Focus on people
    )
    
    print("\n📊 Summary:")
    print(f"  - Frames analyzed: {result.get('frames_analyzed', 0)}")
    print(f"  - Descriptions: {result.get('descriptions', 0)}")
    print(f"  - Triggers fired: {result.get('triggers_fired', 0)}")
    
    return result


def demo_trigger_watch(url: str, triggers: list, duration: int = 60):
    """Watch for specific triggers"""
    print("\n" + "="*60)
    print("🎯 TRIGGER WATCH")
    print("="*60)
    print(f"Watching for: {triggers}")
    print(f"Duration: {duration}s")
    print()
    
    from streamware.components import watch_for
    
    result = watch_for(
        source=url,
        conditions=triggers,
        duration=duration,
        tts=True  # Speak alerts
    )
    
    alerts = result.get("alerts", [])
    print(f"\n🔔 Alerts: {len(alerts)}")
    
    for alert in alerts:
        print(f"  [{alert.get('timestamp')}] {alert.get('description', '')[:100]}...")
    
    return result


def demo_person_detector(url: str, duration: int = 120):
    """Watch for people and describe them"""
    print("\n" + "="*60)
    print("👤 PERSON DETECTOR")
    print("="*60)
    print("Will alert when people appear and describe them")
    print()
    
    person_triggers = [
        "person appears",
        "someone enters",
        "person visible",
        "person leaves",
    ]
    
    from streamware.components import watch_for
    
    result = watch_for(
        source=url,
        conditions=person_triggers,
        duration=duration,
        tts=True
    )
    
    return result


def demo_security_monitor(url: str, duration: int = 300):
    """Full security monitoring with triggers"""
    print("\n" + "="*60)
    print("🔒 SECURITY MONITOR")
    print("="*60)
    
    security_triggers = [
        "intruder detected",
        "suspicious activity",
        "person at door",
        "vehicle enters",
        "package delivered",
    ]
    
    print(f"Monitoring for: {security_triggers}")
    print(f"Duration: {duration//60} minutes")
    print()
    
    from streamware.components import watch_for
    
    return watch_for(
        source=url,
        conditions=security_triggers,
        duration=duration,
        tts=True
    )


def main():
    # Get camera URL from argument or use default
    if len(sys.argv) > 1:
        camera_url = sys.argv[1]
    else:
        camera_url = os.environ.get("CAMERA_URL", EXAMPLE_CAMERAS[0])
    
    print("="*60)
    print("🎙️ STREAMWARE - Live Narrator Demo")
    print("="*60)
    print(f"Camera: {camera_url[:50]}...")
    print()
    
    # Check for espeak
    import shutil
    has_tts = shutil.which("espeak") is not None
    if not has_tts:
        print("⚠️ espeak not found - TTS disabled")
        print("   Install: sudo apt install espeak")
    print()
    
    print("Available demos:")
    print("  1. Describe once (single frame)")
    print("  2. Live narrator (continuous)")
    print("  3. Trigger watch (alert on conditions)")
    print("  4. Person detector")
    print("  5. Security monitor (5 min)")
    print("  0. Run all demos")
    print()
    
    try:
        choice = input("Select demo (0-5): ").strip()
    except KeyboardInterrupt:
        print("\nCancelled")
        return
    
    if choice == "1" or choice == "0":
        demo_describe_once(camera_url)
    
    if choice == "2" or choice == "0":
        demo_live_narrator(camera_url, duration=30, tts=has_tts)
    
    if choice == "3" or choice == "0":
        demo_trigger_watch(
            camera_url,
            triggers=["person appears", "movement detected"],
            duration=30
        )
    
    if choice == "4":
        demo_person_detector(camera_url, duration=60)
    
    if choice == "5":
        demo_security_monitor(camera_url, duration=300)
    
    print("\n" + "="*60)
    print("✅ Demo complete")
    print("="*60)


if __name__ == "__main__":
    main()
