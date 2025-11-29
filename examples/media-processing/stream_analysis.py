#!/usr/bin/env python3
"""
Stream Analysis - Real-time video/audio stream analysis

Supported sources:
    - RTSP: Security cameras, IP cameras
    - HLS: Live streams, TV broadcasts
    - YouTube: Live streams and videos
    - Twitch: Live gaming streams
    - Screen: Desktop screen capture
    - Webcam: Local camera capture

Usage:
    # RTSP camera
    python stream_analysis.py rtsp --url rtsp://camera/live --mode diff
    
    # YouTube stream
    python stream_analysis.py youtube --url "https://youtube.com/watch?v=xxx" --mode stream
    
    # Screen capture
    python stream_analysis.py screen --mode diff --interval 2
    
    # Webcam
    python stream_analysis.py webcam --mode stream

CLI equivalent:
    sq stream rtsp --url rtsp://camera/live --mode diff
    sq stream youtube --url "https://youtube.com/watch?v=xxx"
    sq stream screen --mode diff

Related:
    - examples/media-processing/README.md
    - docs/v2/guides/MEDIA_GUIDE.md
    - streamware/components/stream.py
"""

import sys
import os
import json
import argparse
import signal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from streamware import flow
from streamware.components.stream import (
    analyze_stream,
    analyze_screen,
    analyze_youtube,
    watch_screen,
)


def demo_rtsp(url: str, mode: str = "diff", interval: int = 5, duration: int = 30):
    """
    Analyze RTSP stream (security cameras, IP cameras)
    
    CLI equivalent:
        sq stream rtsp --url rtsp://192.168.1.100/live --mode diff
    """
    print("=" * 60)
    print("RTSP STREAM ANALYSIS")
    print("=" * 60)
    print(f"URL: {url}")
    print(f"Mode: {mode}")
    print(f"Interval: {interval}s")
    print(f"Duration: {duration}s")
    print("-" * 60)
    
    result = flow(f"stream://rtsp?url={url}&mode={mode}&interval={interval}&duration={duration}").run()
    
    print_result(result)
    return result


def demo_hls(url: str, mode: str = "diff", interval: int = 5, duration: int = 30):
    """
    Analyze HLS stream (live TV, broadcasts)
    
    CLI equivalent:
        sq stream hls --url https://stream.m3u8 --mode diff
    """
    print("=" * 60)
    print("HLS STREAM ANALYSIS")
    print("=" * 60)
    print(f"URL: {url}")
    
    result = flow(f"stream://hls?url={url}&mode={mode}&interval={interval}&duration={duration}").run()
    
    print_result(result)
    return result


def demo_youtube(url: str, mode: str = "stream", duration: int = 30):
    """
    Analyze YouTube live stream or video
    
    CLI equivalent:
        sq stream youtube --url "https://youtube.com/watch?v=xxx" --mode stream
    """
    print("=" * 60)
    print("YOUTUBE STREAM ANALYSIS")
    print("=" * 60)
    print(f"URL: {url}")
    print(f"Mode: {mode}")
    print("-" * 60)
    
    result = analyze_youtube(url, mode=mode, duration=duration)
    
    print_result(result)
    return result


def demo_twitch(url: str, mode: str = "stream", duration: int = 30):
    """
    Analyze Twitch live stream
    
    CLI equivalent:
        sq stream twitch --url "https://twitch.tv/channel" --mode stream
    """
    print("=" * 60)
    print("TWITCH STREAM ANALYSIS")
    print("=" * 60)
    print(f"URL: {url}")
    
    result = flow(f"stream://twitch?url={url}&mode={mode}&duration={duration}").run()
    
    print_result(result)
    return result


def demo_screen(mode: str = "diff", interval: int = 2, duration: int = 20):
    """
    Analyze screen capture
    
    CLI equivalent:
        sq stream screen --mode diff --interval 2
    """
    print("=" * 60)
    print("SCREEN CAPTURE ANALYSIS")
    print("=" * 60)
    print(f"Mode: {mode}")
    print(f"Interval: {interval}s")
    print(f"Duration: {duration}s")
    print("-" * 60)
    
    result = analyze_screen(mode=mode, interval=interval, duration=duration)
    
    print_result(result)
    return result


def demo_webcam(device: str = "0", mode: str = "stream", interval: int = 3, duration: int = 15):
    """
    Analyze webcam stream
    
    CLI equivalent:
        sq stream webcam --device 0 --mode stream
    """
    print("=" * 60)
    print("WEBCAM ANALYSIS")
    print("=" * 60)
    print(f"Device: {device}")
    print(f"Mode: {mode}")
    print("-" * 60)
    
    result = flow(f"stream://webcam?device={device}&mode={mode}&interval={interval}&duration={duration}").run()
    
    print_result(result)
    return result


def demo_continuous_screen(mode: str = "diff", interval: int = 2):
    """
    Continuous screen monitoring (press Ctrl+C to stop)
    
    CLI equivalent:
        sq stream screen --mode diff --continuous
    """
    print("=" * 60)
    print("CONTINUOUS SCREEN MONITORING")
    print("=" * 60)
    print(f"Mode: {mode}")
    print(f"Interval: {interval}s")
    print("Press Ctrl+C to stop")
    print("-" * 60)
    
    def signal_handler(sig, frame):
        print("\n\n👋 Stopping...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    for result in watch_screen(mode=mode, interval=interval):
        if result.get("type") == "stopped":
            break
        
        timestamp = result.get("timestamp", "?")
        
        if mode == "diff":
            change_type = result.get("type", "unknown")
            if change_type == "change":
                print(f"\n🔵 [{timestamp}] CHANGE DETECTED:")
                print(f"   {result.get('changes', '')[:200]}")
            else:
                print(f"⚪ [{timestamp}] No changes")
        else:
            print(f"\n📹 [{timestamp}]:")
            print(f"   {result.get('description', '')[:200]}")


def print_result(result: dict):
    """Print analysis result"""
    if result.get("success"):
        print(f"\n✅ Analysis complete!")
        print(f"   Frames analyzed: {result.get('frames_analyzed', '?')}")
        
        if "timeline" in result:
            changes = result.get("significant_changes", 0)
            print(f"   Significant changes: {changes}")
            print("\n📊 Timeline:")
            for item in result.get("timeline", [])[:5]:
                icon = "🔵" if item.get("type") == "change" else "⚪"
                print(f"   {icon} [{item.get('timestamp')}] {item.get('changes', item.get('description', ''))[:100]}")
        
        elif "frames" in result:
            print("\n📋 Frames:")
            for frame in result.get("frames", [])[:5]:
                print(f"   [{frame.get('timestamp')}] {frame.get('description', '')[:100]}")
    else:
        print(f"\n❌ Analysis failed: {result}")


def main():
    parser = argparse.ArgumentParser(
        description="Real-time Stream Analysis with AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Sources:
  rtsp      RTSP streams (security cameras)
  hls       HLS/M3U8 streams (live TV)
  youtube   YouTube live streams/videos
  twitch    Twitch live streams
  screen    Desktop screen capture
  webcam    Local webcam

Examples:
  # Security camera
  python stream_analysis.py rtsp --url rtsp://192.168.1.100/live --mode diff
  
  # YouTube
  python stream_analysis.py youtube --url "https://youtube.com/watch?v=xxx"
  
  # Screen monitoring
  python stream_analysis.py screen --mode diff --interval 2
  
  # Continuous screen watch
  python stream_analysis.py screen --continuous

CLI equivalents:
  sq stream rtsp --url rtsp://camera/live --mode diff
  sq stream youtube --url "https://youtube.com/watch?v=xxx"
  sq stream screen --mode diff

Documentation:
  - examples/media-processing/README.md
  - docs/v2/guides/MEDIA_GUIDE.md
        """
    )
    parser.add_argument("source", nargs="?", choices=["rtsp", "hls", "youtube", "twitch", "screen", "webcam"],
                       help="Stream source")
    parser.add_argument("--url", "-u", help="Stream URL")
    parser.add_argument("--mode", "-m", choices=["full", "stream", "diff"], default="diff",
                       help="Analysis mode (default: diff)")
    parser.add_argument("--interval", "-i", type=int, default=5, help="Seconds between captures")
    parser.add_argument("--duration", "-d", type=int, default=30, help="Total duration in seconds")
    parser.add_argument("--device", default="0", help="Webcam device")
    parser.add_argument("--continuous", "-c", action="store_true", help="Continuous monitoring")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    if not args.source:
        print("=" * 60)
        print("STREAM ANALYSIS DEMO")
        print("=" * 60)
        print("\nUsage: python stream_analysis.py <source> [options]")
        print("\nSources:")
        print("  rtsp     - RTSP cameras (--url rtsp://...)")
        print("  hls      - HLS streams (--url https://...m3u8)")
        print("  youtube  - YouTube (--url https://youtube.com/...)")
        print("  twitch   - Twitch (--url https://twitch.tv/...)")
        print("  screen   - Screen capture")
        print("  webcam   - Webcam (--device 0)")
        print("\nModes:")
        print("  full     - Periodic summaries")
        print("  stream   - Frame-by-frame analysis")
        print("  diff     - Track changes (default)")
        print("\nExamples:")
        print("  python stream_analysis.py screen --mode diff")
        print("  python stream_analysis.py youtube --url 'https://...' --mode stream")
        print("\nCLI equivalent:")
        print("  sq stream screen --mode diff")
        return 1
    
    try:
        if args.source == "rtsp":
            if not args.url:
                print("❌ RTSP URL required: --url rtsp://...")
                return 1
            result = demo_rtsp(args.url, args.mode, args.interval, args.duration)
            
        elif args.source == "hls":
            if not args.url:
                print("❌ HLS URL required: --url https://...m3u8")
                return 1
            result = demo_hls(args.url, args.mode, args.interval, args.duration)
            
        elif args.source == "youtube":
            if not args.url:
                print("❌ YouTube URL required: --url https://youtube.com/...")
                return 1
            result = demo_youtube(args.url, args.mode, args.duration)
            
        elif args.source == "twitch":
            if not args.url:
                print("❌ Twitch URL required: --url https://twitch.tv/...")
                return 1
            result = demo_twitch(args.url, args.mode, args.duration)
            
        elif args.source == "screen":
            if args.continuous:
                demo_continuous_screen(args.mode, args.interval)
                return 0
            result = demo_screen(args.mode, args.interval, args.duration)
            
        elif args.source == "webcam":
            result = demo_webcam(args.device, args.mode, args.interval, args.duration)
        
        if args.json:
            print("\n" + json.dumps(result, indent=2))
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nRequirements:")
        print("  - ffmpeg (all sources)")
        print("  - yt-dlp (YouTube)")
        print("  - streamlink (Twitch)")
        print("  - scrot (screen capture on Linux)")
        print("  - ollama pull llava (AI analysis)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
