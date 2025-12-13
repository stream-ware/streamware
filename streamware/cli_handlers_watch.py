"""
CLI Handlers - Watch Command

Large handler for watch command with qualitative parameters.
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


def handle_watch(args) -> int:
    """Handle watch command with qualitative parameters or natural language"""
    flow = _get_flow()
    from .presets import get_preset, describe_settings
    from .config import config
    
    notify_email = getattr(args, 'email', None)
    notify_slack = getattr(args, 'slack', None)
    notify_telegram = getattr(args, 'telegram', None)
    notify_webhook = getattr(args, 'webhook', None)
    notify_mode = getattr(args, 'notify_mode', 'digest')
    notify_interval = getattr(args, 'notify_interval', 60)
    
    if args.intent:
        from .intent import parse_intent, apply_intent
        
        intent = parse_intent(args.intent)
        apply_intent(intent)
        
        if notify_email:
            intent.notify_email = notify_email
        if notify_mode:
            intent.notify_mode = notify_mode
        
        url = args.url or config.get("SQ_DEFAULT_URL") or config.get("SQ_STREAM_URL")
        if not url:
            print("❌ Error: No URL provided. Use --url or set SQ_DEFAULT_URL in .env")
            return 1
        
        print(f"\n🎯 Intent: {intent.describe()}")
        print(f"   Source: {url[:50]}...")
        print(f"   Duration: {args.duration}s")
        print()
        
        from .components.live_narrator import LiveNarratorComponent
        
        uri = f"live://narrator?source={url}"
        uri += f"&mode={intent.mode}"
        uri += f"&focus={intent.target}"
        uri += f"&duration={args.duration}"
        if intent.tts or getattr(args, 'tts', False):
            uri += "&tts=true"
            uri += f"&tts_mode={intent.tts_mode}"
        
        if intent.notify_email:
            uri += f"&notify_email={intent.notify_email}"
        if intent.notify_mode:
            uri += f"&notify_mode={intent.notify_mode}"
        
        try:
            result = flow(uri).run()
            return 0
        except Exception as e:
            print(f"Error: {e}")
            return 1
    
    detect_target = getattr(args, 'detect', 'any')
    track_target = getattr(args, 'track', None)
    count_target = getattr(args, 'count', None)
    
    if notify_email or notify_slack or notify_telegram or track_target or count_target:
        from .intent import Intent
        
        target = track_target or count_target or detect_target
        action = 'track' if track_target else ('count' if count_target else 'detect')
        intent = Intent(raw_text=f"{action} {target}")
        intent.target = target
        intent.action = action
        intent.notify_email = notify_email
        intent.notify_slack = notify_slack
        intent.notify_telegram = notify_telegram
        intent.notify_webhook = notify_webhook
        intent.notify_mode = notify_mode
        intent.notify_interval = notify_interval
        intent.tts = getattr(args, 'tts', False)
        
        url = args.url or config.get("SQ_DEFAULT_URL") or config.get("SQ_STREAM_URL")
        if not url:
            print("❌ Error: No URL provided. Use --url or set SQ_DEFAULT_URL in .env")
            return 1
        
        print(f"\n🎯 Watch: {intent.action} {intent.target}")
        print(f"   Source: {url[:50]}...")
        print(f"   Duration: {args.duration}s")
        if notify_email:
            print(f"   📧 Email: {notify_email} (mode={notify_mode})")
        print()
        
        try:
            from .components.live_narrator import LiveNarratorComponent
            
            uri = f"live://narrator?source={url}"
            uri += f"&mode={intent.action}"
            uri += f"&focus={intent.target}"
            uri += f"&duration={args.duration}"
            
            if intent.tts:
                uri += "&tts=true"
            
            if intent.notify_email:
                uri += f"&notify_email={intent.notify_email}"
            if intent.notify_mode:
                uri += f"&notify_mode={intent.notify_mode}"
            if intent.notify_interval:
                uri += f"&notify_interval={intent.notify_interval}"
            if intent.notify_slack:
                uri += f"&notify_slack={intent.notify_slack}"
            if intent.notify_telegram:
                uri += f"&notify_telegram={intent.notify_telegram}"
            
            result = flow(uri).run()
            return 0
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return 1
    
    if not args.url:
        print("❌ Error: --url is required (or use natural language intent)")
        print("   Example: sq watch 'track person' --url rtsp://...")
        print("   Example: sq watch --url rtsp://... --detect person")
        return 1
    
    settings = get_preset(
        sensitivity=args.sensitivity,
        detect=args.detect,
        speed=args.speed
    )
    
    desc = describe_settings(args.sensitivity, args.detect, args.speed)
    print(f"\n🎯 Watch Mode: {desc}")
    print(f"   Source: {args.url[:50]}...")
    print(f"   Duration: {args.duration}s")
    if args.alert != "none":
        print(f"   Alert: {args.alert}")
    print()
    
    uri = f"motion://analyze?source={args.url}"
    uri += f"&threshold={settings['threshold']}"
    uri += f"&min_region={settings['min_region']}"
    uri += f"&grid={settings['grid_size']}"
    uri += f"&interval={settings['interval']}"
    uri += f"&duration={args.duration}"
    uri += f"&save_frames=true"
    
    if settings['focus']:
        uri += f"&focus={settings['focus']}"
    
    if not settings['ai_enabled']:
        uri += "&no_ai=true"
    
    try:
        result = flow(uri).run()
        
        if args.alert != "none":
            changes = result.get("significant_changes", 0)
            if changes > 0:
                _trigger_alert(args.alert, args.detect, changes, args.url)
        
        fmt = _get_output_format(args)
        
        if fmt == "json":
            print(json.dumps(result, indent=2, default=str))
        else:
            _print_watch_yaml(result, args)
        
        log_format = getattr(args, 'log', None)
        if getattr(args, 'file', None):
            if log_format == 'md':
                _save_watch_markdown_log(result, args, args.file)
            else:
                _save_watch_report(result, args)
        elif log_format == 'md':
            _save_watch_markdown_log(result, args, "watch_log.md")
        
        return 0
        
    except Exception as e:
        print(f"Watch failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def _trigger_alert(alert_type: str, detect: str, changes: int, url: str):
    """Trigger the specified alert"""
    message = f"Detected {detect}: {changes} changes"
    
    if alert_type == "speak":
        try:
            import subprocess
            subprocess.Popen(["espeak", message], 
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            print(f"🔔 {message}")
    
    elif alert_type == "sound":
        try:
            import subprocess
            subprocess.Popen(["paplay", "/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            print("\a")
    
    elif alert_type == "slack":
        from .helpers import send_alert
        send_alert(message, slack=True)
    
    elif alert_type == "telegram":
        from .helpers import send_alert
        send_alert(message, telegram=True)
    
    elif alert_type == "log":
        print(f"🔔 ALERT: {message}")


def _print_watch_yaml(result: dict, args):
    """Print watch result as YAML"""
    changes = result.get("significant_changes", 0)
    frames = result.get("frames_analyzed", 0)
    
    status = "🔴 DETECTED" if changes > 0 else "✅ CLEAR"
    
    print(f"# Watch ({args.detect})")
    print(f"# Sensitivity: {args.sensitivity}, Speed: {args.speed}")
    print("---")
    print()
    print(f"status: {status}")
    print(f"detected: {args.detect}")
    print(f"changes: {changes}")
    print(f"frames: {frames}")
    print()
    
    timeline = result.get("timeline", [])
    if timeline:
        print("events:")
        for entry in timeline:
            if entry.get("type") == "change":
                ts = entry.get("timestamp", "")
                change_pct = entry.get("change_percent", 0)
                regions = len(entry.get("regions", []))
                print(f"  - time: \"{ts}\"")
                print(f"    change: {change_pct:.1f}%")
                print(f"    regions: {regions}")
                
                analyses = entry.get("region_analyses", [])
                if analyses:
                    desc = analyses[0].get("description", "")
                    print(f"    description: \"{desc}\"")


def _save_watch_report(result: dict, args):
    """Save watch report as HTML"""
    from pathlib import Path
    from datetime import datetime
    
    output_path = Path(args.file).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    changes = result.get("significant_changes", 0)
    status = "DETECTED" if changes > 0 else "CLEAR"
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Watch Report - {args.detect}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
        .header {{ background: {'#e74c3c' if changes > 0 else '#27ae60'}; color: white; 
                  padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .config {{ background: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
        .event {{ background: white; padding: 15px; margin: 10px 0; border-radius: 8px; 
                 border-left: 4px solid {'#e74c3c' if changes > 0 else '#3498db'}; }}
        .frame {{ max-width: 100%; border-radius: 4px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 Watch Report: {args.detect.upper()}</h1>
        <p>Status: <strong>{status}</strong> | Changes: {changes} | 
           Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="config">
        <h3>Configuration</h3>
        <p><strong>Sensitivity:</strong> {args.sensitivity} | 
           <strong>Speed:</strong> {args.speed} | 
           <strong>Duration:</strong> {args.duration}s</p>
        <p><strong>Source:</strong> {args.url[:80]}...</p>
    </div>
"""
    
    timeline = result.get("timeline", [])
    for entry in timeline:
        if entry.get("type") == "change":
            ts = entry.get("timestamp", "")
            change_pct = entry.get("change_percent", 0)
            
            html += f"""
    <div class="event">
        <h4>📍 {ts} - {change_pct:.1f}% change</h4>
"""
            
            img = entry.get("image_base64", "")
            if img:
                html += f'<img class="frame" src="data:image/jpeg;base64,{img}">'
            
            analyses = entry.get("region_analyses", [])
            for a in analyses[:3]:
                desc = a.get("description", "")
                html += f"<p>{desc}</p>"
            
            html += "</div>"
    
    html += """
</body>
</html>"""
    
    with open(output_path, "w") as f:
        f.write(html)
    
    print(f"📄 Report saved: {output_path}")


def _save_watch_markdown_log(result: dict, args, output_file: str):
    """Save watch result as Markdown log."""
    from pathlib import Path
    from datetime import datetime

    output_path = Path(output_file).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    changes = result.get("significant_changes", 0)
    frames = result.get("frames_analyzed", 0)
    timeline = result.get("timeline", [])

    lines = []
    lines.append(f"# Watch Log: {args.detect}")
    lines.append("")
    lines.append(f"- **Source**: `{args.url}`")
    lines.append(f"- **Sensitivity**: `{args.sensitivity}`")
    lines.append(f"- **Speed**: `{args.speed}`")
    lines.append(f"- **Duration**: `{args.duration}s`")
    lines.append(f"- **Generated**: {datetime.now().isoformat(timespec='seconds')}")
    lines.append("")
    lines.append(f"- **Frames analyzed**: `{frames}`")
    lines.append(f"- **Significant changes**: `{changes}`")
    lines.append("")

    if timeline:
        lines.append("## Events")
        for entry in timeline:
            if entry.get("type") != "change":
                continue
            ts = entry.get("timestamp", "")
            change_pct = entry.get("change_percent", 0)
            regions = len(entry.get("regions", []))
            lines.append(f"- **Time**: `{ts}`  ")
            lines.append(f"  - **Change**: `{change_pct:.1f}%` in `{regions}` region(s)")
            analyses = entry.get("region_analyses", [])
            if analyses:
                first = analyses[0]
                desc = first.get("analysis") or first.get("description", "")
                if desc:
                    short = desc.replace("\n", " ").strip()[:200]
                    lines.append(f"  - **AI**: {short}...")
            lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")

    print(f"📄 Markdown log saved: {output_path}")
