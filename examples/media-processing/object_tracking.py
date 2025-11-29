#!/usr/bin/env python3
"""
Object Tracking Examples - Track people, vehicles, and objects in real-time

This example demonstrates the tracking component capabilities:
1. People counting
2. Vehicle detection  
3. Zone monitoring (entry/exit)
4. Movement tracking

Requirements:
    - RTSP camera or video file
    - Ollama with llava:13b model
    - ffmpeg

Usage:
    python object_tracking.py --demo                    # Run all demos
    python object_tracking.py --count                   # Count people
    python object_tracking.py --track                   # Track movement
    python object_tracking.py --zones                   # Monitor zones
    python object_tracking.py --url rtsp://camera/live  # Custom camera
"""

import sys
import os
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from streamware.helpers import (
    find_cameras, count_people, track_person, detect_objects,
    detect_vehicles, monitor_zone, watch_camera, security_check,
    send_alert, generate_report
)

# ============================================================================
# Demo Functions
# ============================================================================

def demo_find_cameras():
    """Demo 1: Find cameras on network"""
    print("\n" + "=" * 60)
    print("📷 DEMO 1: Find Cameras on Network")
    print("=" * 60)
    
    cameras = find_cameras()
    
    if not cameras:
        print("❌ No cameras found")
        return None
    
    print(f"\nFound {len(cameras)} camera(s):\n")
    
    for i, cam in enumerate(cameras, 1):
        ip = cam.get("ip")
        vendor = cam.get("vendor", "Unknown")
        rtsp = cam.get("connection", {}).get("rtsp", ["N/A"])[0]
        
        print(f"  {i}. {ip} ({vendor})")
        print(f"     RTSP: {rtsp[:60]}...")
    
    return cameras[0] if cameras else None


def demo_count_people(camera_url: str, duration: int = 30):
    """Demo 2: Count people over time"""
    print("\n" + "=" * 60)
    print("👥 DEMO 2: People Counting")
    print("=" * 60)
    print(f"Source: {camera_url}")
    print(f"Duration: {duration}s")
    print("-" * 60)
    
    result = count_people(camera_url, duration, interval=10)
    
    if result.get("success"):
        stats = result.get("statistics", {}).get("person", {})
        timeline = result.get("timeline", [])
        
        print(f"\n📊 Statistics:")
        print(f"   Minimum: {stats.get('min', 0)} people")
        print(f"   Maximum: {stats.get('max', 0)} people")
        print(f"   Average: {stats.get('avg', 0):.1f} people")
        
        print(f"\n📈 Timeline:")
        for t in timeline:
            count = t.get("counts", {}).get("person", 0)
            bar = "█" * count + "░" * (10 - count)
            print(f"   [{t.get('timestamp')}] {bar} {count}")
    
    return result


def demo_track_person(camera_url: str, duration: int = 30):
    """Demo 3: Track person movement"""
    print("\n" + "=" * 60)
    print("🚶 DEMO 3: Person Tracking")
    print("=" * 60)
    print(f"Source: {camera_url}")
    print(f"Duration: {duration}s")
    print("-" * 60)
    
    result = track_person(camera_url, name="Visitor", duration=duration)
    
    if result.get("success"):
        trajectory = result.get("trajectory", [])
        summary = result.get("summary", {})
        
        print(f"\n📍 Trajectory ({len(trajectory)} points):")
        for i, point in enumerate(trajectory[:10]):
            print(f"   Point {i+1}: ({point[0]}, {point[1]})")
        
        if len(trajectory) > 10:
            print(f"   ... and {len(trajectory) - 10} more points")
        
        print(f"\n📊 Summary:")
        for obj in summary.get("objects", []):
            print(f"   {obj['type']}: {obj.get('direction', 'unknown')} direction")
            print(f"   Visible for: {obj.get('frames_visible', 0)} frames")
    
    return result


def demo_detect_objects(camera_url: str, duration: int = 30):
    """Demo 4: Detect various objects"""
    print("\n" + "=" * 60)
    print("🔍 DEMO 4: Object Detection")
    print("=" * 60)
    print(f"Source: {camera_url}")
    print(f"Duration: {duration}s")
    print(f"Detecting: person, vehicle, animal")
    print("-" * 60)
    
    result = detect_objects(camera_url, "person,vehicle,animal", duration)
    
    if result.get("success"):
        summary = result.get("summary", {})
        by_type = summary.get("by_type", {})
        
        print(f"\n📊 Objects Detected:")
        for obj_type, count in by_type.items():
            print(f"   {obj_type}: {count}")
        
        print(f"\n🎯 Detection Timeline:")
        for det in result.get("detections", [])[:5]:
            print(f"   Frame {det.get('frame')}: {det.get('objects_detected')} objects")
    
    return result


def demo_zone_monitoring(camera_url: str, duration: int = 30):
    """Demo 5: Monitor zone entry/exit"""
    print("\n" + "=" * 60)
    print("🚪 DEMO 5: Zone Monitoring")
    print("=" * 60)
    print(f"Source: {camera_url}")
    print(f"Duration: {duration}s")
    print(f"Zone: entrance (0,0 - 50,100)")
    print("-" * 60)
    
    result = monitor_zone(camera_url, "entrance", 0, 0, 50, 100, duration)
    
    if result.get("success"):
        events = result.get("events", [])
        
        print(f"\n📊 Zone Events: {len(events)}")
        for event in events:
            icon = "➡️" if event["type"] == "zone_enter" else "⬅️"
            print(f"   {icon} {event['timestamp']}: {event['object_type']} {event['type']}")
    
    return result


def demo_security_check(camera_url: str, duration: int = 30):
    """Demo 6: Security check with alerts"""
    print("\n" + "=" * 60)
    print("🔒 DEMO 6: Security Check")
    print("=" * 60)
    print(f"Source: {camera_url}")
    print(f"Duration: {duration}s")
    print("-" * 60)
    
    result = security_check(camera_url, duration, alert_on_change=False)
    
    status = result.get("status", "UNKNOWN")
    changes = result.get("changes", 0)
    
    icon = "🔴" if result.get("activity") else "✅"
    print(f"\n{icon} Status: {status}")
    print(f"   Changes detected: {changes}")
    print(f"   Frames analyzed: {result.get('frames', 0)}")
    
    if result.get("activity"):
        print("\n⚠️ Activity detected! Review timeline:")
        for event in result.get("timeline", [])[:3]:
            if event.get("type") == "change":
                print(f"   [{event.get('timestamp')}] {event.get('changes', '')[:100]}...")
    
    return result


def demo_generate_report(camera_url: str, duration: int = 30):
    """Demo 7: Generate HTML report"""
    print("\n" + "=" * 60)
    print("📄 DEMO 7: Generate Report")
    print("=" * 60)
    
    print("Analyzing stream...")
    result = watch_camera(camera_url, focus="person", duration=duration)
    
    report_file = f"tracking_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    generate_report(result, report_file, "Object Tracking Report")
    
    print(f"\n✅ Report saved: {report_file}")
    print(f"   Open in browser to view")
    
    return report_file


# ============================================================================
# CLI Examples
# ============================================================================

def show_cli_examples():
    """Show CLI command examples"""
    print("\n" + "=" * 60)
    print("💻 CLI Examples")
    print("=" * 60)
    
    examples = """
# Find cameras on network
sq network find "cameras" --yaml

# Watch camera for people
sq stream rtsp --url "rtsp://admin:pass@camera/live" --focus person --duration 60

# Count people with report
sq stream rtsp --url "rtsp://camera/live" --focus person --file report.html

# Track specific objects
sq tracking detect --url "rtsp://camera/live" --objects "person,vehicle" --duration 60

# Monitor zone
sq tracking zones --url "rtsp://camera/live" --zones "entrance:0,0,100,200" --duration 300
"""
    print(examples)


def show_python_examples():
    """Show Python code examples"""
    print("\n" + "=" * 60)
    print("🐍 Python Code Examples")
    print("=" * 60)
    
    examples = '''
from streamware.helpers import *

# ===========================================
# Quick one-liners
# ===========================================

# Find all cameras
cameras = find_cameras()

# Count people
result = count_people("rtsp://camera/live", duration=60)
print(f"Average: {result['statistics']['person']['avg']:.1f}")

# Security check with alert
check = security_check("rtsp://camera/live", 30, alert_on_change=True)

# Track person
track = track_person("rtsp://camera/live", name="John", duration=120)

# Generate report
result = watch_camera("rtsp://camera/live", focus="person")
generate_report(result, "report.html")

# ===========================================
# Full monitoring script
# ===========================================

from streamware.helpers import find_cameras, security_check, send_alert

# Find all cameras
cameras = find_cameras()

# Check each camera
for cam in cameras:
    url = cam.get("connection", {}).get("rtsp", [])[0]
    result = security_check(url, 30)
    
    if result["activity"]:
        send_alert(f"Motion on {cam['ip']}", slack=True)
'''
    print(examples)


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Object Tracking Examples",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python object_tracking.py --demo                    # Run all demos
  python object_tracking.py --count                   # Count people
  python object_tracking.py --track                   # Track movement
  python object_tracking.py --zones                   # Monitor zones
  python object_tracking.py --url rtsp://camera/live  # Custom camera
  python object_tracking.py --cli                     # Show CLI examples
  python object_tracking.py --python                  # Show Python examples
        """
    )
    
    parser.add_argument("--demo", action="store_true", help="Run all demos")
    parser.add_argument("--count", action="store_true", help="Demo: Count people")
    parser.add_argument("--track", action="store_true", help="Demo: Track person")
    parser.add_argument("--detect", action="store_true", help="Demo: Detect objects")
    parser.add_argument("--zones", action="store_true", help="Demo: Zone monitoring")
    parser.add_argument("--security", action="store_true", help="Demo: Security check")
    parser.add_argument("--report", action="store_true", help="Demo: Generate report")
    parser.add_argument("--url", help="Camera RTSP URL")
    parser.add_argument("--duration", type=int, default=30, help="Duration in seconds")
    parser.add_argument("--cli", action="store_true", help="Show CLI examples")
    parser.add_argument("--python", action="store_true", help="Show Python examples")
    
    args = parser.parse_args()
    
    # Show examples
    if args.cli:
        show_cli_examples()
        return 0
    
    if args.python:
        show_python_examples()
        return 0
    
    # Get camera URL
    camera_url = args.url
    if not camera_url:
        cam = demo_find_cameras()
        if cam:
            camera_url = cam.get("connection", {}).get("rtsp", [""])[0]
        
        if not camera_url:
            print("\n⚠️ No camera URL. Use --url to specify.")
            return 1
    
    # Run demos
    if args.demo:
        demo_count_people(camera_url, args.duration)
        demo_track_person(camera_url, args.duration)
        demo_detect_objects(camera_url, args.duration)
        demo_zone_monitoring(camera_url, args.duration)
        demo_security_check(camera_url, args.duration)
        demo_generate_report(camera_url, args.duration)
    elif args.count:
        demo_count_people(camera_url, args.duration)
    elif args.track:
        demo_track_person(camera_url, args.duration)
    elif args.detect:
        demo_detect_objects(camera_url, args.duration)
    elif args.zones:
        demo_zone_monitoring(camera_url, args.duration)
    elif args.security:
        demo_security_check(camera_url, args.duration)
    elif args.report:
        demo_generate_report(camera_url, args.duration)
    else:
        # Default: quick security check
        demo_security_check(camera_url, args.duration)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
