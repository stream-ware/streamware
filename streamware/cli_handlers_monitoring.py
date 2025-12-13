"""
CLI Handlers - Monitoring Operations

Handlers for: tracking, motion, smart
"""

import sys
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse


def _get_flow():
    """Lazy import for flow."""
    from .core import flow
    return flow


def _get_output_format(args) -> str:
    """Determine output format from global args (yaml is default)"""
    if getattr(args, 'json', False):
        return "json"
    if getattr(args, 'table', False):
        return "table"
    if getattr(args, 'html', False):
        return "html"
    return "yaml"


def handle_tracking(args) -> int:
    """Handle object tracking command"""
    flow = _get_flow()
    
    op = args.operation
    url = args.url
    
    uri = f"tracking://{op}?source={url}"
    uri += f"&objects={args.objects}"
    uri += f"&duration={args.duration}"
    uri += f"&interval={args.interval}"
    
    if args.target:
        uri += f"&target={args.target}"
    if args.name:
        uri += f"&name={args.name}"
    if args.zones:
        uri += f"&zones={args.zones}"
    
    try:
        result = flow(uri).run()
        
        fmt = _get_output_format(args)
        
        if fmt == "json":
            print(json.dumps(result, indent=2))
        else:
            _print_tracking_yaml(result, op)
        
        if getattr(args, 'file', None):
            from .helpers import generate_report
            generate_report(result, args.file, f"Tracking Report: {op}")
            print(f"\n📄 Report saved: {args.file}")
        
        return 0
        
    except Exception as e:
        print(f"Tracking failed: {e}", file=sys.stderr)
        return 1


def _print_tracking_yaml(result: dict, op: str):
    """Print tracking result as YAML"""
    print(f"# Tracking: {op}")
    print(f"# Source: {result.get('source', 'N/A')}")
    print("---")
    
    summary = result.get("summary", {})
    
    total = summary.get("total_objects", 0)
    print(f"\nstatus: {'🔴 OBJECTS_DETECTED' if total > 0 else '✅ NO_OBJECTS'}")
    print(f"total_objects: {total}")
    
    by_type = summary.get("by_type", {})
    if by_type:
        print("\nby_type:")
        for obj_type, count in by_type.items():
            print(f"  {obj_type}: {count}")
    
    objects = summary.get("objects", [])
    if objects:
        print("\nobjects:")
        for obj in objects[:10]:
            print(f"  - id: {obj.get('id')}")
            print(f"    type: {obj.get('type')}")
            if obj.get('name'):
                print(f"    name: {obj.get('name')}")
            print(f"    direction: {obj.get('direction', 'unknown')}")
            print(f"    frames_visible: {obj.get('frames_visible', 0)}")
            print(f"    trajectory_points: {obj.get('trajectory_points', 0)}")
    
    events = result.get("events", [])
    if events:
        print(f"\nevents: # {len(events)} total")
        for event in events[:10]:
            icon = "➡️" if event.get("type") == "zone_enter" else "⬅️"
            print(f"  - {icon} [{event.get('timestamp')}] {event.get('object_type')} {event.get('type')} {event.get('zone')}")
    
    stats = result.get("statistics", {})
    if stats:
        print("\nstatistics:")
        for obj_type, s in stats.items():
            print(f"  {obj_type}:")
            print(f"    min: {s.get('min', 0)}")
            print(f"    max: {s.get('max', 0)}")
            print(f"    avg: {s.get('avg', 0):.1f}")


def handle_motion(args) -> int:
    """Handle smart motion detection command"""
    flow = _get_flow()
    from pathlib import Path
    
    op = getattr(args, 'operation', 'analyze') or 'analyze'
    url = args.url
    
    uri = f"motion://{op}?source={url}"
    uri += f"&threshold={args.threshold}"
    uri += f"&min_region={getattr(args, 'min_region', 500)}"
    uri += f"&grid={args.grid}"
    uri += f"&focus={args.focus}"
    uri += f"&duration={args.duration}"
    uri += f"&interval={args.interval}"
    
    if getattr(args, 'file', None):
        uri += "&save_frames=true"
    
    try:
        result = flow(uri).run()
        
        if getattr(args, 'file', None):
            _save_motion_html_report(result, args.file)
            print(f"📄 Report saved: {args.file}")
        
        fmt = _get_output_format(args)
        
        if fmt == "json":
            print(json.dumps(result, indent=2, default=str))
        else:
            _print_motion_yaml(result)
        
        return 0
        
    except Exception as e:
        print(f"Motion detection failed: {e}", file=sys.stderr)
        print("\nRequirements:")
        print("  - ffmpeg")
        print("  - Pillow: pip install Pillow")
        print("  - numpy: pip install numpy")
        print("  - ollama pull llava:13b")
        return 1


def _print_motion_yaml(result: dict):
    """Print motion result as YAML"""
    timeline = result.get("timeline", [])
    changes = result.get("significant_changes", result.get("total_changes", 0))
    frames = result.get("frames_analyzed", len(timeline))
    
    print(f"# Motion Detection ({result.get('operation', 'analyze')})")
    print(f"# Source: {result.get('source', 'N/A')}")
    print("---")
    print()
    
    if changes == 0:
        print("status: ✅ NO_MOTION")
    else:
        print(f"status: 🔴 MOTION_DETECTED ({changes} changes)")
    print()
    
    print("timeline:")
    for frame in timeline:
        frame_num = frame.get("frame", "?")
        ts = frame.get("timestamp", "")
        has_change = frame.get("has_change", frame.get("type") == "change")
        change_pct = frame.get("change_percent", 0)
        regions = frame.get("regions_detected", len(frame.get("regions", [])))
        
        status = "🔴 CHANGE" if has_change else "⚪ stable"
        
        print(f"  - frame: {frame_num}")
        print(f"    time: \"{ts}\"")
        print(f"    status: {status}")
        
        if has_change:
            print(f"    change_percent: {change_pct}%")
            print(f"    regions: {regions}")
            
            region_analyses = frame.get("region_analyses", [])
            if region_analyses:
                print(f"    analysis:")
                for ra in region_analyses[:2]:
                    region = ra.get("region", {})
                    analysis = ra.get("analysis", "")[:150]
                    print(f"      - region: ({region.get('x')},{region.get('y')}) {region.get('width')}x{region.get('height')}")
                    print(f"        change: {region.get('change_percent')}%")
                    print(f"        description: \"{analysis}...\"")
            
            summary = frame.get("changes", "")
            if summary and not region_analyses:
                print(f"    summary: \"{summary[:200]}...\"")
        print()
    
    print("# Summary")
    print("summary:")
    print(f"  frames: {frames}")
    print(f"  changes: {changes}")
    print(f"  change_ratio: {(changes/frames*100):.1f}%" if frames > 0 else "  change_ratio: 0%")


def _save_motion_html_report(result: dict, output_file: str):
    """Save motion analysis as HTML report"""
    from datetime import datetime
    from pathlib import Path
    
    output_path = Path(output_file).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    timeline = result.get("timeline", [])
    changes = result.get("significant_changes", result.get("total_changes", 0))
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Motion Detection Report</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-900 text-white min-h-screen p-8">
    <div class="max-w-6xl mx-auto">
        <header class="mb-8">
            <h1 class="text-3xl font-bold">🎯 Smart Motion Detection Report</h1>
            <p class="text-gray-400 mt-2">Region-based analysis • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </header>
        
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div class="bg-gray-800 rounded-lg p-4">
                <div class="text-2xl font-bold">{len(timeline)}</div>
                <div class="text-gray-400">Frames</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-4">
                <div class="text-2xl font-bold {'text-red-400' if changes > 0 else 'text-green-400'}">{changes}</div>
                <div class="text-gray-400">Changes</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-4">
                <div class="text-lg">Region-based</div>
                <div class="text-gray-400">Detection Mode</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-4">
                <div class="text-lg">{'🔴 MOTION' if changes > 0 else '✅ STABLE'}</div>
                <div class="text-gray-400">Status</div>
            </div>
        </div>
        
        <h2 class="text-2xl font-bold mb-4">Timeline</h2>
        <div class="space-y-6">
"""
    
    for frame in timeline:
        has_change = frame.get("has_change", frame.get("type") == "change")
        frame_num = frame.get("frame", "?")
        ts = frame.get("timestamp", "")
        change_pct = frame.get("change_percent", 0)
        regions = frame.get("regions_detected", 0)
        image_b64 = frame.get("image_base64", "")
        
        border_class = "border-red-500 bg-red-900/20" if has_change else "border-gray-600 bg-gray-800"
        status_badge = '<span class="bg-red-600 px-2 py-1 rounded text-sm">🔴 MOTION</span>' if has_change else '<span class="bg-gray-600 px-2 py-1 rounded text-sm">⚪ Stable</span>'
        
        html += f"""
            <div class="border-2 {border_class} rounded-lg p-4">
                <div class="flex justify-between items-center mb-4">
                    <div class="flex items-center gap-4">
                        <span class="text-xl font-bold">Frame {frame_num}</span>
                        <span class="text-gray-400">{ts}</span>
                        {f'<span class="text-yellow-400">{change_pct}% changed</span>' if has_change else ''}
                        {f'<span class="text-blue-400">{regions} regions</span>' if regions else ''}
                    </div>
                    {status_badge}
                </div>
"""
        
        if image_b64:
            html += f"""
                <div class="mb-4">
                    <img src="data:image/jpeg;base64,{image_b64}" 
                         class="max-w-full h-auto rounded-lg border border-gray-600"
                         alt="Frame {frame_num}">
                </div>
"""
        
        region_analyses = frame.get("region_analyses", [])
        if region_analyses:
            html += """<div class="grid md:grid-cols-2 gap-4">"""
            for ra in region_analyses:
                region = ra.get("region", {})
                analysis = ra.get("analysis", "")
                
                html += f"""
                    <div class="bg-gray-900 rounded p-3">
                        <div class="text-sm text-yellow-400 mb-2">
                            Region ({region.get('x')},{region.get('y')}) • {region.get('width')}x{region.get('height')} • {region.get('change_percent')}% change
                        </div>
                        <div class="text-sm text-gray-300">{analysis[:500]}</div>
                    </div>
"""
            html += """</div>"""
        
        html += """
            </div>
"""
    
    html += f"""
        </div>
        
        <footer class="mt-8 pt-4 border-t border-gray-700 text-gray-500 text-sm">
            <p>Generated by Streamware Smart Motion Detection • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </footer>
    </div>
</body>
</html>
"""
    
    with open(output_path, "w") as f:
        f.write(html)


def handle_smart(args) -> int:
    """Handle smart monitoring command"""
    flow = _get_flow()
    from pathlib import Path
    
    op = getattr(args, 'operation', 'monitor') or 'monitor'
    url = args.url
    
    uri = f"smart://{op}?source={url}"
    uri += f"&min_interval={getattr(args, 'min_interval', 1.0)}"
    uri += f"&max_interval={getattr(args, 'max_interval', 10.0)}"
    uri += f"&adaptive={'true' if getattr(args, 'adaptive', True) else 'false'}"
    uri += f"&buffer_size={getattr(args, 'buffer_size', 50)}"
    uri += f"&threshold={args.threshold}"
    uri += f"&min_change={getattr(args, 'min_change', 0.5)}"
    uri += f"&focus={args.focus}"
    uri += f"&duration={args.duration}"
    uri += f"&quality={getattr(args, 'quality', 90)}"
    uri += f"&ai={'false' if getattr(args, 'no_ai', False) else 'true'}"
    
    if getattr(args, 'zones', None):
        uri += f"&zones={args.zones}"
    
    if getattr(args, 'file', None):
        uri += "&save_all=true"
    
    print(f"🎯 Smart Monitor ({op})")
    print(f"   Source: {url[:50]}...")
    print(f"   Interval: {getattr(args, 'min_interval', 1.0)}s - {getattr(args, 'max_interval', 10.0)}s")
    print(f"   Buffer: {getattr(args, 'buffer_size', 50)} frames")
    print(f"   AI: {'Off' if getattr(args, 'no_ai', False) else 'On'}")
    print()
    
    try:
        result = flow(uri).run()
        
        if getattr(args, 'file', None):
            _save_smart_html_report(result, args.file)
            print(f"📄 Report saved: {args.file}")
        
        fmt = _get_output_format(args)
        
        if fmt == "json":
            print(json.dumps(result, indent=2, default=str))
        else:
            _print_smart_yaml(result)
        
        return 0
        
    except Exception as e:
        print(f"Smart monitoring failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def _print_smart_yaml(result: dict):
    """Print smart monitor result as YAML"""
    timeline = result.get("timeline", [])
    changes = result.get("significant_changes", result.get("frames_with_changes", 0))
    captured = result.get("frames_captured", len(timeline))
    config = result.get("config", {})
    
    print(f"# Smart Monitor ({result.get('operation', 'monitor')})")
    print(f"# Source: {result.get('source', 'N/A')}")
    print(f"# Mode: {result.get('mode', 'buffered')}")
    print("---")
    print()
    
    print("config:")
    print(f"  interval: {config.get('min_interval', '?')}s - {config.get('max_interval', '?')}s")
    print(f"  adaptive: {config.get('adaptive', False)}")
    print(f"  buffer: {config.get('buffer_size', '?')}")
    print(f"  threshold: {config.get('threshold', '?')}")
    print()
    
    if changes == 0:
        print("status: ✅ NO_CHANGES")
    else:
        print(f"status: 🔴 CHANGES_DETECTED ({changes})")
    print()
    
    print("stats:")
    print(f"  frames_captured: {captured}")
    print(f"  frames_with_changes: {changes}")
    print(f"  buffer_overflows: {result.get('buffer_overflows', 0)}")
    print()
    
    change_frames = [f for f in timeline if f.get("type") == "change"]
    if change_frames:
        print(f"changes: # {len(change_frames)} total")
        for frame in change_frames[:10]:
            print(f"  - frame: {frame.get('frame')}")
            print(f"    time: \"{frame.get('timestamp')}\"")
            print(f"    change: {frame.get('change_percent')}%")
            print(f"    regions: {frame.get('regions', 0)}")
            
            analysis = frame.get("analysis", "")
            if analysis:
                print(f"    analysis: \"{analysis[:150]}...\"")
            print()


def _save_smart_html_report(result: dict, output_file: str):
    """Save smart monitor result as HTML report"""
    from datetime import datetime
    from pathlib import Path
    
    output_path = Path(output_file).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    timeline = result.get("timeline", [])
    changes = result.get("significant_changes", result.get("frames_with_changes", 0))
    captured = result.get("frames_captured", 0)
    config = result.get("config", {})
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Smart Monitor Report</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-900 text-white min-h-screen p-8">
    <div class="max-w-6xl mx-auto">
        <header class="mb-8">
            <h1 class="text-3xl font-bold">🎯 Smart Monitor Report</h1>
            <p class="text-gray-400 mt-2">Buffered adaptive monitoring • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </header>
        
        <div class="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
            <div class="bg-gray-800 rounded-lg p-4">
                <div class="text-2xl font-bold">{captured}</div>
                <div class="text-gray-400">Captured</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-4">
                <div class="text-2xl font-bold {'text-red-400' if changes > 0 else 'text-green-400'}">{changes}</div>
                <div class="text-gray-400">Changes</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-4">
                <div class="text-lg">{config.get('min_interval', '?')}s-{config.get('max_interval', '?')}s</div>
                <div class="text-gray-400">Interval</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-4">
                <div class="text-lg">{config.get('buffer_size', '?')}</div>
                <div class="text-gray-400">Buffer</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-4">
                <div class="text-lg">{'🔴 MOTION' if changes > 0 else '✅ STABLE'}</div>
                <div class="text-gray-400">Status</div>
            </div>
        </div>
        
        <h2 class="text-2xl font-bold mb-4">Timeline (Changes Only)</h2>
        <div class="space-y-6">
"""
    
    for frame in timeline:
        if frame.get("type") != "change":
            continue
        
        frame_num = frame.get("frame", "?")
        ts = frame.get("timestamp", "")
        change_pct = frame.get("change_percent", 0)
        regions = frame.get("regions", 0)
        analysis = frame.get("analysis", "")
        image_b64 = frame.get("image_base64", "")
        region_details = frame.get("region_details", [])
        
        html += f"""
            <div class="border-2 border-red-500 bg-red-900/20 rounded-lg p-4">
                <div class="flex justify-between items-center mb-4">
                    <div class="flex items-center gap-4">
                        <span class="text-xl font-bold">Frame {frame_num}</span>
                        <span class="text-gray-400">{ts}</span>
                        <span class="text-yellow-400">{change_pct}% changed</span>
                        <span class="text-blue-400">{regions} regions</span>
                    </div>
                    <span class="bg-red-600 px-2 py-1 rounded text-sm">🔴 CHANGE</span>
                </div>
"""
        
        if image_b64:
            html += f"""
                <div class="mb-4">
                    <img src="data:image/jpeg;base64,{image_b64}" 
                         class="max-w-full h-auto rounded-lg border border-gray-600" alt="Frame {frame_num}">
                </div>
"""
        
        if region_details:
            html += """<div class="grid md:grid-cols-2 gap-4 mt-4">"""
            for rd in region_details:
                region = rd.get("region", {})
                ra = rd.get("analysis", "")
                html += f"""
                    <div class="bg-gray-900 rounded p-3">
                        <div class="text-sm text-yellow-400 mb-2">
                            Region ({region.get('x')},{region.get('y')}) • {region.get('width')}x{region.get('height')} • {region.get('change_percent')}%
                        </div>
                        <div class="text-sm text-gray-300">{ra[:400]}</div>
                    </div>
"""
            html += """</div>"""
        elif analysis:
            html += f"""<div class="bg-gray-800 rounded p-3 mt-4"><p class="text-sm">{analysis}</p></div>"""
        
        html += """</div>"""
    
    html += f"""
        </div>
        <footer class="mt-8 pt-4 border-t border-gray-700 text-gray-500 text-sm">
            <p>Generated by Streamware Smart Monitor • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </footer>
    </div>
</body>
</html>
"""
    
    with open(output_path, "w") as f:
        f.write(html)
