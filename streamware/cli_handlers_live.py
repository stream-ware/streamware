"""
CLI Handlers - Live Narrator Command

Large handler for live narration with TTS and triggers.
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


def _handle_reader(args) -> int:
    """Handle live reader operation (OCR + LLM vision)."""
    from .components.frame_reader import FrameReaderComponent
    from .core import StreamwareURI
    
    url = args.url
    if not url:
        print("❌ Error: --url parameter is required.", file=sys.stderr)
        print("\nExamples:")
        print("  sq live reader --url rtsp://192.168.1.100/stream --ocr")
        print("  sq live reader --url /dev/video0 --ocr --llm-query 'what do you see?'")
        print("  sq live reader --url screen:// --ocr --lang pol --tts")
        return 1
    
    uri_str = f"live://reader?url={url}"
    
    if getattr(args, 'ocr', True):
        uri_str += "&ocr=true"
    ocr_engine = getattr(args, 'ocr_engine', 'tesseract')
    uri_str += f"&ocr_engine={ocr_engine}"
    
    lang = getattr(args, 'lang', 'eng')
    uri_str += f"&lang={lang}"
    
    llm_query = getattr(args, 'llm_query', None)
    if llm_query:
        uri_str += f"&llm=true&query={llm_query}"
    
    model = getattr(args, 'model', 'llava:7b')
    uri_str += f"&model={model}"
    
    interval = getattr(args, 'interval', 2.0) or 2.0
    duration = getattr(args, 'duration', 60)
    uri_str += f"&interval={interval}&duration={duration}"
    
    if getattr(args, 'continuous', False):
        uri_str += "&continuous=true"
    
    if getattr(args, 'tts', False):
        tts_lang = 'pl' if lang == 'pol' else ('de' if lang == 'deu' else 'en')
        uri_str += f"&tts=true&tts_lang={tts_lang}"
    
    if getattr(args, 'tts_diff', False):
        uri_str += "&diff=true"
    
    try:
        uri = StreamwareURI(uri_str)
        component = FrameReaderComponent(uri)
        result = component.process()
        
        fmt = _get_output_format(args)
        if fmt == "json":
            print(json.dumps(result, indent=2, default=str))
        else:
            print("\n# Frame Reader Results")
            print("---")
            print(f"frames: {result.get('frames', 0)}")
            print(f"analyses: {result.get('analyses', 0)}")
            if result.get('history'):
                print("recent_extractions:")
                for h in result['history'][-5:]:
                    if h.get('ocr') and h['ocr'].get('text'):
                        print(f"  - \"{h['ocr']['text'][:60]}...\"")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


def handle_live(args) -> int:
    """Handle live narration command"""
    flow = _get_flow()
    from .components.live_narrator import LiveNarratorComponent
    
    op = getattr(args, 'operation', 'narrator') or 'narrator'
    url = args.url
    
    if op == 'reader':
        return _handle_reader(args)
    
    if not url:
        print("❌ Error: --url parameter is required (and cannot be empty).", file=sys.stderr)
        print("\nExamples:")
        print("  sq live narrator --url rtsp://192.168.1.100/stream")
        print("  sq live narrator --url /path/to/video.mp4")
        return 1
    
    auto_config = None
    if getattr(args, 'auto', False):
        from .performance_manager import auto_configure
        print("\n🔧 Auto-configuring based on hardware...", flush=True)
        auto_config = auto_configure()
        
        if not getattr(args, 'model', None):
            args.model = auto_config.vision_model
        if not getattr(args, 'interval', None):
            args.interval = auto_config.base_interval
        print()
    
    if getattr(args, 'benchmark', False):
        from .timing_logger import run_benchmark
        print("\n⏱️  Running performance benchmark...", flush=True)
        bench = run_benchmark()
        print(f"   CPU: {bench['cpu_benchmark_ms']:.1f}ms (1M iterations)")
        if bench.get('opencv_available'):
            print(f"   OpenCV: {bench['opencv_benchmark_ms']:.1f}ms (image processing)")
        print(f"   Recommended interval: {bench['recommendations']['interval']}s")
        print(f"   Recommended model: {bench['recommendations']['vision_model']}")
        print(f"   Use HOG detection: {bench['recommendations']['use_hog']}")
        print()
    
    from .config import config
    
    vision_model = getattr(args, 'model', None) or config.get("SQ_MODEL", "llava:7b")
    guarder_model = config.get("SQ_GUARDER_MODEL", "gemma:2b")
    check_tts = getattr(args, 'tts', False)
    
    if check_tts:
        print(f"🔊 TTS requested via --tts flag")
    
    if getattr(args, 'turbo', False):
        print("🚀 TURBO mode: skip checks + fast model + aggressive caching")
        args.skip_checks = True
        args.fast = True
        if not getattr(args, 'model', None):
            args.model = 'llava:7b'
        vision_model = args.model
    
    if getattr(args, 'fast', False) and not getattr(args, 'model', None):
        fast_models = ['llava:7b', 'llava', 'llava:13b', 'bakllava']
        from .setup_utils import check_ollama_model
        for fast_model in fast_models:
            if check_ollama_model(fast_model):
                args.model = fast_model
                vision_model = fast_model
                print(f"⚡ Fast mode enabled: using {fast_model} model, aggressive caching")
                break
    
    skip_checks = getattr(args, 'skip_checks', False)
    
    if skip_checks:
        print("⚡ Skipping dependency checks")
    elif isinstance(vision_model, str) and not vision_model.startswith("gpt"):
        from .setup_utils import run_startup_checks
        
        checks = run_startup_checks(
            vision_model=vision_model,
            guarder_model=guarder_model,
            check_tts=check_tts,
            interactive=True
        )
        
        if not checks.get("llm", False):
            print("\n❌ Cannot start without working LLM configuration.")
            return 1
        
        if not checks["ollama"]:
            print("\n❌ Cannot start without Ollama. Please install and run: ollama serve")
            return 1
        
        if not checks["vision_model"]:
            print("\n❌ Vision model required. Install with: ollama pull " + vision_model)
            return 1
        
        if check_tts and not checks["tts"]:
            print("⚠️  TTS not available, continuing without voice output.")
            args.tts = False
        
        if not checks["guarder_model"]:
            print("ℹ️  Using regex-based filtering (guarder model not available)")
    
    mode = getattr(args, 'mode', 'full') or 'full'
    quiet = getattr(args, 'quiet', False)
    
    intent_str = getattr(args, 'intent', None)
    if intent_str and isinstance(intent_str, str):
        from .detection_pipeline import parse_user_intent
        intent, intent_params = parse_user_intent(intent_str)
        
        print(f"🎯 Intent: {intent.name}")
        print(f"   Focus: {intent_params.get('focus', 'person')}")
        print(f"   Sensitivity: {intent_params.get('sensitivity', 'medium')}")
        
        mode = "track"
        if not getattr(args, 'focus', None):
            args.focus = intent_params.get('focus', 'person')
        
        config.set("SQ_INTENT", intent_str)
        config.set("SQ_INTENT_TYPE", intent.name)
    
        from .setup_utils import check_ollama_model
        if not getattr(args, 'model', None):
            if check_ollama_model("llava:7b")[0]:
                args.model = "llava:7b"
            elif check_ollama_model("llava")[0]:
                args.model = "llava"
            elif check_ollama_model("bakllava")[0]:
                args.model = "bakllava"
        config.set("SQ_FAST_MODE", "true")
        print(f"⚡ Fast mode enabled: using {args.model} model, aggressive caching")
    
    uri = f"live://{op}?source={url}"
    tts_value = 'true' if args.tts else 'false'
    uri += f"&tts={tts_value}"

    tts_mode = 'normal'
    if getattr(args, 'tts_all', False):
        tts_mode = 'all'
    elif getattr(args, 'tts_diff', False):
        tts_mode = 'diff'
    uri += f"&tts_mode={tts_mode}"
    
    if args.tts:
        print(f"🔊 TTS enabled (--tts flag detected, mode={tts_mode})")
    uri += f"&mode={mode}"
    uri += f"&duration={args.duration}"
    
    analysis = getattr(args, 'analysis', 'normal') or 'normal'
    motion = getattr(args, 'motion', 'significant') or 'significant'
    frames = getattr(args, 'frames', 'changed') or 'changed'
    
    uri += f"&analysis={analysis}"
    uri += f"&motion={motion}"
    uri += f"&frames_mode={frames}"
    
    focus = getattr(args, 'focus', None)
    if focus:
        uri += f"&focus={focus}"
    
    if intent_str and isinstance(intent_str, str):
        import urllib.parse
        uri += f"&intent={urllib.parse.quote(intent_str)}"
    
    if getattr(args, 'verbose', False):
        uri += "&verbose=true"
    
    use_ramdisk = getattr(args, 'ramdisk', True) and not getattr(args, 'no_ramdisk', False)
    uri += f"&ramdisk={'true' if use_ramdisk else 'false'}"
    
    if getattr(args, 'frames_dir', None):
        uri += f"&frames_dir={args.frames_dir}"
    
    if getattr(args, 'interval', None):
        uri += f"&interval={args.interval}"
    if getattr(args, 'threshold', None):
        uri += f"&threshold={args.threshold}"
    
    if getattr(args, 'trigger', None):
        uri += f"&trigger={args.trigger}"
    if getattr(args, 'focus', None):
        uri += f"&focus={args.focus}"
    if getattr(args, 'webhook', None):
        uri += f"&webhook_url={args.webhook}"
    model_param = getattr(args, 'model', None) or vision_model
    uri += f"&model={model_param}"
    if getattr(args, 'lite', False):
        uri += "&lite=true"
    if getattr(args, 'quiet', False):
        uri += "&quiet=true"
    lang = getattr(args, 'lang', 'en')
    if lang and lang != 'en':
        uri += f"&lang={lang}"
    if getattr(args, 'realtime', False):
        uri += "&realtime=true"
    if getattr(args, 'dsl_only', False):
        uri += "&dsl_only=true"
    if getattr(args, 'fps', None):
        uri += f"&target_fps={args.fps}"
    
    if getattr(args, 'guarder', False):
        config.set("SQ_USE_GUARDER", "true")
    
    log_file = getattr(args, 'log_file', None)
    log_format = getattr(args, 'log_format', 'csv')
    
    uri += f"&log_format={log_format}"
    
    if log_file and isinstance(log_file, str):
        from .timing_logger import set_log_file
        set_log_file(log_file, verbose=getattr(args, 'verbose', False))
        print(f"📊 Timing logs will be saved to: {log_file} (format: {log_format})")
        uri += f"&log_file={log_file}"
    
    fmt = _get_output_format(args)
    if fmt in ("json", "yaml"):
        uri += "&quiet=true"
    
    show_header = not quiet and fmt not in ("json", "yaml")
    if show_header:
        print(f"\n🎙️ Live Narrator ({mode} mode)")
        print(f"   Source: {url[:50]}...")
        print(f"   TTS: {'ON' if args.tts else 'OFF'}")
        if getattr(args, 'focus', None):
            print(f"   Focus: {args.focus}")
        print()
    
    try:
        result = flow(uri).run()
        
        if fmt == "json":
            print(json.dumps(result, indent=2, default=str))
        else:
            _print_live_yaml(result, mode)
        
        log_format = getattr(args, 'log', None)
        if getattr(args, 'file', None):
            if log_format == 'md':
                _save_live_markdown_log(result, args.file, mode, url)
            else:
                _save_live_report(result, args.file, mode, url)
        elif log_format == 'md':
            _save_live_markdown_log(result, 'live_log.md', mode, url)
        
        return 0
        
    except Exception as e:
        print(f"Live narration failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def _print_live_yaml(result: dict, mode: str = "full"):
    """Print live narrator result as YAML"""
    op = result.get("operation", "narrator")
    config = result.get("config", {})
    
    print(f"# Live Narrator - {op} ({mode} mode)")
    print("---")
    print()
    
    print("config:")
    print(f"  model: {config.get('model', 'unknown')}")
    print(f"  mode: {config.get('mode', mode)}")
    print(f"  focus: {config.get('focus', 'general')}")
    print(f"  interval: {config.get('interval', 3)}s")
    print(f"  diff_threshold: {config.get('diff_threshold', 15)}")
    print()
    
    if op == "describe":
        desc = result.get("description", "")
        print(f"description: |")
        for line in desc.split('\n'):
            print(f"  {line}")
    elif op == "watch":
        alerts = result.get("alerts", [])
        print(f"triggers: {result.get('triggers', [])}")
        print(f"frames_checked: {result.get('frames_checked', 0)}")
        print(f"alerts_count: {len(alerts)}")
        print()
        if alerts:
            print("alerts:")
            for alert in alerts:
                print(f"  - time: \"{alert.get('timestamp')}\"")
                print(f"    frame: {alert.get('frame')}")
                print(f"    description: \"{alert.get('description', '')}\"")
    else:
        print(f"tts: {config.get('tts_enabled', False)}")
        print(f"duration: {config.get('duration', 0)}s")
        print(f"frames: {result.get('frames_analyzed', 0)}")
        print(f"descriptions: {result.get('descriptions', 0)}")
        print(f"triggers_fired: {result.get('triggers_fired', 0)}")
        print()
        
        history = result.get("history", [])
        if history:
            print("history:")
            for entry in history[-10:]:
                triggered = "🔴 " if entry.get("triggered") else ""
                print(f"  - time: \"{entry.get('timestamp', '')[:19]}\"")
                print(f"    {triggered}description: \"{entry.get('description', '')}\"")
                if entry.get("matches"):
                    print(f"    matches: {entry.get('matches')}")


def _save_live_report(result: dict, output_file: str, mode: str, source: str):
    """Save live narrator report as HTML with images"""
    from pathlib import Path
    from datetime import datetime
    
    output_path = Path(output_file).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    history = result.get("history", [])
    triggers = result.get("triggers_fired", 0)
    config = result.get("config", {})
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Live Narrator Report - {mode} mode</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               max-width: 1200px; margin: 0 auto; padding: 20px; background: #1a1a2e; color: #eee; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                  padding: 25px; border-radius: 12px; margin-bottom: 20px; }}
        h1 {{ margin: 0; }}
        .stats {{ display: flex; gap: 15px; margin-top: 15px; flex-wrap: wrap; }}
        .stat {{ background: rgba(255,255,255,0.1); padding: 10px 20px; border-radius: 8px; }}
        .config {{ background: #16213e; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
        .config-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; }}
        .config-item {{ background: rgba(255,255,255,0.05); padding: 8px 12px; border-radius: 4px; }}
        .config-label {{ color: #888; font-size: 0.8em; }}
        .entry {{ background: #16213e; padding: 20px; margin: 15px 0; border-radius: 12px; 
                 border-left: 4px solid #667eea; }}
        .entry.triggered {{ border-left-color: #e74c3c; background: #1e1e3f; }}
        .images-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px; }}
        .image-box {{ text-align: center; }}
        .image-box img {{ width: 100%; border-radius: 8px; }}
        .image-label {{ color: #888; font-size: 0.8em; margin-top: 5px; }}
        .time {{ color: #888; font-size: 0.9em; margin-bottom: 10px; }}
        .desc {{ line-height: 1.6; font-size: 1.1em; }}
        .analysis-box {{ background: #0f0f23; padding: 12px; border-radius: 6px; margin-top: 10px; font-size: 0.85em; }}
        .no-image {{ background: #0f0f23; padding: 30px; text-align: center; border-radius: 8px; color: #666; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎙️ Live Narrator Report</h1>
        <p>Mode: <strong>{mode}</strong> | Focus: <strong>{config.get('focus', 'general')}</strong></p>
        <div class="stats">
            <div class="stat">📝 {len(history)} descriptions</div>
            <div class="stat">🔔 {triggers} triggers</div>
            <div class="stat">🎞️ {result.get('frames_analyzed', 0)} frames</div>
            <div class="stat">⏱️ {config.get('duration', 0)}s</div>
        </div>
    </div>
    
    <div class="config">
        <h3 style="margin-top: 0;">📋 Analysis Configuration</h3>
        <div class="config-grid">
            <div class="config-item"><div class="config-label">Model</div><div>{config.get('model', 'unknown')}</div></div>
            <div class="config-item"><div class="config-label">Mode</div><div>{config.get('mode', mode)}</div></div>
            <div class="config-item"><div class="config-label">Focus</div><div>{config.get('focus', 'general')}</div></div>
            <div class="config-item"><div class="config-label">Interval</div><div>{config.get('interval', 3)}s</div></div>
            <div class="config-item"><div class="config-label">TTS</div><div>{'✅ Enabled' if config.get('tts_enabled') else '❌ Disabled'}</div></div>
            <div class="config-item"><div class="config-label">Source</div><div style="font-size: 0.8em;">{source[:60]}...</div></div>
        </div>
    </div>
    
    <h2>📸 Frame Analysis</h2>
"""
    
    for i, entry in enumerate(history):
        triggered_class = "triggered" if entry.get("triggered") else ""
        ts = entry.get("timestamp", "")[:19]
        desc = entry.get("description", "")
        original_b64 = entry.get("image_base64", "")
        annotated_b64 = entry.get("annotated_base64", "")
        frame_num = entry.get("frame", i+1)
        
        orig_html = f'<img src="data:image/jpeg;base64,{original_b64}" alt="Original">' if original_b64 else '<div class="no-image">No image</div>'
        
        if annotated_b64:
            annot_html = f'<img src="data:image/jpeg;base64,{annotated_b64}" alt="LLM View">'
        elif original_b64:
            annot_html = f'<img src="data:image/jpeg;base64,{original_b64}" alt="LLM View">'
        else:
            annot_html = '<div class="no-image">No annotation</div>'
        
        html += f"""
    <div class="entry {triggered_class}">
        <div class="time">{'🔴 TRIGGER - ' if entry.get('triggered') else '📷 '}Frame #{frame_num} | {ts}</div>
        <div class="images-row">
            <div class="image-box">{orig_html}<div class="image-label">📷 Original</div></div>
            <div class="image-box">{annot_html}<div class="image-label">🔍 Analyzed</div></div>
        </div>
        <div class="desc">{desc}</div>
    </div>
"""
    
    html += f"""
    <footer style="text-align: center; margin-top: 30px; padding: 20px; color: #666; border-top: 1px solid #333;">
        Generated by Streamware at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </footer>
</body>
</html>"""
    
    with open(output_path, "w") as f:
        f.write(html)
    
    print(f"📄 Report saved: {output_path}")


def _save_live_markdown_log(result: dict, output_file: str, mode: str, source: str):
    """Save live narrator result as Markdown log."""
    from pathlib import Path
    from datetime import datetime

    output_path = Path(output_file).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    op = result.get("operation", "narrator")
    config = result.get("config", {})
    history = result.get("history", [])
    triggers = result.get("triggers", [])

    lines = []
    lines.append(f"# Live Narrator Log ({op}, {mode} mode)")
    lines.append("")
    lines.append(f"- **Source**: `{source}`")
    lines.append(f"- **Model**: `{config.get('model', 'unknown')}`")
    lines.append(f"- **Mode**: `{config.get('mode', mode)}`")
    lines.append(f"- **Focus**: `{config.get('focus', 'general')}`")
    lines.append(f"- **Generated**: {datetime.now().isoformat(timespec='seconds')}")
    lines.append("")

    if triggers:
        lines.append("- **Triggers**:")
        for t in triggers:
            lines.append(f"  - `{t}`")
        lines.append("")

    if history:
        lines.append("## Timeline")
        for entry in history:
            ts = entry.get("timestamp", "")
            desc = entry.get("description", "")
            triggered = entry.get("triggered", False)
            matches = entry.get("matches", [])
            prefix = "🔴" if triggered else "📝"
            short = desc.replace("\n", " ").strip()[:220]
            lines.append(f"- {prefix} **{ts}**  ")
            lines.append(f"  - {short}...")
            if matches:
                lines.append(f"  - **Matches**: {', '.join(matches)}")
            lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")

    print(f"📄 Markdown log saved: {output_path}")
