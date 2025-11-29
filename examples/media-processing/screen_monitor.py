#!/usr/bin/env python3
"""
Screen Monitor - Real-time screen analysis with AI

Captures screen periodically and uses AI to detect changes,
identify content, and track activity.

Usage:
    python screen_monitor.py                    # Default diff mode
    python screen_monitor.py --mode stream      # Detailed analysis
    python screen_monitor.py --continuous       # Non-stop monitoring

CLI equivalent:
    sq stream screen --mode diff
    sq stream screen --mode stream --interval 3

Use Cases:
    - Activity tracking
    - Productivity monitoring
    - Automated documentation
    - Accessibility descriptions
    - Security monitoring

Related:
    - examples/media-processing/stream_analysis.py
    - streamware/components/stream.py
    - docs/v2/guides/MEDIA_GUIDE.md
"""

import sys
import os
import argparse
import signal
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from streamware import flow
from streamware.components.stream import analyze_screen, watch_screen


def monitor_screen(mode: str = "diff", interval: int = 3, duration: int = 60, output_file: str = None):
    """
    Monitor screen for specified duration
    
    Args:
        mode: Analysis mode (full/stream/diff)
        interval: Seconds between captures
        duration: Total duration
        output_file: Optional file to save results
    """
    print("=" * 60)
    print("SCREEN MONITOR")
    print("=" * 60)
    print(f"Mode: {mode}")
    print(f"Interval: {interval}s")
    print(f"Duration: {duration}s")
    if output_file:
        print(f"Output: {output_file}")
    print("-" * 60)
    
    result = analyze_screen(mode=mode, interval=interval, duration=duration)
    
    if result.get("success"):
        print(f"\n✅ Monitoring complete!")
        print(f"   Frames: {result.get('frames_analyzed')}")
        
        if mode == "diff":
            changes = result.get("significant_changes", 0)
            print(f"   Changes detected: {changes}")
            
            print("\n📊 Activity Timeline:")
            for item in result.get("timeline", []):
                ts = item.get("timestamp")
                if item.get("type") == "change":
                    print(f"   🔵 [{ts}] {item.get('changes', '')[:80]}...")
                else:
                    print(f"   ⚪ [{ts}] No change")
        else:
            print("\n📋 Screen Descriptions:")
            for frame in result.get("frames", []):
                print(f"\n   [{frame.get('timestamp')}]")
                print(f"   {frame.get('description', '')[:150]}...")
        
        if output_file:
            with open(output_file, "w") as f:
                json.dump(result, f, indent=2)
            print(f"\n💾 Saved to: {output_file}")
    
    return result


def continuous_monitor(mode: str = "diff", interval: int = 3, alert_on_change: bool = True):
    """
    Continuous screen monitoring (until Ctrl+C)
    
    Args:
        mode: Analysis mode
        interval: Seconds between captures
        alert_on_change: Print alert on significant changes
    """
    print("=" * 60)
    print("CONTINUOUS SCREEN MONITOR")
    print("=" * 60)
    print(f"Mode: {mode}")
    print(f"Interval: {interval}s")
    print("Press Ctrl+C to stop")
    print("-" * 60)
    
    def signal_handler(sig, frame):
        print("\n\n👋 Monitoring stopped")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    log = []
    
    for result in watch_screen(mode=mode, interval=interval):
        if result.get("type") == "stopped":
            break
        
        ts = result.get("timestamp", datetime.now().strftime("%H:%M:%S"))
        
        if mode == "diff":
            if result.get("type") == "change":
                changes = result.get("changes", "")[:100]
                print(f"\n🔵 [{ts}] CHANGE: {changes}")
                log.append({"timestamp": ts, "type": "change", "changes": changes})
            else:
                print(f"⚪ [{ts}] No change", end="\r")
        else:
            desc = result.get("description", "")[:100]
            print(f"\n📹 [{ts}] {desc}")
            log.append({"timestamp": ts, "description": desc})
    
    return log


def main():
    parser = argparse.ArgumentParser(
        description="Screen Monitor - Real-time screen analysis with AI",
        epilog="""
Examples:
  python screen_monitor.py                     # Quick 1-minute scan
  python screen_monitor.py --mode stream       # Detailed analysis
  python screen_monitor.py --continuous        # Non-stop monitoring
  python screen_monitor.py --duration 300      # 5-minute monitoring
  python screen_monitor.py --output log.json   # Save results

CLI equivalent:
  sq stream screen --mode diff
  sq stream screen --mode stream --duration 60
        """
    )
    parser.add_argument("--mode", "-m", choices=["full", "stream", "diff"], default="diff",
                       help="Analysis mode (default: diff)")
    parser.add_argument("--interval", "-i", type=int, default=3,
                       help="Seconds between captures (default: 3)")
    parser.add_argument("--duration", "-d", type=int, default=60,
                       help="Duration in seconds (default: 60)")
    parser.add_argument("--continuous", "-c", action="store_true",
                       help="Continuous monitoring (Ctrl+C to stop)")
    parser.add_argument("--output", "-o", help="Save results to file")
    
    args = parser.parse_args()
    
    try:
        if args.continuous:
            continuous_monitor(args.mode, args.interval)
        else:
            monitor_screen(args.mode, args.interval, args.duration, args.output)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nRequirements:")
        print("  - scrot (Linux): sudo apt-get install scrot")
        print("  - ffmpeg: sudo apt-get install ffmpeg")
        print("  - ollama pull llava")
        return 1


if __name__ == "__main__":
    sys.exit(main())
