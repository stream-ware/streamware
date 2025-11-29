#!/usr/bin/env python3
"""
Security Pipeline - Network scan + Camera monitoring + Alerts

Complete security monitoring pipeline using multiple Streamware components:
1. NetworkScanComponent - Discover cameras
2. StreamComponent - Analyze video streams  
3. SlackComponent/TelegramComponent - Send alerts (optional)
4. FileComponent - Log events

Usage:
    python security_pipeline.py                    # Quick scan + analysis
    python security_pipeline.py --watch            # Continuous monitoring
    python security_pipeline.py --slack-webhook URL # Send alerts to Slack

CLI equivalent pipeline:
    sq network find "cameras" --json | jq -r '.devices[].ip' | \\
    while read ip; do
        sq stream rtsp --url "rtsp://admin:admin123@$ip:554/h264Preview_01_main" --mode diff
    done

Related:
    - examples/network/smart_camera_monitor.py
    - streamware/components/network_scan.py
    - streamware/components/stream.py
    - streamware/components/slack.py
"""

import sys
import os
import argparse
import time
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from streamware import flow
from streamware.components.network_scan import find_cameras, scan_network


class SecurityPipeline:
    """Complete security monitoring pipeline"""
    
    def __init__(self, slack_webhook: str = None, log_file: str = "security_log.json"):
        self.slack_webhook = slack_webhook
        self.log_file = log_file
        self.cameras = []
        self.events = []
    
    def discover_devices(self):
        """Phase 1: Network discovery"""
        print("=" * 70)
        print("🔍 PHASE 1: Network Discovery")
        print("=" * 70)
        
        # Full network scan
        result = scan_network()
        total = result.get("total_devices", 0)
        by_type = result.get("by_type", {})
        
        print(f"\n📊 Network Summary:")
        print(f"   Total devices: {total}")
        for dtype, devices in by_type.items():
            icon = self._get_icon(dtype)
            print(f"   {icon} {dtype}: {len(devices)}")
        
        # Get cameras
        self.cameras = by_type.get("camera", [])
        print(f"\n📷 Found {len(self.cameras)} camera(s) for monitoring")
        
        for cam in self.cameras:
            ip = cam.get("ip")
            vendor = cam.get("vendor", "Unknown")
            conn = cam.get("connection", {})
            rtsp = conn.get("rtsp", ["N/A"])[0] if conn else "N/A"
            
            print(f"   • {ip} ({vendor})")
            print(f"     RTSP: {rtsp[:60]}...")
        
        return self.cameras
    
    def analyze_cameras(self, duration: int = 30, interval: int = 5, mode: str = "diff"):
        """Phase 2: Camera analysis"""
        print("\n" + "=" * 70)
        print("🎥 PHASE 2: Camera Analysis")
        print("=" * 70)
        
        results = []
        
        for i, cam in enumerate(self.cameras, 1):
            ip = cam.get("ip")
            vendor = cam.get("vendor", "Unknown")
            conn = cam.get("connection", {})
            
            print(f"\n[{i}/{len(self.cameras)}] Analyzing {ip} ({vendor})...")
            
            # Build RTSP URL
            rtsp_url = self._build_rtsp_url(cam)
            
            try:
                result = flow(
                    f"stream://rtsp?url={rtsp_url}&mode={mode}&duration={duration}&interval={interval}"
                ).run()
                
                if result.get("success"):
                    changes = result.get("significant_changes", 0)
                    frames = len(result.get("timeline", []))
                    
                    status = "🔴 ACTIVITY" if changes > 0 else "⚪ No activity"
                    print(f"   {status} ({frames} frames, {changes} changes)")
                    
                    # Log event
                    event = {
                        "timestamp": datetime.now().isoformat(),
                        "camera_ip": ip,
                        "vendor": vendor,
                        "changes": changes,
                        "frames": frames,
                        "status": "activity" if changes > 0 else "normal"
                    }
                    self.events.append(event)
                    results.append(result)
                    
                    # Send alert if activity detected
                    if changes > 0:
                        self._send_alert(cam, result)
                else:
                    print(f"   ❌ Analysis failed")
                    
            except Exception as e:
                print(f"   ❌ Error: {str(e)[:50]}")
        
        return results
    
    def continuous_watch(self, interval: int = 60):
        """Phase 3: Continuous monitoring"""
        print("\n" + "=" * 70)
        print("👁️ PHASE 3: Continuous Monitoring")
        print("=" * 70)
        print("Press Ctrl+C to stop\n")
        
        cycle = 0
        try:
            while True:
                cycle += 1
                print(f"\n--- Cycle #{cycle} ({datetime.now().strftime('%H:%M:%S')}) ---")
                
                for cam in self.cameras:
                    ip = cam.get("ip")
                    vendor = cam.get("vendor", "Unknown")
                    rtsp_url = self._build_rtsp_url(cam)
                    
                    try:
                        # Quick check - single frame comparison
                        result = flow(
                            f"stream://rtsp?url={rtsp_url}&mode=diff&duration=10&interval=10"
                        ).run()
                        
                        if result.get("success"):
                            changes = result.get("significant_changes", 0)
                            icon = "🔴" if changes > 0 else "⚪"
                            print(f"  {icon} {ip}: {'ACTIVITY' if changes else 'quiet'}")
                            
                            if changes > 0:
                                self._send_alert(cam, result)
                                
                    except Exception as e:
                        print(f"  ❌ {ip}: {str(e)[:30]}")
                
                # Save log periodically
                self._save_log()
                
                print(f"\n⏳ Next check in {interval}s...")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Monitoring stopped")
            self._save_log()
    
    def generate_report(self):
        """Generate summary report"""
        print("\n" + "=" * 70)
        print("📋 SECURITY REPORT")
        print("=" * 70)
        
        if not self.events:
            print("No events recorded")
            return
        
        activity_count = sum(1 for e in self.events if e["status"] == "activity")
        normal_count = len(self.events) - activity_count
        
        print(f"\n📊 Summary:")
        print(f"   Total checks: {len(self.events)}")
        print(f"   Activity detected: {activity_count}")
        print(f"   Normal: {normal_count}")
        
        print(f"\n📷 By Camera:")
        camera_stats = {}
        for event in self.events:
            ip = event["camera_ip"]
            if ip not in camera_stats:
                camera_stats[ip] = {"activity": 0, "normal": 0, "vendor": event.get("vendor")}
            if event["status"] == "activity":
                camera_stats[ip]["activity"] += 1
            else:
                camera_stats[ip]["normal"] += 1
        
        for ip, stats in camera_stats.items():
            vendor = stats.get("vendor", "Unknown")
            print(f"   {ip} ({vendor}): {stats['activity']} activity, {stats['normal']} normal")
        
        print(f"\n📁 Log saved to: {self.log_file}")
    
    def _build_rtsp_url(self, camera: dict) -> str:
        """Build RTSP URL from camera info"""
        conn = camera.get("connection", {})
        ip = camera.get("ip", "")
        
        rtsp_paths = conn.get("rtsp", [])
        if rtsp_paths:
            return rtsp_paths[0]
        
        creds = conn.get("default_credentials", "admin/admin").split("/")
        user = creds[0] if len(creds) > 0 else "admin"
        password = creds[1] if len(creds) > 1 else "admin"
        
        return f"rtsp://{user}:{password}@{ip}:554/stream1"
    
    def _send_alert(self, camera: dict, result: dict):
        """Send alert notification"""
        ip = camera.get("ip")
        vendor = camera.get("vendor", "Unknown")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        changes = result.get("significant_changes", 0)
        
        message = f"🚨 Activity detected!\n📷 Camera: {ip} ({vendor})\n⏰ Time: {timestamp}\n📊 Changes: {changes}"
        
        print(f"   📧 Alert sent: {ip}")
        
        # Send to Slack if configured
        if self.slack_webhook:
            try:
                import requests
                requests.post(self.slack_webhook, json={"text": message}, timeout=5)
            except Exception as e:
                print(f"   ⚠️ Slack alert failed: {e}")
    
    def _save_log(self):
        """Save events to log file"""
        try:
            with open(self.log_file, "w") as f:
                json.dump({
                    "generated": datetime.now().isoformat(),
                    "cameras": len(self.cameras),
                    "events": self.events
                }, f, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to save log: {e}")
    
    def _get_icon(self, device_type: str) -> str:
        icons = {
            "camera": "📷", "printer": "🖨️", "router": "📡",
            "nas": "💾", "smart_tv": "📺", "iot_device": "🏠",
            "gpu_server": "🎮", "server": "🖥️", "raspberry_pi": "🍓",
            "unknown": "❓"
        }
        return icons.get(device_type, "❓")


def main():
    parser = argparse.ArgumentParser(
        description="Security Pipeline - Complete camera monitoring solution"
    )
    parser.add_argument("--watch", "-w", action="store_true",
                       help="Continuous monitoring mode")
    parser.add_argument("--interval", "-i", type=int, default=60,
                       help="Check interval for watch mode (seconds)")
    parser.add_argument("--duration", "-d", type=int, default=30,
                       help="Analysis duration per camera")
    parser.add_argument("--slack-webhook", help="Slack webhook URL for alerts")
    parser.add_argument("--log", default="security_log.json",
                       help="Log file path")
    
    args = parser.parse_args()
    
    # Create pipeline
    pipeline = SecurityPipeline(
        slack_webhook=args.slack_webhook,
        log_file=args.log
    )
    
    try:
        # Phase 1: Discover
        cameras = pipeline.discover_devices()
        
        if not cameras:
            print("\n❌ No cameras found. Exiting.")
            return 1
        
        if args.watch:
            # Continuous monitoring
            pipeline.continuous_watch(args.interval)
        else:
            # Single analysis
            pipeline.analyze_cameras(args.duration)
        
        # Generate report
        pipeline.generate_report()
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n🛑 Stopped")
        pipeline.generate_report()
        return 0


if __name__ == "__main__":
    sys.exit(main())
