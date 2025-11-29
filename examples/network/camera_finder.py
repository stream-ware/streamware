#!/usr/bin/env python3
"""
Camera Finder - Find and analyze cameras on your network

Finds IP cameras, then optionally connects to analyze their streams.

Usage:
    python camera_finder.py                      # Find cameras
    python camera_finder.py --analyze            # Find and analyze first camera
    python camera_finder.py --ip 192.168.1.100   # Analyze specific camera

CLI equivalent:
    sq network find "cameras"
    sq stream rtsp --url rtsp://192.168.1.100/live --mode diff

Related:
    - examples/media-processing/stream_analysis.py
    - streamware/components/stream.py
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from streamware import flow
from streamware.components.network_scan import find_cameras


def find_and_list_cameras(subnet: str = None):
    """Find all cameras on network"""
    print("=" * 60)
    print("📷 CAMERA FINDER")
    print("=" * 60)
    
    result = find_cameras(subnet)
    
    cameras = result.get("devices", [])
    print(f"\nFound {len(cameras)} camera(s) on network")
    print("-" * 60)
    
    for i, cam in enumerate(cameras, 1):
        print(f"\n📷 Camera #{i}")
        print(f"   IP: {cam.get('ip')}")
        print(f"   Hostname: {cam.get('hostname') or 'N/A'}")
        print(f"   MAC: {cam.get('mac') or 'N/A'}")
        print(f"   Vendor: {cam.get('vendor') or 'Unknown'}")
        
        # Suggest RTSP URLs
        ip = cam.get("ip")
        print(f"\n   Possible RTSP URLs:")
        print(f"   - rtsp://{ip}/live")
        print(f"   - rtsp://{ip}:554/stream1")
        print(f"   - rtsp://{ip}:554/h264")
    
    return cameras


def analyze_camera(ip: str, mode: str = "diff", duration: int = 30):
    """Analyze camera stream with AI"""
    print("=" * 60)
    print(f"📷 ANALYZING CAMERA: {ip}")
    print("=" * 60)
    print(f"Mode: {mode}")
    print(f"Duration: {duration}s")
    print("-" * 60)
    
    # Try common RTSP paths
    rtsp_paths = [
        f"rtsp://{ip}/live",
        f"rtsp://{ip}:554/stream1",
        f"rtsp://{ip}:554/h264",
        f"rtsp://{ip}/cam/realmonitor",
    ]
    
    for rtsp_url in rtsp_paths:
        print(f"\n🔄 Trying: {rtsp_url}")
        try:
            result = flow(f"stream://rtsp?url={rtsp_url}&mode={mode}&duration={duration}").run()
            
            if result.get("success"):
                print(f"✅ Connected!")
                print(f"\n📊 Analysis:")
                
                if mode == "diff":
                    for item in result.get("timeline", [])[:5]:
                        if item.get("type") == "change":
                            print(f"   🔵 [{item.get('timestamp')}] {item.get('changes', '')[:100]}")
                else:
                    for frame in result.get("frames", [])[:3]:
                        print(f"   [{frame.get('timestamp')}] {frame.get('description', '')[:100]}")
                
                return result
                
        except Exception as e:
            print(f"   ❌ Failed: {str(e)[:50]}")
            continue
    
    print("\n❌ Could not connect to camera. Try manually with:")
    print(f"   sq stream rtsp --url rtsp://{ip}/YOUR_PATH --mode diff")
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Camera Finder - Find and analyze IP cameras"
    )
    parser.add_argument("--subnet", "-s", help="Subnet to scan")
    parser.add_argument("--analyze", "-a", action="store_true", help="Analyze first found camera")
    parser.add_argument("--ip", help="Analyze specific camera IP")
    parser.add_argument("--mode", "-m", choices=["full", "stream", "diff"], default="diff",
                       help="Analysis mode")
    parser.add_argument("--duration", "-d", type=int, default=30, help="Analysis duration")
    
    args = parser.parse_args()
    
    try:
        if args.ip:
            analyze_camera(args.ip, args.mode, args.duration)
        else:
            cameras = find_and_list_cameras(args.subnet)
            
            if args.analyze and cameras:
                print("\n" + "=" * 60)
                analyze_camera(cameras[0]["ip"], args.mode, args.duration)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
