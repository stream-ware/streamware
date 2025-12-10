"""
Streamware CLI - Command-line interface for stream processing
"""

import sys
import argparse
import json
import asyncio
from pathlib import Path
from typing import Any
from .core import flow, registry
from .diagnostics import enable_diagnostics, metrics
from .exceptions import StreamwareError


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Streamware - Modern Python stream processing framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simple pipeline
  streamware "http://api.example.com/data" --pipe "transform://json" --pipe "file://write?path=output.json"
  
  # Extract data from web
  streamware "curllm://browse?url=https://example.com" --instruction "Extract all links"
  
  # Process Kafka messages
  streamware "kafka://consume?topic=events" --pipe "transform://json" --pipe "postgres://insert?table=events"
  
  # Show available components
  streamware --list-components
  
  # Enable debug logging
  streamware --debug "http://api.example.com" --pipe "transform://json"
        """
    )
    
    parser.add_argument(
        "uri",
        nargs="?",
        help="Starting URI for the pipeline"
    )
    
    parser.add_argument(
        "--pipe", "-p",
        action="append",
        dest="pipes",
        help="Add pipeline step (can be used multiple times)"
    )
    
    parser.add_argument(
        "--data", "-d",
        help="Input data (JSON string or @filename)"
    )
    
    parser.add_argument(
        "--instruction", "-i",
        help="Instruction for CurLLM operations"
    )
    
    parser.add_argument(
        "--output", "-o",
        help="Output file path"
    )
    
    parser.add_argument(
        "--format", "-f",
        choices=["json", "csv", "text"],
        default="json",
        help="Output format"
    )
    
    parser.add_argument(
        "--stream", "-s",
        action="store_true",
        help="Enable streaming mode"
    )
    
    parser.add_argument(
        "--async",
        action="store_true",
        dest="async_mode",
        help="Run in async mode"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Enable trace logging (very verbose)"
    )
    
    parser.add_argument(
        "--metrics",
        action="store_true",
        help="Show metrics after execution"
    )
    
    parser.add_argument(
        "--list-components",
        action="store_true",
        help="List available components"
    )
    
    parser.add_argument(
        "--install-protocol",
        action="store_true",
        help="Install system protocol handler"
    )
    
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Run auto-configuration wizard"
    )
    
    parser.add_argument(
        "--mode",
        choices=["eco", "balance", "performance"],
        default="balance",
        help="Configuration mode (eco, balance, performance)"
    )
    
    parser.add_argument(
        "--check",
        choices=["camera", "tts", "ollama", "all"],
        help="Run diagnostic check (camera, tts, ollama, all)"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0"
    )
    
    args = parser.parse_args()
    
    # Handle special commands
    if args.list_components:
        list_components()
        return 0
        
    if args.install_protocol:
        install_protocol_handler()
        return 0
        
    if args.setup:
        from .setup import run_setup, run_setup_tts

        # Special case: `streamware --setup tts` runs TTS-only wizard
        if args.uri and str(args.uri).lower() == "tts":
            run_setup_tts()
        else:
            run_setup(mode=args.mode)
        return 0

    if args.check:
        return run_diagnostics(args.check, args.uri)

    if not args.uri:
        parser.print_help()
        return 1
        
    # Enable diagnostics if requested
    if args.debug:
        enable_diagnostics(level="DEBUG", use_rich=True)
    elif args.trace:
        enable_diagnostics(level="DEBUG", use_rich=True)
        
    # Process the pipeline
    try:
        result = run_pipeline(args)
        
        # Output results
        output_result(result, args)
        
        # Show metrics if requested
        if args.metrics:
            metrics.print_summary()
            
        return 0
        
    except StreamwareError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


def run_pipeline(args) -> Any:
    """Run the pipeline based on CLI arguments"""
    # Create flow
    pipeline = flow(args.uri)
    
    # Add instruction if specified
    if args.instruction:
        # Modify URI to include instruction
        if "curllm" in args.uri:
            pipeline.steps[0] = f"{args.uri}&instruction={args.instruction}"
            
    # Add pipeline steps
    if args.pipes:
        for pipe in args.pipes:
            pipeline = pipeline | pipe
            
    # Enable diagnostics if trace mode
    if args.trace:
        pipeline = pipeline.with_diagnostics(trace=True)
        
    # Load input data if specified
    data = None
    if args.data:
        if args.data.startswith('@'):
            # Load from file
            file_path = Path(args.data[1:]).expanduser()
            with open(file_path, 'r') as f:
                content = f.read()
                try:
                    data = json.loads(content)
                except json.JSONDecodeError:
                    data = content
        else:
            # Parse as JSON or use as string
            try:
                data = json.loads(args.data)
            except json.JSONDecodeError:
                data = args.data
                
    # Run pipeline
    if args.stream:
        # Streaming mode
        results = []
        for item in pipeline.stream(data):
            results.append(item)
            if not args.output:
                # Print each item as it comes
                print(format_output(item, args.format))
        return results
    elif args.async_mode:
        # Async mode
        return asyncio.run(pipeline.run_async(data))
    else:
        # Normal mode
        return pipeline.run(data)


def output_result(result: Any, args):
    """Output the result based on format and destination"""
    formatted = format_output(result, args.format)
    
    if args.output:
        # Write to file
        output_path = Path(args.output).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.write(formatted)
        print(f"Output written to: {output_path}")
    else:
        # Print to stdout
        print(formatted)


def format_output(data: Any, format: str) -> str:
    """Format output data"""
    if format == "json":
        if isinstance(data, str):
            return data
        return json.dumps(data, indent=2, ensure_ascii=False)
    elif format == "csv":
        if isinstance(data, list) and all(isinstance(item, dict) for item in data):
            import csv
            import io
            output = io.StringIO()
            if data:
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            return output.getvalue()
        return str(data)
    else:  # text
        return str(data)


def list_components():
    """List all registered components"""
    print("Available Streamware Components:")
    print("=" * 50)
    
    components = registry.list_components()
    categories = {
        "Core": ["split", "join", "multicast", "choose", "filter", "aggregate"],
        "Data": ["transform", "jsonpath", "template", "csv", "validate", "enrich"],
        "File": ["file", "file-read", "file-write", "file-watch", "file-lines"],
        "Web": ["http", "https", "rest", "webhook", "graphql", "download"],
        "Automation": ["curllm", "curllm-stream", "web"],
        "Message Brokers": ["kafka", "kafka-produce", "kafka-consume", "rabbitmq", "rabbitmq-publish", "rabbitmq-consume"],
        "Database": ["postgres", "postgresql", "postgres-query", "postgres-insert"],
    }
    
    for category, items in categories.items():
        print(f"\n{category}:")
        for item in items:
            if item in components:
                print(f"  - {item}://")


def install_protocol_handler():
    """Install system protocol handler for stream://"""
    print("Installing stream:// protocol handler...")
    
    # Create handler script
    handler_script = """#!/bin/bash
python3 -m streamware.handler "$1"
"""
    
    handler_path = Path("/usr/local/bin/stream-handler")
    
    # Create desktop file
    desktop_file = """[Desktop Entry]
Type=Application
Name=Streamware Protocol Handler
Exec=/usr/local/bin/stream-handler %u
StartupNotify=false
MimeType=x-scheme-handler/stream;
"""
    
    desktop_path = Path("~/.local/share/applications/stream-protocol-handler.desktop").expanduser()
    
    try:
        # Write handler script
        print(f"Creating handler script at {handler_path}...")
        handler_path.write_text(handler_script)
        handler_path.chmod(0o755)
        
        # Write desktop file
        print(f"Creating desktop file at {desktop_path}...")
        desktop_path.parent.mkdir(parents=True, exist_ok=True)
        desktop_path.write_text(desktop_file)
        
        # Register with xdg-mime
        import subprocess
        subprocess.run([
            "xdg-mime", "default", 
            "stream-protocol-handler.desktop", 
            "x-scheme-handler/stream"
        ])
        
        print("✓ Protocol handler installed successfully!")
        print("You can now use stream:// URLs in your browser or terminal")
        
    except Exception as e:
        print(f"Error installing protocol handler: {e}")
        print("You may need to run with sudo or manually configure the handler")


def _update_env_file(key: str, value: str):
    """Update or add a key in .env file."""
    from .setup_utils import update_env_file
    if update_env_file(key, value):
        print(f"   Updated .env: {key}={value}")


def run_diagnostics(check_type: str, url: str = None) -> int:
    """Run diagnostic checks for camera, TTS, or Ollama.
    
    Args:
        check_type: One of 'camera', 'tts', 'ollama', 'all'
        url: Optional URL for camera check (RTSP/file)
    
    Returns:
        0 if all checks pass, 1 otherwise
    """
    from .config import config
    import subprocess
    import tempfile
    
    results = {}
    all_ok = True
    
    print("\n🔍 Streamware Diagnostics")
    print("=" * 50)
    
    # --- CAMERA CHECK ---
    if check_type in ("camera", "all"):
        print("\n📷 Camera / RTSP Check:")
        
        # Get URL from arg or config
        camera_url = url
        if not camera_url:
            # Try to build from config
            user = config.get("SQ_RTSP_USER", "admin")
            passwd = config.get("SQ_RTSP_PASS", "admin")
            port = config.get("SQ_RTSP_PORT", "554")
            print(f"   No URL provided. Use: streamware --check camera <rtsp://...>")
            results["camera_url"] = "⚠️  NOT PROVIDED"
        else:
            results["camera_url"] = camera_url[:50] + "..." if len(camera_url) > 50 else camera_url
            
            # Test ffmpeg capture
            try:
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
                    temp_path = tf.name
                
                cmd = [
                    "ffmpeg", "-y", "-rtsp_transport", "tcp",
                    "-i", camera_url,
                    "-frames:v", "1", "-q:v", "2",
                    temp_path
                ]
                result = subprocess.run(cmd, capture_output=True, timeout=15)
                
                if result.returncode == 0:
                    import os
                    size = os.path.getsize(temp_path)
                    results["ffmpeg_capture"] = f"✅ OK ({size} bytes)"
                    # Keep temp_path for vision test, will be cleaned up later
                    results["_temp_frame"] = temp_path
                else:
                    results["ffmpeg_capture"] = f"❌ FAILED (exit {result.returncode})"
                    all_ok = False
            except subprocess.TimeoutExpired:
                results["ffmpeg_capture"] = "❌ TIMEOUT"
                all_ok = False
            except FileNotFoundError:
                results["ffmpeg_capture"] = "❌ ffmpeg NOT FOUND"
                all_ok = False
            except Exception as e:
                results["ffmpeg_capture"] = f"❌ ERROR: {e}"
                all_ok = False
        
        for key, val in results.items():
            if key.startswith("camera") or key.startswith("ffmpeg"):
                print(f"   {key}: {val}")
    
    # --- OLLAMA CHECK ---
    if check_type in ("ollama", "camera", "all"):
        print("\n🤖 Ollama / LLM Check:")
        
        ollama_url = config.get("SQ_OLLAMA_URL", "http://localhost:11434")
        model = config.get("SQ_MODEL", "llava:7b")
        
        results["ollama_url"] = ollama_url
        results["model"] = model
        
        try:
            import requests
            
            # Test connection
            resp = requests.get(f"{ollama_url}/api/tags", timeout=5)
            if resp.ok:
                tags = resp.json()
                models = [m.get("name", "") for m in tags.get("models", [])]
                results["ollama_connection"] = "✅ OK"
                
                # Check if model is available
                if any(model in m for m in models):
                    results["model_available"] = f"✅ {model} found"
                else:
                    results["model_available"] = f"⚠️  {model} not found. Available: {', '.join(models[:3])}"
            else:
                results["ollama_connection"] = f"❌ HTTP {resp.status_code}"
                all_ok = False
        except requests.exceptions.ConnectionError:
            results["ollama_connection"] = "❌ CONNECTION REFUSED"
            all_ok = False
        except requests.exceptions.Timeout:
            results["ollama_connection"] = "❌ TIMEOUT"
            all_ok = False
        except Exception as e:
            results["ollama_connection"] = f"❌ ERROR: {e}"
            all_ok = False
        
        for key, val in results.items():
            if key.startswith("ollama") or key.startswith("model"):
                print(f"   {key}: {val}")
        
        # Test vision with captured frame (if available)
        temp_frame = results.get("_temp_frame")
        if temp_frame and results.get("ollama_connection", "").startswith("✅"):
            print("\n👁️ Vision Test:")
            try:
                import base64
                with open(temp_frame, "rb") as f:
                    image_data = base64.b64encode(f.read()).decode()
                
                vision_prompt = "Is there a person visible? Answer only: YES or NO"
                resp = requests.post(
                    f"{ollama_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": vision_prompt,
                        "images": [image_data],
                        "stream": False
                    },
                    timeout=30
                )
                
                if resp.ok:
                    answer = resp.json().get("response", "")[:50]
                    results["ollama_vision"] = f"✅ OK - {answer.strip()}"
                else:
                    results["ollama_vision"] = f"❌ HTTP {resp.status_code}"
                    all_ok = False
            except requests.exceptions.Timeout:
                results["ollama_vision"] = "❌ TIMEOUT (vision model too slow)"
                all_ok = False
            except Exception as e:
                results["ollama_vision"] = f"❌ ERROR: {e}"
                all_ok = False
            finally:
                # Cleanup temp frame
                try:
                    import os
                    os.unlink(temp_frame)
                except Exception:
                    pass
            
            print(f"   ollama_vision: {results.get('ollama_vision', 'N/A')}")
    
    # --- TTS CHECK ---
    if check_type in ("tts", "all"):
        print("\n🔊 TTS / Voice Check:")
        
        from .setup_utils import check_tts_available, ensure_tts_available
        
        tts_engine = config.get("SQ_TTS_ENGINE", "auto")
        results["tts_engine"] = tts_engine
        results["tts_voice"] = config.get("SQ_TTS_VOICE", "") or "(default)"
        results["tts_rate"] = config.get("SQ_TTS_RATE", "150")
        
        # Check and install if needed
        available, engine_used = check_tts_available()
        
        if available:
            # Test speaking
            from .tts import speak
            success = speak("Streamware TTS test", block=True)
            if success:
                results["tts_test"] = f"✅ OK (using {engine_used})"
            else:
                results["tts_test"] = f"⚠️  {engine_used} found but failed"
                all_ok = False
        else:
            results["tts_test"] = "❌ NO WORKING TTS ENGINE"
            all_ok = False
            
            # Offer to install
            if ensure_tts_available(interactive=True):
                available, engine_used = check_tts_available()
                if available:
                    results["tts_test"] = f"✅ {engine_used} installed"
                    _update_env_file("SQ_TTS_ENGINE", engine_used)
                    all_ok = True
        
        for key, val in results.items():
            if key.startswith("tts"):
                print(f"   {key}: {val}")
    
    # --- SUMMARY ---
    print("\n" + "=" * 50)
    if all_ok:
        print("✅ All checks passed!")
    else:
        print("⚠️  Some checks failed. Review output above.")
    print()
    
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
