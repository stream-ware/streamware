#!/usr/bin/env python3
"""
Smart Camera Monitor - Auto-discover cameras and analyze streams

This example demonstrates chaining multiple Streamware components:
1. Network scan to find cameras
2. Auto-detect vendor and RTSP paths
3. Stream analysis with AI (motion detection, activity recognition)

Usage:
    python smart_camera_monitor.py                    # Find and monitor all cameras
    python smart_camera_monitor.py --vendor reolink   # Filter by vendor
    python smart_camera_monitor.py --alert            # Alert on changes
    python smart_camera_monitor.py --continuous       # Continuous monitoring

CLI equivalent:
    # Step 1: Find cameras
    sq network find "cameras" --yaml
    
    # Step 2: Analyze camera stream
    sq stream rtsp --url "rtsp://admin:admin123@192.168.1.100:554/h264Preview_01_main" --mode diff

Related:
    - examples/network/network_discovery.py
    - examples/media-processing/stream_analysis.py
    - streamware/components/network_scan.py
    - streamware/components/stream.py
"""

import sys
import os
import argparse
import time
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from streamware import flow
from streamware.components.network_scan import find_cameras, find_devices


def discover_cameras(vendor_filter: str = None):
    """Step 1: Discover cameras on network"""
    print("=" * 70)
    print("📷 STEP 1: Discovering cameras on network...")
    print("=" * 70)
    
    result = find_cameras()
    cameras = result.get("devices", [])
    
    print(f"\nFound {len(cameras)} camera(s)")
    
    # Filter by vendor if specified
    if vendor_filter:
        cameras = [c for c in cameras if vendor_filter.lower() in c.get("vendor", "").lower()]
        print(f"Filtered to {len(cameras)} {vendor_filter} camera(s)")
    
    for i, cam in enumerate(cameras, 1):
        print(f"\n  📷 Camera #{i}: {cam.get('ip')}")
        print(f"     Vendor: {cam.get('vendor', 'Unknown')}")
        print(f"     MAC: {cam.get('mac', 'N/A')}")
        
        conn = cam.get("connection", {})
        if conn.get("rtsp"):
            print(f"     RTSP: {conn['rtsp'][0]}")
        if conn.get("default_credentials"):
            print(f"     Credentials: {conn['default_credentials']}")
    
    return cameras


def build_rtsp_url(camera: dict, user: str = None, password: str = None) -> str:
    """Step 2: Build RTSP URL from camera info"""
    conn = camera.get("connection", {})
    ip = camera.get("ip", "")
    
    # Use provided credentials or defaults
    if not user or not password:
        creds = conn.get("default_credentials", "admin/admin").split("/")
        user = creds[0] if len(creds) > 0 else "admin"
        password = creds[1] if len(creds) > 1 else "admin"
    
    # Get RTSP path from vendor info
    rtsp_paths = conn.get("rtsp", [])
    if rtsp_paths:
        # Use first path (main stream)
        path = rtsp_paths[0]
        # Replace placeholders
        if "{user}" in path or "{pass}" in path:
            return path.replace("{user}", user).replace("{pass}", password)
        return path
    
    # Fallback: generic RTSP URL
    return f"rtsp://{user}:{password}@{ip}:554/stream1"


def analyze_camera(camera: dict, mode: str = "diff", duration: int = 30, 
                   interval: int = 5, user: str = None, password: str = None):
    """Step 3: Analyze camera stream with AI"""
    ip = camera.get("ip", "")
    vendor = camera.get("vendor", "Unknown")
    rtsp_url = build_rtsp_url(camera, user, password)
    
    print("\n" + "=" * 70)
    print(f"🎥 STEP 2: Analyzing camera stream")
    print("=" * 70)
    print(f"Camera: {ip} ({vendor})")
    print(f"RTSP: {rtsp_url}")
    print(f"Mode: {mode}")
    print(f"Duration: {duration}s, Interval: {interval}s")
    print("-" * 70)
    
    try:
        result = flow(
            f"stream://rtsp?url={rtsp_url}&mode={mode}&duration={duration}&interval={interval}"
        ).run()
        
        if result.get("success"):
            timeline = result.get("timeline", [])
            changes = result.get("significant_changes", 0)
            
            print(f"\n✅ Analysis complete!")
            print(f"   Frames analyzed: {len(timeline)}")
            print(f"   Significant changes: {changes}")
            
            # Show timeline
            print("\n📊 Timeline:")
            for event in timeline:
                timestamp = event.get("timestamp", "")
                event_type = event.get("type", "")
                icon = "🔵" if event_type == "change" else "⚪"
                
                print(f"   {icon} [{timestamp}] {event_type}")
                if event_type == "change":
                    desc = event.get("changes", "")[:150]
                    print(f"      {desc}...")
            
            return result
        else:
            print(f"❌ Analysis failed")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def monitor_all_cameras(cameras: list, mode: str = "diff", continuous: bool = False,
                        alert_on_change: bool = False, interval: int = 10):
    """Step 3b: Monitor all cameras"""
    print("\n" + "=" * 70)
    print(f"👁️ MONITORING {len(cameras)} CAMERA(S)")
    print("=" * 70)
    
    if continuous:
        print("Mode: Continuous (Ctrl+C to stop)")
    
    try:
        while True:
            for cam in cameras:
                ip = cam.get("ip", "")
                vendor = cam.get("vendor", "Unknown")
                rtsp_url = build_rtsp_url(cam)
                
                print(f"\n📷 Checking {ip} ({vendor})...")
                
                try:
                    # Quick check - just one frame
                    result = flow(
                        f"stream://rtsp?url={rtsp_url}&mode={mode}&duration=5&interval=5"
                    ).run()
                    
                    if result.get("success"):
                        changes = result.get("significant_changes", 0)
                        if changes > 0:
                            print(f"   🔴 ACTIVITY DETECTED!")
                            if alert_on_change:
                                _send_alert(cam, result)
                        else:
                            print(f"   ⚪ No changes")
                    
                except Exception as e:
                    print(f"   ❌ Error: {str(e)[:50]}")
            
            if not continuous:
                break
            
            print(f"\n⏳ Waiting {interval}s before next check...")
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Monitoring stopped")


def _send_alert(camera: dict, result: dict):
    """Send alert on activity (example - extend with email/slack/telegram)"""
    ip = camera.get("ip", "")
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"   📧 Alert: Activity at {ip} on {timestamp}")
    
    # Example: Save alert to file
    alert = {
        "timestamp": timestamp,
        "camera_ip": ip,
        "vendor": camera.get("vendor"),
        "changes": result.get("significant_changes"),
        "timeline": result.get("timeline", [])
    }
    
    with open("camera_alerts.json", "a") as f:
        f.write(json.dumps(alert) + "\n")


def demo_pipeline():
    """Demo: Full pipeline from discovery to analysis"""
    print("=" * 70)
    print("🚀 STREAMWARE: Camera Discovery & Analysis Pipeline")
    print("=" * 70)
    print()
    print("This demo shows how to chain multiple components:")
    print("  1. Network Scan → Find cameras")
    print("  2. Vendor Detection → Get RTSP paths")
    print("  3. Stream Analysis → AI motion detection")
    print()
    
    # Step 1: Find cameras
    cameras = discover_cameras()
    
    if not cameras:
        print("\n❌ No cameras found on network")
        print("\nTry:")
        print("  - Check your network connection")
        print("  - Install nmap: sudo apt-get install nmap")
        return
    
    # Step 2: Analyze first camera
    print("\n" + "=" * 70)
    print("Selecting first camera for analysis...")
    
    camera = cameras[0]
    analyze_camera(camera, mode="diff", duration=30, interval=5)
    
    # Show CLI equivalent
    rtsp_url = build_rtsp_url(camera)
    print("\n" + "=" * 70)
    print("📋 CLI Equivalent:")
    print("=" * 70)
    print(f"""
# Step 1: Find cameras
sq network find "cameras" --yaml

# Step 2: Analyze stream
sq stream rtsp --url "{rtsp_url}" --mode diff --interval 5

# Or use continuous monitoring
sq stream rtsp --url "{rtsp_url}" --mode diff --continuous
""")


def main():
    parser = argparse.ArgumentParser(
        description="Smart Camera Monitor - Discover and analyze cameras",
        epilog="""
Examples:
  python smart_camera_monitor.py                      # Demo pipeline
  python smart_camera_monitor.py --analyze            # Analyze first camera
  python smart_camera_monitor.py --monitor            # Monitor all cameras
  python smart_camera_monitor.py --vendor reolink     # Filter by vendor
  python smart_camera_monitor.py --continuous --alert # Continuous + alerts

CLI equivalent:
  sq network find "cameras" --yaml
  sq stream rtsp --url "rtsp://admin:admin123@192.168.1.100:554/h264Preview_01_main" --mode diff
        """
    )
    parser.add_argument("--analyze", "-a", action="store_true", 
                       help="Analyze first found camera")
    parser.add_argument("--monitor", "-m", action="store_true",
                       help="Monitor all cameras")
    parser.add_argument("--continuous", "-c", action="store_true",
                       help="Continuous monitoring")
    parser.add_argument("--alert", action="store_true",
                       help="Send alerts on activity")
    parser.add_argument("--vendor", "-v", help="Filter by vendor (e.g., reolink, hikvision)")
    parser.add_argument("--user", "-u", help="Camera username")
    parser.add_argument("--password", "-p", help="Camera password")
    parser.add_argument("--duration", "-d", type=int, default=30,
                       help="Analysis duration in seconds")
    parser.add_argument("--interval", "-i", type=int, default=5,
                       help="Interval between frames")
    parser.add_argument("--mode", choices=["full", "stream", "diff"], default="diff",
                       help="Analysis mode")
    parser.add_argument("--ip", help="Analyze specific camera by IP")
    
    args = parser.parse_args()
    
    try:
        if args.ip:
            # Analyze specific camera
            camera = {
                "ip": args.ip,
                "vendor": args.vendor or "Generic",
                "connection": {
                    "rtsp": [f"rtsp://{args.ip}:554/stream1"],
                    "default_credentials": f"{args.user or 'admin'}/{args.password or 'admin'}"
                }
            }
            analyze_camera(camera, args.mode, args.duration, args.interval,
                          args.user, args.password)
            
        elif args.monitor or args.continuous:
            # Monitor mode
            cameras = discover_cameras(args.vendor)
            if cameras:
                monitor_all_cameras(cameras, args.mode, args.continuous, 
                                   args.alert, args.interval)
                
        elif args.analyze:
            # Analyze first camera
            cameras = discover_cameras(args.vendor)
            if cameras:
                analyze_camera(cameras[0], args.mode, args.duration, args.interval,
                              args.user, args.password)
        else:
            # Demo mode
            demo_pipeline()
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n🛑 Stopped")
        return 0
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
