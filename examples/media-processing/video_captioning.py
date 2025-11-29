#!/usr/bin/env python3
"""
Video Captioning - Generate descriptions with AI

Three analysis modes:
    - full: Coherent narrative (default)
    - stream: Frame-by-frame details
    - diff: Track changes between frames

Usage:
    python video_captioning.py video.mp4
    python video_captioning.py video.mp4 --mode stream
    python video_captioning.py video.mp4 --mode diff

Requirements:
    ollama pull llava
    sudo apt-get install ffmpeg

Related Documentation:
    - examples/media-processing/README.md - Full mode documentation
    - docs/v2/guides/MEDIA_GUIDE.md - Media processing guide
    - docs/v2/components/QUICK_CLI.md - CLI reference

Related Examples:
    - examples/llm-ai/ - AI text processing
    - examples/voice-control/ - Audio input/output

Source Code:
    - streamware/components/media.py - MediaComponent implementation
"""

import sys
import os
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from streamware import flow


def describe_video(file: str, mode: str = "full", prompt: str = None, model: str = "llava"):
    """
    Describe video content using AI vision.
    
    Args:
        file: Path to video file
        mode: Analysis mode - 'full', 'stream', or 'diff'
        prompt: Custom prompt for AI
        model: Vision model to use (default: llava)
    
    Returns:
        dict: Analysis results based on mode
        
    See Also:
        - examples/media-processing/README.md#video-analysis-modes
        - docs/v2/guides/MEDIA_GUIDE.md
    """
    uri = f"media://describe_video?file={file}&mode={mode}&model={model}"
    if prompt:
        uri += f"&prompt={prompt}"
    
    result = flow(uri).run()
    return result


def demo_full_mode(file: str):
    """
    Demo: Full mode - coherent narrative
    
    Creates a single, coherent description tracking subjects
    through the entire video.
    
    CLI equivalent:
        sq media describe_video --file video.mp4 --mode full
    """
    print("\n" + "=" * 60)
    print("MODE: FULL - Coherent Narrative")
    print("=" * 60)
    
    result = describe_video(file, mode="full")
    
    print(f"\n📹 File: {result['file']}")
    print(f"⏱️ Duration: {result.get('duration', 'unknown')}")
    print(f"🎬 Scenes analyzed: {result.get('scenes', result.get('num_frames', '?'))}")
    print(f"\n📝 Description:\n{result['description']}")
    
    return result


def demo_stream_mode(file: str):
    """
    Demo: Stream mode - frame-by-frame analysis
    
    Provides detailed description of each analyzed frame
    including subjects, objects, actions, and text.
    
    CLI equivalent:
        sq media describe_video --file video.mp4 --mode stream
    """
    print("\n" + "=" * 60)
    print("MODE: STREAM - Frame-by-Frame Details")
    print("=" * 60)
    
    result = describe_video(file, mode="stream")
    
    print(f"\n📹 File: {result['file']}")
    print(f"🎞️ Frames analyzed: {result['num_frames']}")
    
    print("\n📋 Frame Details:")
    for frame in result.get("frames", []):
        print(f"\n[{frame['timestamp']}] Frame {frame['frame']}")
        print("-" * 40)
        print(frame['description'][:500])
        if len(frame['description']) > 500:
            print("...")
    
    return result


def demo_diff_mode(file: str):
    """
    Demo: Diff mode - track changes between frames
    
    Identifies what changed between consecutive frames:
    - NEW: What appeared
    - REMOVED: What disappeared
    - MOVED: Position changes
    - CHANGED: Visual changes
    
    CLI equivalent:
        sq media describe_video --file video.mp4 --mode diff
    """
    print("\n" + "=" * 60)
    print("MODE: DIFF - Track Changes")
    print("=" * 60)
    
    result = describe_video(file, mode="diff")
    
    print(f"\n📹 File: {result['file']}")
    print(f"🔄 Significant changes: {result.get('significant_changes', '?')}")
    
    print("\n📊 Timeline:")
    for item in result.get("timeline", []):
        emoji = "🟢" if item["type"] == "start" else ("🔵" if item["type"] == "change" else "⚪")
        print(f"\n{emoji} [{item['timestamp']}] {item['type'].upper()}")
        content = item.get("changes", item.get("description", ""))
        print(f"   {content[:300]}")
    
    print(f"\n📝 Summary:\n{result.get('summary', 'No summary available')}")
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Video Captioning with AI - Three analysis modes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python video_captioning.py video.mp4                    # Full mode (default)
  python video_captioning.py video.mp4 --mode stream      # Frame-by-frame
  python video_captioning.py video.mp4 --mode diff        # Track changes
  python video_captioning.py video.mp4 --all              # Run all modes

CLI equivalents:
  sq media describe_video --file video.mp4 --mode full
  sq media describe_video --file video.mp4 --mode stream
  sq media describe_video --file video.mp4 --mode diff

Documentation:
  - examples/media-processing/README.md
  - docs/v2/guides/MEDIA_GUIDE.md
        """
    )
    parser.add_argument("file", nargs="?", help="Video file to analyze")
    parser.add_argument("--mode", choices=["full", "stream", "diff"], default="full",
                       help="Analysis mode (default: full)")
    parser.add_argument("--all", action="store_true", help="Run all three modes")
    parser.add_argument("--prompt", help="Custom prompt for AI")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    if not args.file:
        print("=" * 60)
        print("VIDEO CAPTIONING DEMO")
        print("=" * 60)
        print("\nUsage: python video_captioning.py <video_file> [--mode MODE]")
        print("\nModes:")
        print("  full   - Coherent narrative summary (default)")
        print("  stream - Detailed frame-by-frame analysis")
        print("  diff   - Track changes between frames")
        print("\nExamples:")
        print("  python video_captioning.py video.mp4")
        print("  python video_captioning.py video.mp4 --mode stream")
        print("  python video_captioning.py video.mp4 --mode diff --prompt 'Focus on people'")
        print("\nCLI equivalent:")
        print("  sq media describe_video --file video.mp4 --mode full")
        print("\nSee: examples/media-processing/README.md for full documentation")
        return 1
    
    try:
        if args.all:
            # Run all modes
            results = {
                "full": demo_full_mode(args.file),
                "stream": demo_stream_mode(args.file),
                "diff": demo_diff_mode(args.file)
            }
            if args.json:
                print("\n" + json.dumps(results, indent=2))
        else:
            # Run single mode
            if args.mode == "full":
                result = demo_full_mode(args.file)
            elif args.mode == "stream":
                result = demo_stream_mode(args.file)
            else:
                result = demo_diff_mode(args.file)
            
            if args.json:
                print("\n" + json.dumps(result, indent=2))
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure you have:")
        print("  1. ollama pull llava")
        print("  2. sudo apt-get install ffmpeg")
        return 1


if __name__ == "__main__":
    sys.exit(main())
