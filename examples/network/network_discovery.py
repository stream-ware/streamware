#!/usr/bin/env python3
"""
Network Discovery - Scan and find devices on your network

Usage:
    python network_discovery.py                    # Scan local network
    python network_discovery.py --find "cameras"   # Find cameras
    python network_discovery.py --find "raspberry" # Find Raspberry Pi
    python network_discovery.py --subnet 10.0.0.0/24

CLI equivalent:
    sq network scan
    sq network find "cameras"
    sq network find "raspberry pi"

Related:
    - examples/network/README.md
    - streamware/components/network_scan.py
"""

import sys
import os
import argparse
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from streamware import flow
from streamware.components.network_scan import (
    scan_network,
    find_devices,
    find_cameras,
    find_raspberry_pi,
    find_printers,
)


def get_icon(device_type: str) -> str:
    """Get emoji icon for device type"""
    icons = {
        "raspberry_pi": "🍓",
        "camera": "📷",
        "printer": "🖨️",
        "router": "📡",
        "nas": "💾",
        "smart_tv": "📺",
        "iot_device": "🏠",
        "server": "🖥️",
        "unknown": "❓",
    }
    return icons.get(device_type, "❓")


def demo_scan(subnet: str = None):
    """Demo: Full network scan"""
    print("=" * 60)
    print("NETWORK SCAN")
    print("=" * 60)
    
    if subnet:
        result = flow(f"network://scan?subnet={subnet}").run()
    else:
        result = scan_network()
    
    print(f"\n📡 Subnet: {result.get('subnet')}")
    print(f"📊 Total devices: {result.get('total_devices', 0)}")
    print("-" * 60)
    
    for device in result.get("devices", []):
        icon = get_icon(device.get("type", "unknown"))
        print(f"\n{icon} {device.get('ip')}")
        print(f"   Hostname: {device.get('hostname') or 'N/A'}")
        print(f"   MAC: {device.get('mac') or 'N/A'}")
        print(f"   Vendor: {device.get('vendor') or 'Unknown'}")
        print(f"   Type: {device.get('description', 'Unknown Device')}")
    
    print("\n" + "-" * 60)
    print("📊 Summary by type:")
    for dtype, devices in result.get("by_type", {}).items():
        print(f"   {get_icon(dtype)} {dtype}: {len(devices)}")
    
    return result


def demo_find(query: str, subnet: str = None):
    """Demo: Find devices by query"""
    print("=" * 60)
    print(f"SEARCH: '{query}'")
    print("=" * 60)
    
    result = find_devices(query, subnet)
    
    print(f"\n🔍 Query: {query}")
    print(f"📊 Found: {result.get('matched_devices', 0)} / {result.get('total_scanned', 0)} devices")
    print("-" * 60)
    
    if not result.get("devices"):
        print("\n❌ No devices found matching your query.")
        print("\nTry:")
        print("  - 'cameras' for IP cameras")
        print("  - 'raspberry pi' for Raspberry Pi")
        print("  - 'printers' for network printers")
        print("  - 'servers' for servers")
    else:
        for device in result.get("devices", []):
            icon = get_icon(device.get("type", "unknown"))
            print(f"\n{icon} {device.get('ip')}")
            print(f"   Hostname: {device.get('hostname') or 'N/A'}")
            print(f"   MAC: {device.get('mac') or 'N/A'}")
            print(f"   Type: {device.get('description', 'Unknown')}")
    
    return result


def demo_quick_finders():
    """Demo: Quick finder functions"""
    print("=" * 60)
    print("QUICK DEVICE FINDERS")
    print("=" * 60)
    
    # Cameras
    print("\n📷 Searching for cameras...")
    cameras = find_cameras()
    print(f"   Found: {cameras.get('matched_devices', 0)}")
    for cam in cameras.get("devices", [])[:3]:
        print(f"   - {cam['ip']} ({cam.get('hostname', 'N/A')})")
    
    # Raspberry Pi
    print("\n🍓 Searching for Raspberry Pi...")
    rpis = find_raspberry_pi()
    print(f"   Found: {rpis.get('matched_devices', 0)}")
    for rpi in rpis.get("devices", [])[:3]:
        print(f"   - {rpi['ip']} ({rpi.get('hostname', 'N/A')})")
    
    # Printers
    print("\n🖨️ Searching for printers...")
    printers = find_printers()
    print(f"   Found: {printers.get('matched_devices', 0)}")
    for printer in printers.get("devices", [])[:3]:
        print(f"   - {printer['ip']} ({printer.get('hostname', 'N/A')})")


def main():
    parser = argparse.ArgumentParser(
        description="Network Discovery - Find devices on your network",
        epilog="""
Examples:
  python network_discovery.py                    # Full scan
  python network_discovery.py --find "cameras"   # Find cameras
  python network_discovery.py --find "raspberry" # Find Raspberry Pi
  python network_discovery.py --find "printers"  # Find printers
  python network_discovery.py --quick            # Quick finders demo

CLI equivalent:
  sq network scan
  sq network find "cameras"
  sq network find "raspberry pi"
        """
    )
    parser.add_argument("--find", "-f", help="Search query (e.g., 'cameras', 'raspberry pi')")
    parser.add_argument("--subnet", "-s", help="Subnet to scan (default: auto-detect)")
    parser.add_argument("--quick", "-q", action="store_true", help="Run quick finders demo")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    try:
        if args.quick:
            demo_quick_finders()
        elif args.find:
            result = demo_find(args.find, args.subnet)
            if args.json:
                print("\n" + json.dumps(result, indent=2))
        else:
            result = demo_scan(args.subnet)
            if args.json:
                print("\n" + json.dumps(result, indent=2))
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nFor best results, install:")
        print("  sudo apt-get install nmap arp-scan")
        return 1


if __name__ == "__main__":
    sys.exit(main())
