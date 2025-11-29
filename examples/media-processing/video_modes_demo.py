#!/usr/bin/env python3
"""
Video Modes Demo - Compare all three analysis modes

This script demonstrates the difference between:
    - full: Overall narrative
    - stream: Frame details
    - diff: Change tracking

Usage:
    python video_modes_demo.py video.mp4

Related:
    - examples/media-processing/README.md - Mode documentation
    - examples/media-processing/video_captioning.py - Main example
    - docs/v2/guides/MEDIA_GUIDE.md - Media guide
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from streamware import flow


def compare_modes(video_file: str):
    """Compare all three video analysis modes side by side."""
    
    print("=" * 70)
    print("VIDEO ANALYSIS MODES COMPARISON")
    print("=" * 70)
    print(f"\n📹 Analyzing: {video_file}\n")
    
    modes = [
        ("full", "Coherent Narrative", "Single description tracking subjects through video"),
        ("stream", "Frame-by-Frame", "Detailed analysis of each frame"),
        ("diff", "Change Tracking", "What changed between frames"),
    ]
    
    results = {}
    
    for mode, title, desc in modes:
        print(f"\n{'─' * 70}")
        print(f"🎬 MODE: {mode.upper()} - {title}")
        print(f"   {desc}")
        print("─" * 70)
        
        try:
            result = flow(f"media://describe_video?file={video_file}&mode={mode}").run()
            results[mode] = result
            
            if mode == "full":
                print(f"\n📝 Description:\n{result['description'][:500]}...")
                print(f"\n📊 Stats: {result.get('num_frames', '?')} frames, {result.get('duration', '?')} duration")
                
            elif mode == "stream":
                frames = result.get("frames", [])
                print(f"\n🎞️ Analyzed {len(frames)} frames:")
                for f in frames[:3]:  # Show first 3
                    print(f"\n  [{f['timestamp']}] {f['description'][:150]}...")
                if len(frames) > 3:
                    print(f"\n  ... and {len(frames) - 3} more frames")
                    
            elif mode == "diff":
                timeline = result.get("timeline", [])
                changes = result.get("significant_changes", 0)
                print(f"\n🔄 {changes} significant changes detected")
                print(f"\n📝 Summary: {result.get('summary', 'N/A')}")
                print(f"\n📊 Timeline ({len(timeline)} entries):")
                for t in timeline[:4]:
                    icon = "🟢" if t["type"] == "start" else "🔵" if t["type"] == "change" else "⚪"
                    content = t.get("changes", t.get("description", ""))[:100]
                    print(f"  {icon} [{t['timestamp']}] {content}...")
                    
        except Exception as e:
            print(f"❌ Error: {e}")
            results[mode] = {"error": str(e)}
    
    # Summary comparison
    print("\n" + "=" * 70)
    print("📋 COMPARISON SUMMARY")
    print("=" * 70)
    
    print("""
| Mode   | Best For                          | Output Type        |
|--------|-----------------------------------|-------------------|
| full   | Video summaries, SEO, accessibility | Single narrative  |
| stream | Documentation, training data       | Frame-by-frame    |
| diff   | Surveillance, activity tracking    | Change timeline   |
    """)
    
    print("\n💡 CLI Commands:")
    print(f"  sq media describe_video --file {video_file} --mode full")
    print(f"  sq media describe_video --file {video_file} --mode stream")
    print(f"  sq media describe_video --file {video_file} --mode diff")
    
    return results


def main():
    if len(sys.argv) < 2:
        print("=" * 60)
        print("VIDEO MODES COMPARISON DEMO")
        print("=" * 60)
        print("\nUsage: python video_modes_demo.py <video_file>")
        print("\nThis script compares all three analysis modes:")
        print("  - full: Coherent narrative")
        print("  - stream: Frame-by-frame details")
        print("  - diff: Change tracking")
        print("\nExample:")
        print("  python video_modes_demo.py presentation.mp4")
        print("\nSee: examples/media-processing/README.md")
        return 1
    
    video_file = sys.argv[1]
    
    if not os.path.exists(video_file):
        print(f"❌ File not found: {video_file}")
        return 1
    
    try:
        results = compare_modes(video_file)
        
        # Save results
        output_file = f"{os.path.splitext(video_file)[0]}_analysis.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Results saved to: {output_file}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
