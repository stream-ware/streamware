"""
CLI Handlers - Apps, Setup, and Automation

Handlers for: setup, template, registry, webapp, desktop, media, service, 
voice, auto, bot, voice_mouse, deploy, ssh
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


def handle_setup(args) -> int:
    """Handle setup command"""
    flow = _get_flow()
    uri = f"setup://{args.operation}?"
    
    if args.packages:
        uri += f"packages={args.packages}&"
    if args.component:
        uri += f"component={args.component}&"
    if args.model:
        uri += f"model={args.model}&"
    if args.force:
        uri += "force=true&"
    
    try:
        result = flow(uri).run()
        
        if not args.quiet:
            print(json.dumps(result, indent=2))
        
        return 0 if result.get("success", True) else 1
    except Exception as e:
        print(f"Setup failed: {e}", file=sys.stderr)
        return 1


def handle_template(args) -> int:
    """Handle template command"""
    flow = _get_flow()
    uri = f"template://{args.operation}?"
    
    if args.name:
        uri += f"name={args.name}&"
    if args.output:
        uri += f"output={args.output}&"
    if args.no_install:
        uri += "auto_install=false&"
    
    try:
        result = flow(uri).run()
        
        if not args.quiet:
            print(json.dumps(result, indent=2))
        
        return 0
    except Exception as e:
        print(f"Template operation failed: {e}", file=sys.stderr)
        return 1


def handle_registry(args) -> int:
    """Handle registry command"""
    flow = _get_flow()
    uri = f"registry://{args.operation}?"
    
    if args.type:
        uri += f"type={args.type}&"
    if args.name:
        uri += f"name={args.name}&"
    if args.tags:
        uri += f"tags={args.tags}&"
    
    try:
        result = flow(uri).run()
        
        if not args.quiet:
            print(json.dumps(result, indent=2))
        
        return 0
    except Exception as e:
        print(f"Registry operation failed: {e}", file=sys.stderr)
        return 1


def handle_webapp(args) -> int:
    """Handle webapp command"""
    flow = _get_flow()
    uri = f"webapp://{args.operation}?"
    
    if args.framework:
        uri += f"framework={args.framework}&"
    if args.name:
        uri += f"name={args.name}&"
    if args.port:
        uri += f"port={args.port}&"
    if args.output:
        uri += f"output={args.output}&"
    
    try:
        result = flow(uri).run()
        
        if not args.quiet:
            print(json.dumps(result, indent=2))
        
        return 0
    except Exception as e:
        print(f"WebApp operation failed: {e}", file=sys.stderr)
        return 1


def handle_desktop(args) -> int:
    """Handle desktop command"""
    flow = _get_flow()
    uri = f"desktop://{args.operation}?"
    
    if args.framework:
        uri += f"framework={args.framework}&"
    if args.name:
        uri += f"name={args.name}&"
    if args.output:
        uri += f"output={args.output}&"
    
    try:
        result = flow(uri).run()
        
        if not args.quiet:
            print(json.dumps(result, indent=2))
        
        return 0
    except Exception as e:
        print(f"Desktop operation failed: {e}", file=sys.stderr)
        return 1


def handle_media(args) -> int:
    """Handle media command"""
    flow = _get_flow()
    
    # Check required parameters and show examples
    examples = {
        "describe_video": [
            "sq media describe_video --file video.mp4",
            "sq media describe_video --file video.mp4 --mode full      # Whole video summary",
            "sq media describe_video --file video.mp4 --mode stream    # Frame-by-frame details",
            "sq media describe_video --file video.mp4 --mode diff      # Changes between frames",
            "sq media describe_video --file video.mp4 --model llava --prompt 'Focus on people'",
        ],
        "describe_image": [
            "sq media describe_image --file photo.jpg",
            "sq media describe_image --file screenshot.png --model llava",
            "sq media describe_image --file diagram.png --prompt 'Explain this diagram'",
        ],
        "transcribe": [
            "sq media transcribe --file audio.mp3",
            "sq media transcribe --file meeting.wav --output transcript.txt",
        ],
        "speak": [
            "sq media speak --text 'Hello World' --output hello.wav",
            "sq media speak --text 'Witaj świecie' --output message.mp3",
        ],
    }
    
    op = args.operation
    
    # Validate required parameters
    if op in ["describe_video", "describe_image", "transcribe"] and not args.file:
        show_examples(f"media {op}", examples.get(op, []), "file")
        return 1
    if op == "speak" and not args.text:
        show_examples("media speak", examples["speak"], "text")
        return 1
    
    uri = f"media://{args.operation}?"
    
    if args.file:
        uri += f"file={args.file}&"
    if args.text:
        uri += f"text={args.text}&"
    if args.model:
        uri += f"model={args.model}&"
    if hasattr(args, 'prompt') and args.prompt:
        uri += f"prompt={args.prompt}&"
    if args.output:
        uri += f"output={args.output}&"
    if hasattr(args, 'mode') and args.mode:
        uri += f"mode={args.mode}&"
    
    try:
        result = flow(uri).run()
        
        if not args.quiet:
            print(json.dumps(result, indent=2))
        
        return 0
    except Exception as e:
        print(f"Media operation failed: {e}", file=sys.stderr)
        return 1


def handle_service(args) -> int:
    """Handle service command"""
    flow = _get_flow()
    uri = f"service://{args.operation}?"
    
    if args.name:
        uri += f"name={args.name}&"
    if args.command:
        uri += f"command={args.command}&"
    if args.dir:
        uri += f"dir={args.dir}&"
    
    try:
        result = flow(uri).run()
        
        if not args.quiet:
            print(json.dumps(result, indent=2))
        
        return 0
    except Exception as e:
        print(f"Service operation failed: {e}", file=sys.stderr)
        return 1


def handle_voice(args) -> int:
    """Handle voice command"""
    flow = _get_flow()
    uri = f"voice://{args.operation}?"
    
    if args.text:
        uri += f"text={args.text}&"
    if args.language:
        uri += f"language={args.language}&"
    
    try:
        result = flow(uri).run()
        
        if not args.quiet:
            print(json.dumps(result, indent=2))
        
        return 0
    except Exception as e:
        print(f"Voice operation failed: {e}", file=sys.stderr)
        return 1


def handle_auto(args) -> int:
    """Handle automation command"""
    flow = _get_flow()
    
    # Check required parameters and show examples if missing
    examples = {
        "click": [
            "sq auto click --x 100 --y 200",
            "sq auto click --x 500 --y 300 --button right",
            "sq auto click --x 100 --y 100 --clicks 2  # double click",
        ],
        "move": [
            "sq auto move --x 500 --y 300",
            "sq auto move --x 0 --y 0  # top-left corner",
        ],
        "type": [
            "sq auto type --text 'Hello World'",
            "sq auto type --text 'user@email.com'",
        ],
        "press": [
            "sq auto press --key enter",
            "sq auto press --key tab",
            "sq auto press --key escape",
        ],
        "hotkey": [
            "sq auto hotkey --keys ctrl+c",
            "sq auto hotkey --keys ctrl+shift+s",
            "sq auto hotkey --keys alt+f4",
        ],
        "screenshot": [
            "sq auto screenshot --text /tmp/screen.png",
            "sq auto screenshot --text ~/Desktop/capture.png",
        ],
        "automate": [
            "sq auto automate --task 'click the Submit button'",
            "sq auto automate --task 'fill the form with name John'",
        ],
    }
    
    op = args.operation
    
    # Validate required parameters
    if op == "click" and (args.x is None or args.y is None):
        show_examples("auto click", examples["click"], "x and --y")
        return 1
    if op == "move" and (args.x is None or args.y is None):
        show_examples("auto move", examples["move"], "x and --y")
        return 1
    if op == "type" and not args.text:
        show_examples("auto type", examples["type"], "text")
        return 1
    if op == "press" and not args.key:
        show_examples("auto press", examples["press"], "key")
        return 1
    if op == "hotkey" and not args.keys:
        show_examples("auto hotkey", examples["hotkey"], "keys")
        return 1
    if op == "automate" and not args.task:
        show_examples("auto automate", examples["automate"], "task")
        return 1
    
    uri = f"automation://{args.operation}?"
    
    if args.x is not None:
        uri += f"x={args.x}&"
    if args.y is not None:
        uri += f"y={args.y}&"
    if args.text:
        uri += f"text={args.text}&"
    if args.key:
        uri += f"key={args.key}&"
    if args.keys:
        uri += f"keys={args.keys}&"
    if args.task:
        uri += f"task={args.task}&"
    
    try:
        result = flow(uri).run()
        
        if not args.quiet:
            print(json.dumps(result, indent=2))
        
        return 0
    except Exception as e:
        print(f"Automation operation failed: {e}", file=sys.stderr)
        return 1


def handle_bot(args) -> int:
    """Handle bot command"""
    flow = _get_flow()
    uri = f"vscode://{args.operation}?"
    
    if args.button:
        uri += f"button={args.button}&"
    if args.iterations:
        uri += f"iterations={args.iterations}&"
    if args.delay:
        uri += f"delay={args.delay}&"
    if args.message:
        uri += f"message={args.message}&"
    if args.task:
        uri += f"task={args.task}&"
    if args.workspace:
        uri += f"workspace={args.workspace}&"
    
    try:
        result = flow(uri).run()
        
        if not args.quiet:
            print(json.dumps(result, indent=2))
        
        return 0
    except Exception as e:
        print(f"Bot operation failed: {e}", file=sys.stderr)
        return 1


def handle_voice_mouse(args) -> int:
    """Handle voice-click command"""
    flow = _get_flow()
    uri = f"voice_mouse://{args.operation}?"
    
    if hasattr(args, 'command') and args.command:
        uri += f"command={args.command}&"
    if args.language:
        uri += f"language={args.language}&"
    if args.iterations:
        uri += f"iterations={args.iterations}&"
    if args.confirm:
        uri += f"confirm={args.confirm}&"
    
    try:
        result = flow(uri).run()
        
        if not args.quiet:
            print(json.dumps(result, indent=2))
        
        return 0
    except Exception as e:
        print(f"Voice mouse operation failed: {e}", file=sys.stderr)
        return 1


def handle_deploy(args) -> int:
    """Handle deploy command"""
    flow = _get_flow()
    
    # Determine operation
    operation = "apply"
    if args.delete:
        operation = "delete"
    elif args.update:
        operation = "update"
    elif args.scale:
        operation = "scale"
    elif args.status:
        operation = "status"
    elif args.logs:
        operation = "logs"
    elif args.rollback:
        operation = "rollback"
    
    uri = f"deploy://{args.platform}/{operation}?"
    
    if args.file:
        uri += f"file={args.file}&"
    if args.namespace:
        uri += f"namespace={args.namespace}&"
    if args.name:
        uri += f"name={args.name}&"
    if args.image:
        uri += f"image={args.image}&"
    if args.tag:
        uri += f"tag={args.tag}&"
    if args.scale:
        uri += f"replicas={args.scale}&"
    if args.project:
        uri += f"project={args.project}&"
    if args.stack:
        uri += f"stack={args.stack}&"
    if args.context:
        uri += f"context={args.context}&"
    
    try:
        result = flow(uri).run()
        
        if not args.quiet:
            print(json.dumps(result, indent=2))
        
        return 0
    except Exception as e:
        print(f"Deploy operation failed: {e}", file=sys.stderr)
        return 1


def handle_ssh(args) -> int:
    """Handle SSH command"""
    flow = _get_flow()
    
    # Determine operation
    if args.upload:
        operation = "upload"
        file_param = f"local={args.upload}&"
        if args.remote:
            file_param += f"remote={args.remote}&"
    elif args.download:
        operation = "download"
        file_param = f"remote={args.download}&"
        if args.local:
            file_param += f"local={args.local}&"
    elif getattr(args, 'exec', None):
        operation = "exec"
        file_param = f"command={getattr(args, 'exec')}&"
    elif args.deploy:
        operation = "deploy"
        file_param = f"file={args.deploy}&"
        if args.remote:
            file_param += f"remote={args.remote}&"
        if args.restart:
            file_param += f"restart={args.restart}&"
    else:
        print("Error: Specify --upload, --download, --exec, or --deploy", file=sys.stderr)
        return 1
    
    uri = f"ssh://{args.user}@{args.host}:{args.port}/{operation}?"
    uri += file_param
    
    if args.key:
        uri += f"key={args.key}&"
    
    try:
        result = flow(uri).run()
        
        if not args.quiet:
            print(json.dumps(result, indent=2))
        
        return 0
    except Exception as e:
        print(f"SSH operation failed: {e}", file=sys.stderr)
        return 1
