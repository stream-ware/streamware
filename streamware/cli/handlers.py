"""
CLI Command Handlers

Each handler implements a specific CLI subcommand.
"""

import argparse
import sys
from typing import Optional

from ..config import config
from ..llm_intent import parse_command, LLMIntent


# =============================================================================
# WATCH HANDLER
# =============================================================================

def handle_watch(args: argparse.Namespace) -> int:
    """
    Handle the 'watch' command.
    
    Supports both natural language intent and explicit CLI options.
    """
    from ..core import flow
    
    # Parse natural language intent if provided
    intent: Optional[LLMIntent] = None
    if args.intent:
        print(f"🧠 Parsing: \"{args.intent}\"")
        intent = parse_command(
            args.intent,
            provider="auto",
            model=getattr(args, "llm_model", None)
        )
        print(f"✅ Intent: {intent.describe()}")
        print(f"   CLI: {intent.to_cli_string()}")
        print()
        
        # Apply intent to config
        for key, value in intent.to_env().items():
            config.set(key, value)
        
        # Save notification addresses to .env
        _save_intent_to_env(intent)
    
    # Resolve URL
    url = args.url or args.source or (intent.url if intent else None)
    if not url:
        url = config.get("SQ_DEFAULT_URL")
    
    if not url:
        print("❌ Error: No video source specified")
        print("   Use --url or set SQ_DEFAULT_URL in .env")
        return 1
    
    # Build parameters from intent + explicit args
    detect_target = args.detect or (intent.target if intent else "motion")
    mode = args.mode or (intent.mode if intent else "hybrid")
    duration = args.duration or (intent.duration if intent else 60)
    fps = args.fps or (intent.fps if intent else 2.0)
    tts = args.tts or (intent.tts_enabled if intent else False)
    
    # Notifications
    notify_email = args.email or (intent.notify_email if intent else None)
    notify_mode = getattr(args, "notify_mode", None) or (intent.notify_mode if intent else "digest")
    
    if notify_email:
        config.set("SQ_NOTIFY_EMAIL", notify_email)
        config.set("SQ_NOTIFY_MODE", notify_mode)
    
    # Print summary
    print(f"🎯 Watch: {detect_target} | Mode: {mode} | Duration: {duration}s")
    print(f"   Source: {url[:50]}...")
    if notify_email:
        print(f"   📧 Notify: {notify_email} ({notify_mode})")
    print()
    
    # Build flow URI
    uri = f"live://narrator?source={url}"
    uri += f"&mode={mode}"
    uri += f"&focus={detect_target}"
    uri += f"&duration={duration}"
    uri += f"&fps={fps}"
    if tts:
        uri += "&tts=true"
    if args.quiet:
        uri += "&quiet=true"
    if args.verbose:
        uri += "&verbose=true"
    
    try:
        result = flow(uri).run()
        return 0
    except KeyboardInterrupt:
        print("\n🛑 Stopped")
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def _save_intent_to_env(intent: LLMIntent):
    """Save user-provided notification addresses to .env."""
    saved = []
    
    if intent.notify_email:
        current = config.get("SQ_EMAIL_TO", "")
        if intent.notify_email not in current:
            config.set("SQ_EMAIL_TO", intent.notify_email)
            saved.append(f"email: {intent.notify_email}")
    
    if intent.notify_slack:
        config.set("SQ_SLACK_CHANNEL", intent.notify_slack)
        saved.append(f"slack: {intent.notify_slack}")
    
    if intent.notify_telegram:
        config.set("SQ_TELEGRAM_CHAT_ID", intent.notify_telegram)
        saved.append(f"telegram: {intent.notify_telegram}")
    
    if saved:
        try:
            config.save()
            print(f"💾 Saved to .env: {', '.join(saved)}")
        except Exception as e:
            print(f"⚠️  Could not save to .env: {e}")


# =============================================================================
# LIVE HANDLER
# =============================================================================

def handle_live(args: argparse.Namespace) -> int:
    """Handle the 'live' command for real-time narration."""
    from ..core import flow
    
    url = args.url
    if not url:
        print("❌ Error: --url is required")
        return 1
    
    uri = f"live://narrator?source={url}"
    uri += f"&mode={args.mode}"
    if args.focus:
        uri += f"&focus={args.focus}"
    uri += f"&duration={args.duration}"
    if args.tts:
        uri += "&tts=true"
    if args.quiet:
        uri += "&quiet=true"
    
    try:
        print(f"🎬 Starting live narration...")
        print(f"   Source: {url[:50]}...")
        result = flow(uri).run()
        return 0
    except KeyboardInterrupt:
        print("\n🛑 Stopped")
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


# =============================================================================
# DETECT HANDLER
# =============================================================================

def handle_detect(args: argparse.Namespace) -> int:
    """Handle the 'detect' command for single-frame analysis."""
    from ..smart_detector import SmartDetector
    import json
    
    detector = SmartDetector()
    
    try:
        result = detector.detect(
            args.source,
            target=args.target,
            mode=args.mode
        )
        
        if args.format == "json":
            print(json.dumps(result, indent=2))
        elif args.format == "yaml":
            import yaml
            print(yaml.dump(result, default_flow_style=False))
        else:
            print(f"Detected: {result.get('objects', [])}")
        
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


# =============================================================================
# CONFIG HANDLER
# =============================================================================

def handle_config(args: argparse.Namespace) -> int:
    """Handle the 'config' command."""
    if args.show:
        print("📋 Current Configuration:")
        print()
        for key in sorted(config._cache.keys()):
            value = config.get(key)
            # Hide sensitive values
            if any(s in key.upper() for s in ["PASS", "KEY", "TOKEN", "SECRET"]):
                value = "*" * len(str(value)) if value else "(not set)"
            print(f"  {key}={value}")
        return 0
    
    if args.get:
        value = config.get(args.get)
        print(f"{args.get}={value}")
        return 0
    
    if args.set:
        key, value = args.set
        config.set(key, value)
        config.save()
        print(f"✅ Set {key}={value}")
        return 0
    
    if args.diagnose:
        return _run_diagnostics()
    
    if args.reset:
        print("⚠️  Reset not implemented yet")
        return 1
    
    # Default: show help
    print("Use --show to view config, --set KEY VALUE to modify")
    return 0


def _run_diagnostics() -> int:
    """Run system diagnostics."""
    print("🔍 Running diagnostics...")
    print()
    
    # Check SMTP
    print("📧 Email Configuration:")
    smtp_host = config.get("SQ_SMTP_HOST")
    smtp_user = config.get("SQ_SMTP_USER")
    print(f"   Host: {smtp_host or '(not set)'}")
    print(f"   User: {smtp_user or '(not set)'}")
    
    # Check YOLO
    print()
    print("🎯 YOLO Model:")
    try:
        from ultralytics import YOLO
        print("   ✅ Ultralytics installed")
    except ImportError:
        print("   ❌ Ultralytics not installed")
    
    # Check Ollama
    print()
    print("🤖 LLM (Ollama):")
    import requests
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=2)
        if resp.ok:
            models = [m["name"] for m in resp.json().get("models", [])]
            print(f"   ✅ Ollama running ({len(models)} models)")
        else:
            print("   ⚠️  Ollama not responding")
    except Exception:
        print("   ❌ Ollama not running")
    
    return 0


# =============================================================================
# TEST HANDLER
# =============================================================================

def handle_test(args: argparse.Namespace) -> int:
    """Handle the 'test' command."""
    component = args.component
    
    if component == "email" or component == "all":
        print("📧 Testing email...")
        try:
            from ..notifier import notify
            to = args.to or config.get("SQ_EMAIL_TO")
            if to:
                notify(f"Test email from Streamware at {__import__('datetime').datetime.now()}")
                print(f"   ✅ Email sent to {to}")
            else:
                print("   ⚠️  No email address configured (use --to or set SQ_EMAIL_TO)")
        except Exception as e:
            print(f"   ❌ Email failed: {e}")
    
    if component == "camera" or component == "all":
        print("📹 Testing camera...")
        url = args.url or config.get("SQ_DEFAULT_URL")
        if url:
            try:
                import cv2
                cap = cv2.VideoCapture(url)
                ret, frame = cap.read()
                cap.release()
                if ret:
                    print(f"   ✅ Camera working ({frame.shape})")
                else:
                    print("   ❌ Could not read frame")
            except Exception as e:
                print(f"   ❌ Camera error: {e}")
        else:
            print("   ⚠️  No camera URL configured")
    
    if component == "tts" or component == "all":
        print("🔊 Testing TTS...")
        try:
            from ..tts_worker import TTSWorker
            worker = TTSWorker()
            worker.speak("Test speech from Streamware")
            worker.stop()
            print("   ✅ TTS working")
        except Exception as e:
            print(f"   ❌ TTS failed: {e}")
    
    if component == "yolo" or component == "all":
        print("🎯 Testing YOLO...")
        try:
            from ultralytics import YOLO
            model = YOLO("yolo11n.pt")
            print("   ✅ YOLO model loaded")
        except Exception as e:
            print(f"   ❌ YOLO failed: {e}")
    
    if component == "llm" or component == "all":
        print("🤖 Testing LLM...")
        try:
            from ..llm_intent import parse_command
            intent = parse_command("detect person")
            if intent.llm_model:
                print(f"   ✅ LLM working ({intent.llm_model})")
            else:
                print("   ⚠️  Using heuristics fallback")
        except Exception as e:
            print(f"   ❌ LLM failed: {e}")
    
    return 0
