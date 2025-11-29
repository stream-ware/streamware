#!/usr/bin/env python3
"""
Smart Security System - Full Integration Example

This example demonstrates:
1. Camera discovery on network
2. Quick motion detection (no AI)
3. Smart buffered monitoring with AI
4. Alert integration (Slack, Telegram)
5. HTML report generation
6. Zone-based monitoring
7. Two-stage detection pipeline

Usage:
    python smart_security_system.py --demo discovery    # Find cameras
    python smart_security_system.py --demo quick        # Quick diff check
    python smart_security_system.py --demo smart        # Smart monitoring
    python smart_security_system.py --demo zones        # Zone monitoring
    python smart_security_system.py --demo pipeline     # Full pipeline
    python smart_security_system.py --help              # Show help

Requirements:
    - streamware
    - ollama with llava:13b
    - ffmpeg
    - Pillow, numpy
"""

import argparse
import sys
import time
import json
from datetime import datetime
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from streamware.core import flow
from streamware.helpers import (
    find_cameras, scan_network, send_alert, 
    generate_report, log_event
)
from streamware.components import (
    smart_monitor, quick_watch, monitor_zones,
    detect_motion, analyze_motion
)


def demo_discovery():
    """Demo 1: Discover cameras on network"""
    print("\n" + "="*60)
    print("📷 Demo: Camera Discovery")
    print("="*60 + "\n")
    
    print("Scanning network for cameras...")
    cameras = find_cameras()
    
    if not cameras:
        print("No cameras found on network")
        return
    
    print(f"\nFound {len(cameras)} camera(s):\n")
    
    for cam in cameras:
        ip = cam.get('ip', 'unknown')
        vendor = cam.get('vendor', 'Unknown')
        rtsp_urls = cam.get('connection', {}).get('rtsp', [])
        
        print(f"  📷 {ip} ({vendor})")
        if rtsp_urls:
            print(f"     RTSP: {rtsp_urls[0][:60]}...")
        print()
    
    return cameras


def demo_quick_check(camera_url: str):
    """Demo 2: Quick pixel diff (no AI)"""
    print("\n" + "="*60)
    print("⚡ Demo: Quick Motion Check (No AI)")
    print("="*60 + "\n")
    
    print(f"Camera: {camera_url[:50]}...")
    print("Duration: 15 seconds")
    print("Mode: Pixel diff only (fast)\n")
    
    result = quick_watch(camera_url, duration=15)
    
    captured = result.get('frames_captured', 0)
    changes = result.get('frames_with_changes', 0)
    
    print(f"Frames captured: {captured}")
    print(f"Frames with changes: {changes}")
    print(f"Status: {'🔴 MOTION DETECTED' if changes > 0 else '✅ STABLE'}")
    
    return result


def demo_smart_monitor(camera_url: str, output_dir: str = "./reports"):
    """Demo 3: Smart buffered monitoring with AI"""
    print("\n" + "="*60)
    print("🎯 Demo: Smart Buffered Monitoring")
    print("="*60 + "\n")
    
    print(f"Camera: {camera_url[:50]}...")
    print("Duration: 30 seconds")
    print("Features:")
    print("  - Frame buffering (capture continues during AI)")
    print("  - Adaptive rate (faster when activity)")
    print("  - Region upscaling (better AI accuracy)")
    print("  - AI analysis on changed regions only")
    print()
    
    result = smart_monitor(
        camera_url,
        duration=30,
        min_interval=1,
        max_interval=5,
        threshold=25,
        focus="person",
        ai=True
    )
    
    # Print results
    captured = result.get('frames_captured', 0)
    changes = result.get('frames_with_changes', 0)
    config = result.get('config', {})
    
    print(f"\nResults:")
    print(f"  Frames captured: {captured}")
    print(f"  Frames with changes: {changes}")
    print(f"  Buffer overflows: {result.get('buffer_overflows', 0)}")
    print(f"  Status: {'🔴 MOTION' if changes > 0 else '✅ STABLE'}")
    
    # Show change details
    timeline = result.get('timeline', [])
    change_frames = [f for f in timeline if f.get('type') == 'change']
    
    if change_frames:
        print(f"\nChanges detected:")
        for frame in change_frames[:5]:
            print(f"  Frame {frame.get('frame')}: {frame.get('change_percent')}% change")
            analysis = frame.get('analysis', '')
            if analysis:
                print(f"    → {analysis[:100]}...")
    
    # Save report
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    report_file = f"{output_dir}/smart_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\nReport saved: {report_file}")
    
    return result


def demo_zones(camera_url: str):
    """Demo 4: Zone-based monitoring"""
    print("\n" + "="*60)
    print("🔲 Demo: Zone-Based Monitoring")
    print("="*60 + "\n")
    
    # Define zones (adjust for your camera view)
    zones = "door:0,40,25,60|window:75,30,25,40|desk:25,20,50,60"
    
    print(f"Camera: {camera_url[:50]}...")
    print("Zones defined:")
    print("  🚪 door: left side (0,40) size 25x60")
    print("  🪟 window: right side (75,30) size 25x40")
    print("  🖥️ desk: center (25,20) size 50x60")
    print()
    
    result = monitor_zones(camera_url, zones, duration=30)
    
    captured = result.get('frames_captured', 0)
    changes = result.get('frames_with_changes', 0)
    
    print(f"\nResults:")
    print(f"  Frames: {captured}")
    print(f"  Changes: {changes}")
    
    # Show zone activity
    zones_info = result.get('zones', [])
    if zones_info:
        print(f"\nZones monitored:")
        for z in zones_info:
            print(f"  - {z.get('name')}: ({z.get('x')},{z.get('y')}) {z.get('width')}x{z.get('height')}")
    
    return result


def demo_pipeline(camera_url: str = None, output_dir: str = "./reports"):
    """Demo 5: Full security pipeline"""
    print("\n" + "="*60)
    print("🔒 Demo: Full Security Pipeline")
    print("="*60 + "\n")
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Stage 1: Discovery
    print("Stage 1: 🔍 Camera Discovery")
    print("-" * 40)
    
    cameras = []
    if camera_url:
        cameras = [{'ip': 'manual', 'connection': {'rtsp': [camera_url]}}]
        print(f"  Using provided camera: {camera_url[:50]}...")
    else:
        cameras = find_cameras()
        if cameras:
            print(f"  Found {len(cameras)} camera(s)")
        else:
            print("  No cameras found. Provide --url argument.")
            return
    
    # Stage 2: Quick scan
    print("\nStage 2: ⚡ Quick Motion Scan")
    print("-" * 40)
    
    cameras_with_motion = []
    
    for cam in cameras:
        ip = cam.get('ip', 'unknown')
        rtsp = cam.get('connection', {}).get('rtsp', [])
        if not rtsp:
            continue
        
        url = rtsp[0]
        print(f"  Scanning {ip}...")
        
        try:
            result = quick_watch(url, duration=10)
            changes = result.get('frames_with_changes', 0)
            
            if changes > 0:
                print(f"    🔴 Motion detected ({changes} changes)")
                cameras_with_motion.append((ip, url))
            else:
                print(f"    ✅ Stable")
        except Exception as e:
            print(f"    ⚠️ Error: {e}")
    
    if not cameras_with_motion:
        print("\n✅ No motion detected on any camera")
        return
    
    # Stage 3: Smart analysis
    print(f"\nStage 3: 🎯 Smart Analysis ({len(cameras_with_motion)} cameras)")
    print("-" * 40)
    
    alerts = []
    
    for ip, url in cameras_with_motion:
        print(f"\n  Analyzing {ip}...")
        
        try:
            result = smart_monitor(
                url,
                duration=30,
                min_interval=1,
                max_interval=5,
                threshold=20,
                focus="person"
            )
            
            changes = result.get('frames_with_changes', 0)
            
            if changes > 0:
                # Get summary
                timeline = result.get('timeline', [])
                summaries = [f.get('analysis', '')[:100] for f in timeline if f.get('analysis')]
                summary = summaries[0] if summaries else "Activity detected"
                
                # Save report
                report_file = f"{output_dir}/alert_{ip.replace('.', '_')}_{datetime.now().strftime('%H%M%S')}.json"
                with open(report_file, 'w') as f:
                    json.dump(result, f, indent=2, default=str)
                
                alerts.append({
                    'ip': ip,
                    'changes': changes,
                    'summary': summary,
                    'report': report_file
                })
                
                print(f"    🔴 Confirmed: {changes} changes")
                print(f"    📄 Report: {report_file}")
            else:
                print(f"    ✅ False positive")
                
        except Exception as e:
            print(f"    ⚠️ Error: {e}")
    
    # Stage 4: Alerts
    if alerts:
        print(f"\nStage 4: 🚨 Alerts ({len(alerts)} cameras)")
        print("-" * 40)
        
        for alert in alerts:
            msg = f"🚨 Security Alert!\nCamera: {alert['ip']}\nChanges: {alert['changes']}\nSummary: {alert['summary']}"
            print(f"\n  Alert for {alert['ip']}:")
            print(f"    {alert['summary'][:80]}...")
            
            # Uncomment to send real alerts:
            # send_alert(msg, slack=True, telegram=True)
    
    # Summary
    print("\n" + "="*60)
    print("📊 Pipeline Summary")
    print("="*60)
    print(f"  Cameras scanned: {len(cameras)}")
    print(f"  Motion detected: {len(cameras_with_motion)}")
    print(f"  Confirmed alerts: {len(alerts)}")
    print(f"  Reports: {output_dir}/")
    
    return {'alerts': alerts, 'cameras_with_motion': cameras_with_motion}


def main():
    parser = argparse.ArgumentParser(
        description="Smart Security System - Full Integration Example",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python smart_security_system.py --demo discovery
  python smart_security_system.py --demo quick --url rtsp://camera/live
  python smart_security_system.py --demo smart --url rtsp://camera/live
  python smart_security_system.py --demo zones --url rtsp://camera/live
  python smart_security_system.py --demo pipeline --url rtsp://camera/live
        """
    )
    
    parser.add_argument('--demo', choices=['discovery', 'quick', 'smart', 'zones', 'pipeline'],
                        default='pipeline', help='Demo to run')
    parser.add_argument('--url', '-u', help='Camera RTSP URL')
    parser.add_argument('--output', '-o', default='./reports', help='Output directory')
    
    args = parser.parse_args()
    
    try:
        if args.demo == 'discovery':
            demo_discovery()
        elif args.demo == 'quick':
            if not args.url:
                print("Error: --url required for quick demo")
                return 1
            demo_quick_check(args.url)
        elif args.demo == 'smart':
            if not args.url:
                print("Error: --url required for smart demo")
                return 1
            demo_smart_monitor(args.url, args.output)
        elif args.demo == 'zones':
            if not args.url:
                print("Error: --url required for zones demo")
                return 1
            demo_zones(args.url)
        elif args.demo == 'pipeline':
            demo_pipeline(args.url, args.output)
        
        return 0
        
    except KeyboardInterrupt:
        print("\nInterrupted")
        return 130
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
