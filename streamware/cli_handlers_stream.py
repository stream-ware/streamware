"""
CLI Handlers - Stream Analysis

Handlers for: stream, network, config
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


def show_examples(command: str, examples: list, missing_param: str = None):
    """Show helpful examples when parameter is missing"""
    print(f"\n{'─' * 60}")
    if missing_param:
        print(f"⚠️  Missing parameter: --{missing_param}")
    print(f"\n📋 Examples for 'sq {command}':\n")
    for ex in examples:
        print(f"  {ex}")
    print(f"\n{'─' * 60}")
    print("💡 Tip: Use --help for all options\n")


def _get_output_format(args) -> str:
    """Determine output format from global args (yaml is default)"""
    if getattr(args, 'json', False):
        return "json"
    if getattr(args, 'table', False):
        return "table"
    if getattr(args, 'html', False):
        return "html"
    return "yaml"


def handle_stream(args) -> int:
    """Handle stream command for real-time video analysis"""
    flow = _get_flow()
    
    examples = {
        "rtsp": [
            "sq stream rtsp --url rtsp://192.168.1.100/live --mode diff",
            "sq stream rtsp --url rtsp://camera/stream --interval 3 --duration 60",
        ],
        "hls": [
            "sq stream hls --url https://stream.example.com/live.m3u8 --mode stream",
        ],
        "youtube": [
            "sq stream youtube --url 'https://youtube.com/watch?v=xxx' --mode stream",
            "sq stream youtube --url 'https://youtu.be/xxx' --duration 30",
        ],
        "twitch": [
            "sq stream twitch --url 'https://twitch.tv/channel' --mode diff",
        ],
        "screen": [
            "sq stream screen --mode diff --interval 2",
            "sq stream screen --mode stream --duration 60",
            "sq stream screen --continuous  # Non-stop monitoring",
        ],
        "webcam": [
            "sq stream webcam --device 0 --mode stream",
            "sq stream webcam --mode diff --interval 3",
        ],
        "http": [
            "sq stream http --url https://example.com/video.mp4 --mode full",
        ],
    }
    
    source = args.source
    
    if source in ["rtsp", "hls", "youtube", "twitch", "http"] and not args.url:
        show_examples(f"stream {source}", examples.get(source, []), "url")
        return 1
    
    # Handle continuous screen monitoring
    if source == "screen" and args.continuous:
        print("=" * 60)
        print("CONTINUOUS SCREEN MONITORING")
        print("=" * 60)
        print(f"Mode: {args.mode}")
        print(f"Interval: {args.interval}s")
        print("Press Ctrl+C to stop")
        print("-" * 60)
        
        try:
            f = flow(f"stream://screen?mode={args.mode}&interval={args.interval}&duration=0")
            for result in f.stream():
                if result.get("type") == "stopped":
                    break
                ts = result.get("timestamp", "?")
                if args.mode == "diff":
                    if result.get("type") == "change":
                        print(f"\n🔵 [{ts}] CHANGE: {result.get('changes', '')[:100]}")
                    else:
                        print(f"⚪ [{ts}] No change", end="\r")
                else:
                    print(f"\n📹 [{ts}] {result.get('description', '')[:100]}")
        except KeyboardInterrupt:
            print("\n\n👋 Monitoring stopped")
        return 0
    
    # Build URI
    uri = f"stream://{source}?"
    
    if args.url:
        uri += f"url={args.url}&"
    if args.mode:
        uri += f"mode={args.mode}&"
    if args.interval:
        uri += f"interval={args.interval}&"
    if args.duration:
        uri += f"duration={args.duration}&"
    if args.device:
        uri += f"device={args.device}&"
    if args.model:
        uri += f"model={args.model}&"
    if args.prompt:
        uri += f"prompt={args.prompt}&"
    if getattr(args, 'focus', None):
        uri += f"focus={args.focus}&"
    if getattr(args, 'zone', None):
        uri += f"zone={args.zone}&"
    if getattr(args, 'sensitivity', None):
        uri += f"sensitivity={args.sensitivity}&"
    
    save_frames = getattr(args, 'file', None) is not None
    if save_frames:
        uri += "save_frames=true&"
    
    try:
        result = flow(uri).run()
        
        if getattr(args, 'file', None):
            _save_stream_html_report(result, args.file)
            print(f"📄 Report saved to: {args.file}")
        
        if not args.quiet:
            output_format = _get_output_format(args)
            _print_stream_result(result, output_format)
        
        return 0
    except Exception as e:
        print(f"Stream analysis failed: {e}", file=sys.stderr)
        print("\nRequirements:")
        print("  - ffmpeg (all sources)")
        print("  - yt-dlp (YouTube): pip install yt-dlp")
        print("  - streamlink (Twitch): pip install streamlink")
        print("  - scrot (screen): sudo apt-get install scrot")
        print("  - ollama pull llava (AI)")
        return 1


def _save_stream_html_report(result: dict, output_file: str):
    """Save stream analysis as HTML report with embedded images"""
    from datetime import datetime
    from pathlib import Path
    
    output_path = Path(output_file).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_file = str(output_path)
    
    timeline = result.get("timeline", [])
    changes = result.get("significant_changes", 0)
    source = result.get("source", "Unknown")
    mode = result.get("mode", "diff")
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stream Analysis Report</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-900 text-white min-h-screen p-8">
    <div class="max-w-6xl mx-auto">
        <header class="mb-8">
            <h1 class="text-3xl font-bold">📹 Stream Analysis Report</h1>
            <p class="text-gray-400 mt-2">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </header>
        
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div class="bg-gray-800 rounded-lg p-4">
                <div class="text-2xl font-bold">{len(timeline)}</div>
                <div class="text-gray-400">Frames Analyzed</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-4">
                <div class="text-2xl font-bold {'text-red-400' if changes > 0 else 'text-green-400'}">{changes}</div>
                <div class="text-gray-400">Changes Detected</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-4">
                <div class="text-lg font-mono">{mode}</div>
                <div class="text-gray-400">Analysis Mode</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-4">
                <div class="text-lg">{'🔴 ACTIVITY' if changes > 0 else '✅ STABLE'}</div>
                <div class="text-gray-400">Status</div>
            </div>
        </div>
        
        <div class="bg-gray-800 rounded-lg p-4 mb-8">
            <div class="text-gray-400 text-sm">Source</div>
            <div class="font-mono text-sm break-all">{source}</div>
        </div>
        
        <h2 class="text-2xl font-bold mb-4">Timeline</h2>
        <div class="space-y-6">
"""
    
    for event in timeline:
        frame = event.get("frame", 0)
        ts = event.get("timestamp", "")
        event_type = event.get("type", "")
        desc = event.get("changes", event.get("description", ""))
        image_b64 = event.get("image_base64", "")
        
        status_class = "border-red-500 bg-red-900/20" if event_type == "change" else "border-gray-600 bg-gray-800"
        status_badge = '<span class="bg-red-600 text-white px-2 py-1 rounded text-sm">🔴 CHANGE</span>' if event_type == "change" else '<span class="bg-gray-600 text-white px-2 py-1 rounded text-sm">⚪ Stable</span>'
        
        html += f"""
            <div class="border-2 {status_class} rounded-lg p-4">
                <div class="flex justify-between items-center mb-4">
                    <div class="flex items-center gap-4">
                        <span class="text-xl font-bold">Frame {frame}</span>
                        <span class="text-gray-400">{ts}</span>
                    </div>
                    {status_badge}
                </div>
"""
        
        if image_b64:
            html += f"""
                <div class="mb-4">
                    <img src="data:image/jpeg;base64,{image_b64}" 
                         class="max-w-full h-auto rounded-lg border border-gray-600"
                         alt="Frame {frame}">
                </div>
"""
        
        if desc:
            html += f"""
                <div class="bg-gray-900 rounded p-4 text-sm">
                    <pre class="whitespace-pre-wrap font-sans">{desc[:1000]}</pre>
                </div>
"""
        
        html += """
            </div>
"""
    
    html += f"""
        </div>
        
        <footer class="mt-8 pt-4 border-t border-gray-700 text-gray-500 text-sm">
            <p>Generated by Streamware • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </footer>
    </div>
</body>
</html>
"""
    
    with open(output_file, "w") as f:
        f.write(html)


def _print_stream_result(result: dict, fmt: str = "yaml"):
    """Print stream analysis result in specified format"""
    if fmt == "json":
        print(json.dumps(result, indent=2))
        return
    
    if fmt == "table":
        _print_stream_table(result)
        return
    
    _print_stream_yaml(result)


def _print_stream_yaml(result: dict):
    """Print stream result as YAML with clear change indicators"""
    timeline = result.get("timeline", [])
    changes = result.get("significant_changes", 0)
    frames = result.get("frames_analyzed", len(timeline))
    source = result.get("source", "")
    mode = result.get("mode", "diff")
    
    print(f"# Stream Analysis")
    print(f"# Source: {source}")
    print(f"# Mode: {mode}")
    print(f"# Frames: {frames}, Changes: {changes}")
    print("---")
    print()
    
    if changes == 0:
        print("status: ✅ NO_CHANGES")
    elif changes == 1:
        print("status: ⚠️ MINOR_ACTIVITY")
    else:
        print(f"status: 🔴 ACTIVITY_DETECTED ({changes} changes)")
    print()
    
    print("timeline:")
    for event in timeline:
        frame = event.get("frame", 0)
        ts = event.get("timestamp", "")
        event_type = event.get("type", "")
        desc = event.get("changes", "")
        
        if event_type == "change":
            indicator = "🔴 CHANGE"
        else:
            indicator = "⚪ stable"
        
        print(f"  - frame: {frame}")
        print(f"    time: \"{ts}\"")
        print(f"    status: {indicator}")
        
        if event_type == "change":
            if "NEW:" in desc or "REMOVED:" in desc or "MOVED:" in desc:
                print(f"    diff: |")
                for line in desc.split("\n"):
                    line = line.strip()
                    if line.startswith("NEW:") or line.startswith("1."):
                        print(f"      + {line}")
                    elif line.startswith("REMOVED:") or line.startswith("2."):
                        print(f"      - {line}")
                    elif line.startswith("MOVED:") or line.startswith("3."):
                        print(f"      ~ {line}")
                    elif line.startswith("ACTION:") or line.startswith("4."):
                        print(f"      ! {line}")
                    elif line:
                        print(f"        {line[:100]}")
            else:
                short = desc[:200].replace("\n", " ").strip()
                print(f"    description: \"{short}...\"")
        print()
    
    print("# Summary")
    print("summary:")
    print(f"  total_frames: {frames}")
    print(f"  changes_detected: {changes}")
    print(f"  change_ratio: {changes/frames*100:.1f}%" if frames > 0 else "  change_ratio: 0%")
    
    print()
    print(f"# Quick check: {'ACTIVITY' if changes > 0 else 'STABLE'}")


def _print_stream_table(result: dict):
    """Print stream result as ASCII table"""
    timeline = result.get("timeline", [])
    changes = result.get("significant_changes", 0)
    source = result.get("source", "")
    
    print(f"# Stream Analysis: {source}")
    print(f"# Changes: {changes} / {len(timeline)} frames")
    print()
    
    print("+-------+----------+----------+--------------------------------------------------+")
    print("| Frame | Time     | Status   | Description                                      |")
    print("+=======+==========+==========+==================================================+")
    
    for event in timeline:
        frame = event.get("frame", 0)
        ts = event.get("timestamp", "")
        event_type = event.get("type", "")
        desc = event.get("changes", "")[:45].replace("\n", " ")
        
        status = "🔴 CHANGE" if event_type == "change" else "⚪ stable"
        
        print(f"| {frame:5} | {ts:8} | {status:8} | {desc:48} |")
    
    print("+-------+----------+----------+--------------------------------------------------+")
    print()
    print(f"Result: {'🔴 ACTIVITY DETECTED' if changes > 0 else '✅ NO CHANGES'}")


def handle_network(args) -> int:
    """Handle network scanning command"""
    flow = _get_flow()
    
    examples = {
        "scan": [
            "sq network scan",
            "sq network scan --subnet 192.168.1.0/24",
            "sq network scan --format json",
            "sq network scan --table",
        ],
        "find": [
            "sq network find 'raspberry pi'",
            "sq network find 'cameras'",
            "sq network find 'printers'",
            "sq network find 'servers'",
        ],
        "identify": [
            "sq network identify --ip 192.168.1.100",
        ],
        "ports": [
            "sq network ports --ip 192.168.1.100",
        ],
    }
    
    op = args.operation
    
    if op == "find" and not args.query:
        show_examples("network find", examples["find"], "query")
        return 1
    if op in ["identify", "ports"] and not args.ip:
        show_examples(f"network {op}", examples.get(op, []), "ip")
        return 1
    
    output_format = _get_output_format(args)
    
    uri = f"network://{op}?"
    
    if args.query:
        uri += f"query={args.query}&"
    if args.subnet:
        uri += f"subnet={args.subnet}&"
    if args.ip:
        uri += f"ip={args.ip}&"
    if args.deep:
        uri += "deep=true&"
    if args.timeout:
        uri += f"timeout={args.timeout}&"
    
    try:
        result = flow(uri).run()
        
        if not args.quiet:
            _print_network_result(result, output_format, op, args.query if hasattr(args, 'query') else None)
        
        return 0
        
    except Exception as e:
        print(f"Network scan failed: {e}", file=sys.stderr)
        print("\nRequirements (install for better results):")
        print("  - nmap: sudo apt-get install nmap")
        print("  - arp-scan: sudo apt-get install arp-scan")
        return 1


def _print_network_result(result: dict, fmt: str, op: str, query: str = None):
    """Print network scan result in specified format"""
    
    if fmt == "json":
        print(json.dumps(result, indent=2))
        return
    
    if fmt == "yaml":
        _print_network_yaml(result, op, query)
        return
    
    if fmt == "table":
        _print_network_table(result, op, query)
        return


def _print_network_yaml(result: dict, op: str, query: str = None):
    """Print result as YAML"""
    devices = result.get("devices", [])
    by_type = result.get("by_type", {})
    
    if op == "find" and query:
        print(f"# Network Search: '{query}'")
        print(f"# Found: {result.get('matched_devices', len(devices))} devices")
    else:
        print(f"# Network Scan: {result.get('subnet', 'N/A')}")
        print(f"# Total: {result.get('total_devices', len(devices))} devices")
    print("---")
    print()
    
    for dtype in sorted(by_type.keys()):
        type_devices = by_type[dtype]
        desc = type_devices[0].get("description", dtype) if type_devices else dtype
        icon = _get_device_icon(dtype)
        
        print(f"{dtype}:  # {icon} {desc}")
        for dev in type_devices:
            print(f"  - ip: {dev.get('ip')}")
            if dev.get('hostname'):
                print(f"    hostname: {dev.get('hostname')}")
            if dev.get('mac'):
                print(f"    mac: \"{dev.get('mac')}\"")
            if dev.get('vendor'):
                print(f"    vendor: {dev.get('vendor')}")
            if dev.get('open_ports'):
                print(f"    ports: {dev.get('open_ports')}")
            if dev.get('services'):
                svc_names = [s.get('name') for s in dev.get('services', [])]
                print(f"    services: [{', '.join(svc_names)}]")
            
            conn = dev.get('connection', {})
            if conn:
                if 'rtsp' in conn:
                    print(f"    rtsp:")
                    for url in conn['rtsp'][:2]:
                        print(f"      - \"{url}\"")
                    if conn.get('default_credentials'):
                        print(f"    credentials: \"{conn['default_credentials']}\"")
                if 'print_url' in conn:
                    print(f"    print_url: \"{conn['print_url']}\"")
                if 'ipp_url' in conn:
                    print(f"    ipp_url: \"{conn['ipp_url']}\"")
                if 'web_ui' in conn:
                    print(f"    web_ui: \"{conn['web_ui']}\"")
                if 'notes' in conn:
                    print(f"    notes: \"{conn['notes']}\"")
        print()
    
    print("# Summary")
    print("summary:")
    for dtype in sorted(by_type.keys()):
        print(f"  {dtype}: {len(by_type[dtype])}")


def _print_network_table(result: dict, op: str, query: str = None):
    """Print result as ASCII table"""
    devices = result.get("devices", [])
    
    if op == "find" and query:
        print(f"# Network Search: '{query}' - Found {len(devices)} devices")
    else:
        print(f"# Network Scan: {result.get('subnet', 'N/A')} - {len(devices)} devices")
    print()
    
    print("+" + "-" * 17 + "+" + "-" * 22 + "+" + "-" * 19 + "+" + "-" * 20 + "+")
    print(f"| {'IP':<15} | {'Hostname':<20} | {'MAC':<17} | {'Type':<18} |")
    print("+" + "=" * 17 + "+" + "=" * 22 + "+" + "=" * 19 + "+" + "=" * 20 + "+")
    
    for device in sorted(devices, key=lambda d: (d.get('type', 'zzz'), d.get('ip', ''))):
        ip = device.get('ip', '')[:15]
        hostname = (device.get('hostname') or 'N/A')[:20]
        mac = (device.get('mac') or 'N/A')[:17]
        dtype = device.get('description', 'Unknown')[:18]
        print(f"| {ip:<15} | {hostname:<20} | {mac:<17} | {dtype:<18} |")
    
    print("+" + "-" * 17 + "+" + "-" * 22 + "+" + "-" * 19 + "+" + "-" * 20 + "+")
    
    by_type = result.get("by_type", {})
    if by_type:
        print()
        print("Summary:")
        for dtype in sorted(by_type.keys()):
            icon = _get_device_icon(dtype)
            print(f"  {icon} {dtype}: {len(by_type[dtype])}")


def _get_device_icon(device_type: str) -> str:
    """Get emoji icon for device type"""
    icons = {
        "raspberry_pi": "🍓",
        "camera": "📷",
        "printer": "🖨️",
        "router": "📡",
        "nas": "💾",
        "smart_tv": "📺",
        "iot_device": "🏠",
        "gpu_server": "🎮",
        "server": "🖥️",
        "workstation": "💻",
        "mobile": "📱",
        "unknown": "❓",
    }
    return icons.get(device_type, "❓")


def handle_config(args) -> int:
    """Handle configuration management command"""
    from .config import config, CONFIG_CATEGORIES, run_config_web
    from pathlib import Path
    
    if args.web:
        run_config_web(port=args.port)
        return 0
    
    if args.show:
        from .diagnostics import print_active_configuration
        print_active_configuration()
        return 0
    
    if args.set:
        key, value = args.set
        config.set(key, value)
        print(f"✅ Set {key}={value}")
        if args.save:
            config.save(keys_only=[key])
            print(f"💾 Saved to .env")
        else:
            print(f"💡 Use --save to persist to .env")
        return 0
    
    if args.save:
        config.save(full=True)
        print(f"💾 Configuration saved to .env (full)")
        return 0
    
    if args.init:
        example = Path(".env.example")
        env_file = Path(".env")
        
        if env_file.exists():
            print("⚠️  .env already exists. Use --show to view or --save to update.")
            return 1
        
        if example.exists():
            import shutil
            shutil.copy(example, env_file)
            print(f"✅ Created .env from .env.example")
        else:
            config.save(env_file, full=True)
            print(f"✅ Created .env with default values")
        
        print(f"📝 Edit .env to customize your settings")
        print(f"🌐 Or use: sq config --web")
        return 0
    
    print("Streamware Configuration")
    print()
    print("Usage:")
    print("  sq config --show           Show current configuration")
    print("  sq config --web            Open web configuration panel")
    print("  sq config --set KEY VALUE  Set configuration value")
    print("  sq config --save           Save configuration to .env")
    print("  sq config --init           Create .env from defaults")
    print()
    print("Examples:")
    print("  sq config --set SQ_MODEL llava:13b --save")
    print("  sq config --set SQ_STREAM_FOCUS person --save")
    print("  sq config --web --port 9000")
    
    return 0
