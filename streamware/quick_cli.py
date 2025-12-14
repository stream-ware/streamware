"""
Quick CLI - Simplified shell interface for Streamware

Provides shorter, more intuitive commands for common operations.

OPTIMIZED: Uses lazy imports for fast startup (~0.3s instead of ~3s)
"""

import sys
import argparse
from pathlib import Path
from typing import Optional

# LAZY IMPORTS - only import heavy modules when needed
# This speeds up CLI startup from ~3s to ~0.3s

def _get_flow():
    """Lazy import for flow."""
    from .core import flow
    return flow

def _get_pipeline():
    """Lazy import for Pipeline."""
    from .dsl import Pipeline
    return Pipeline

def _get_quick():
    """Lazy import for quick."""
    from .dsl import quick
    return quick

def enable_diagnostics(level="INFO"):
    """Lazy import for diagnostics."""
    from .diagnostics import enable_diagnostics as _enable
    return _enable(level)

class StreamwareError(Exception):
    """Placeholder - real one imported lazily."""
    pass

def _get_streamware_error():
    """Lazy import for StreamwareError."""
    from .exceptions import StreamwareError
    return StreamwareError

# Lazy flow wrapper - imports only when called
def flow(uri):
    """Lazy wrapper for flow - imports core only when first used."""
    from .core import flow as _flow
    return _flow(uri)

# Lazy Pipeline wrapper
def Pipeline(*args, **kwargs):
    """Lazy wrapper for Pipeline."""
    from .dsl import Pipeline as _Pipeline
    return _Pipeline(*args, **kwargs)

# Lazy quick wrapper  
def quick(*args, **kwargs):
    """Lazy wrapper for quick."""
    from .dsl import quick as _quick
    return _quick(*args, **kwargs)


# Lazy handler imports - only import when command is used
def _get_handler(module_name: str, handler_name: str):
    """Lazy import for handlers."""
    import importlib
    module = importlib.import_module(f".{module_name}", package="streamware")
    return getattr(module, handler_name)


# Handler references (lazy loaded)
def handle_get(args): return _get_handler("cli_handlers_io", "handle_get")(args)
def handle_post(args): return _get_handler("cli_handlers_io", "handle_post")(args)
def handle_file(args): return _get_handler("cli_handlers_io", "handle_file")(args)
def handle_kafka(args): return _get_handler("cli_handlers_io", "handle_kafka")(args)
def handle_postgres(args): return _get_handler("cli_handlers_io", "handle_postgres")(args)
def handle_email(args): return _get_handler("cli_handlers_io", "handle_email")(args)
def handle_slack(args): return _get_handler("cli_handlers_io", "handle_slack")(args)
def handle_transform(args): return _get_handler("cli_handlers_io", "handle_transform")(args)
def handle_llm(args): return _get_handler("cli_handlers_io", "handle_llm")(args)

def handle_setup(args): return _get_handler("cli_handlers_apps", "handle_setup")(args)
def handle_template(args): return _get_handler("cli_handlers_apps", "handle_template")(args)
def handle_registry(args): return _get_handler("cli_handlers_apps", "handle_registry")(args)
def handle_webapp(args): return _get_handler("cli_handlers_apps", "handle_webapp")(args)
def handle_desktop(args): return _get_handler("cli_handlers_apps", "handle_desktop")(args)
def handle_media(args): return _get_handler("cli_handlers_apps", "handle_media")(args)
def handle_service(args): return _get_handler("cli_handlers_apps", "handle_service")(args)
def handle_voice(args): return _get_handler("cli_handlers_apps", "handle_voice")(args)
def handle_auto(args): return _get_handler("cli_handlers_apps", "handle_auto")(args)
def handle_bot(args): return _get_handler("cli_handlers_apps", "handle_bot")(args)
def handle_voice_mouse(args): return _get_handler("cli_handlers_apps", "handle_voice_mouse")(args)
def handle_deploy(args): return _get_handler("cli_handlers_apps", "handle_deploy")(args)
def handle_ssh(args): return _get_handler("cli_handlers_apps", "handle_ssh")(args)

def handle_stream(args): return _get_handler("cli_handlers_stream", "handle_stream")(args)
def handle_network(args): return _get_handler("cli_handlers_stream", "handle_network")(args)
def handle_config(args): return _get_handler("cli_handlers_stream", "handle_config")(args)

def handle_tracking(args): return _get_handler("cli_handlers_monitoring", "handle_tracking")(args)
def handle_motion(args): return _get_handler("cli_handlers_monitoring", "handle_motion")(args)
def handle_smart(args): return _get_handler("cli_handlers_monitoring", "handle_smart")(args)

def handle_watch(args): return _get_handler("cli_handlers_watch", "handle_watch")(args)
def handle_live(args): return _get_handler("cli_handlers_live", "handle_live")(args)

def handle_visualize(args): return _get_handler("cli_handlers_misc", "handle_visualize")(args)
def handle_mqtt(args): return _get_handler("cli_handlers_misc", "handle_mqtt")(args)
def handle_shell(args): return _get_handler("cli_handlers_misc", "handle_shell")(args)
def handle_functions(args): return _get_handler("cli_handlers_misc", "handle_functions")(args)
def handle_voice_shell(args): return _get_handler("cli_handlers_misc", "handle_voice_shell")(args)
def handle_accounting(args): return _get_handler("cli_handlers_misc", "handle_accounting")(args)


def main():
    """Quick CLI entry point"""
    parser = argparse.ArgumentParser(
        prog='sq',  # stream-quick
        description="Streamware Quick - Simplified shell interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Quick Examples:
  # HTTP GET and save
  sq get api.example.com/data --json --save data.json
  
  # Transform file
  sq file input.json --json --csv --save output.csv
  
  # Kafka consume
  sq kafka events --group processor --json
  
  # Send email
  sq email user@example.com --subject "Hello" --body "Message"
  
  # PostgreSQL query
  sq postgres "SELECT * FROM users" --csv --save users.csv

Shortcuts:
  get       HTTP GET request
  post      HTTP POST request
  file      Read file
  kafka     Kafka operations
  postgres  PostgreSQL operations
  email     Send email
  slack     Send to Slack
  transform Transform data
        """
    )
    
    # Parent parser for common output format options
    format_parser = argparse.ArgumentParser(add_help=False)
    format_parser.add_argument('--yaml', '-Y', action='store_true', help='Output as YAML (default for some commands)')
    format_parser.add_argument('--json', '-J', action='store_true', help='Output as JSON')
    format_parser.add_argument('--table', '-T', action='store_true', help='Output as ASCII table')
    format_parser.add_argument('--html', action='store_true', help='Output as HTML')
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # GET command
    get_parser = subparsers.add_parser('get', help='HTTP GET request', parents=[format_parser])
    get_parser.add_argument('url', help='URL to fetch (http:// optional)')
    get_parser.add_argument('--csv', action='store_true', help='Convert to CSV')
    get_parser.add_argument('--save', '-o', metavar='FILE', help='Save to file')
    get_parser.add_argument('--pretty', action='store_true', help='Pretty print JSON')
    
    # POST command
    post_parser = subparsers.add_parser('post', help='HTTP POST request')
    post_parser.add_argument('url', help='URL to post to')
    post_parser.add_argument('--data', '-d', help='Data to send (JSON string or @file)')
    post_parser.add_argument('--json', action='store_true', help='Parse response as JSON')
    post_parser.add_argument('--save', '-o', metavar='FILE', help='Save response to file')
    
    # FILE command
    file_parser = subparsers.add_parser('file', help='Read and transform file')
    file_parser.add_argument('path', help='File path to read')
    file_parser.add_argument('--json', action='store_true', help='Parse as JSON')
    file_parser.add_argument('--csv', action='store_true', help='Convert to CSV')
    file_parser.add_argument('--base64', action='store_true', help='Base64 encode')
    file_parser.add_argument('--decode', action='store_true', help='Base64 decode')
    file_parser.add_argument('--save', '-o', metavar='FILE', help='Save to file')
    
    # KAFKA command
    kafka_parser = subparsers.add_parser('kafka', help='Kafka operations')
    kafka_parser.add_argument('topic', help='Kafka topic')
    kafka_parser.add_argument('--consume', action='store_true', help='Consume messages')
    kafka_parser.add_argument('--produce', action='store_true', help='Produce message')
    kafka_parser.add_argument('--group', default='default', help='Consumer group')
    kafka_parser.add_argument('--data', '-d', help='Data to produce')
    kafka_parser.add_argument('--json', action='store_true', help='Parse as JSON')
    kafka_parser.add_argument('--stream', action='store_true', help='Stream mode')
    
    # POSTGRES command
    pg_parser = subparsers.add_parser('postgres', help='PostgreSQL operations')
    pg_parser.add_argument('sql', help='SQL query')
    pg_parser.add_argument('--json', action='store_true', help='Output as JSON')
    pg_parser.add_argument('--csv', action='store_true', help='Output as CSV')
    pg_parser.add_argument('--save', '-o', metavar='FILE', help='Save to file')
    
    # EMAIL command
    email_parser = subparsers.add_parser('email', help='Send email')
    email_parser.add_argument('to', help='Recipient email')
    email_parser.add_argument('--subject', '-s', required=True, help='Email subject')
    email_parser.add_argument('--body', '-b', help='Email body')
    email_parser.add_argument('--file', '-f', help='Body from file')
    
    # SLACK command
    slack_parser = subparsers.add_parser('slack', help='Send to Slack')
    slack_parser.add_argument('channel', help='Slack channel')
    slack_parser.add_argument('--message', '-m', required=True, help='Message to send')
    slack_parser.add_argument('--token', '-t', help='Slack token (or use env SLACK_BOT_TOKEN)')
    
    # TRANSFORM command
    transform_parser = subparsers.add_parser('transform', help='Transform data')
    transform_parser.add_argument('type', choices=['json', 'csv', 'base64', 'yaml'], 
                                  help='Transform type')
    transform_parser.add_argument('--input', '-i', help='Input file (or stdin)')
    transform_parser.add_argument('--output', '-o', help='Output file (or stdout)')
    transform_parser.add_argument('--decode', action='store_true', help='Decode (for base64)')
    
    # SSH command
    ssh_parser = subparsers.add_parser('ssh', help='SSH operations')
    ssh_parser.add_argument('host', help='Remote host')
    ssh_parser.add_argument('--upload', '-u', metavar='FILE', help='Upload file')
    ssh_parser.add_argument('--download', '-d', metavar='FILE', help='Download file')
    ssh_parser.add_argument('--exec', '-e', metavar='COMMAND', help='Execute command')
    ssh_parser.add_argument('--deploy', metavar='FILE', help='Deploy file')
    ssh_parser.add_argument('--user', default='root', help='SSH user')
    ssh_parser.add_argument('--key', '-k', help='SSH key path')
    ssh_parser.add_argument('--port', '-p', type=int, default=22, help='SSH port')
    ssh_parser.add_argument('--remote', '-r', help='Remote path')
    ssh_parser.add_argument('--local', '-l', help='Local path')
    ssh_parser.add_argument('--restart', help='Restart service after deploy')
    
    # LLM command
    llm_parser = subparsers.add_parser('llm', help='LLM operations and DSL conversion')
    llm_parser.add_argument('prompt', nargs='?', help='Prompt or natural language input')
    llm_parser.add_argument('--to-sql', action='store_true', help='Convert to SQL query')
    llm_parser.add_argument('--to-sq', action='store_true', help='Convert to Streamware command')
    llm_parser.add_argument('--to-bash', action='store_true', help='Convert to bash command')
    llm_parser.add_argument('--analyze', action='store_true', help='Analyze text')
    llm_parser.add_argument('--summarize', action='store_true', help='Summarize text')
    llm_parser.add_argument('--provider', choices=['openai', 'anthropic', 'ollama'], 
                           help='LLM provider (default: from config)')
    llm_parser.add_argument('--model', help='Model name')
    llm_parser.add_argument('--execute', action='store_true', help='Execute generated command')
    llm_parser.add_argument('--input', '-i', help='Input file')
    
    # Setup command
    setup_parser = subparsers.add_parser('setup', help='Setup and install dependencies')
    setup_parser.add_argument('operation', choices=['check', 'install', 'python', 'system', 'ollama', 'all'],
                             help='Setup operation')
    setup_parser.add_argument('--packages', help='Comma-separated package list')
    setup_parser.add_argument('--component', help='Component name for auto-install')
    setup_parser.add_argument('--model', help='Ollama model name')
    setup_parser.add_argument('--force', action='store_true', help='Force reinstall')
    
    # Template command
    template_parser = subparsers.add_parser('template', help='Generate project templates')
    template_parser.add_argument('operation', choices=['generate', 'list', 'info'],
                                help='Template operation')
    template_parser.add_argument('--name', help='Template name')
    template_parser.add_argument('--output', default='.', help='Output directory')
    template_parser.add_argument('--no-install', action='store_true', help='Skip auto-install')
    
    # Registry command
    registry_parser = subparsers.add_parser('registry', help='Resource registry')
    registry_parser.add_argument('operation', choices=['register', 'lookup', 'list', 'remove'],
                                help='Registry operation')
    registry_parser.add_argument('--type', default='component', help='Resource type')
    registry_parser.add_argument('--name', help='Resource name')
    registry_parser.add_argument('--tags', help='Comma-separated tags')
    
    # WebApp command
    webapp_parser = subparsers.add_parser('webapp', help='Create web applications')
    webapp_parser.add_argument('operation', choices=['create', 'serve', 'build'],
                               help='WebApp operation')
    webapp_parser.add_argument('--framework', choices=['flask', 'fastapi', 'streamlit', 'gradio', 'dash'],
                              default='flask', help='Web framework')
    webapp_parser.add_argument('--name', default='myapp', help='App name')
    webapp_parser.add_argument('--port', type=int, help='Port number')
    webapp_parser.add_argument('--output', default='.', help='Output directory')
    
    # Desktop command
    desktop_parser = subparsers.add_parser('desktop', help='Create desktop applications')
    desktop_parser.add_argument('operation', choices=['create', 'run', 'build'],
                                help='Desktop operation')
    desktop_parser.add_argument('--framework', choices=['tkinter', 'pyqt', 'kivy'],
                               default='tkinter', help='GUI framework')
    desktop_parser.add_argument('--name', default='myapp', help='App name')
    desktop_parser.add_argument('--output', default='.', help='Output directory')
    
    # Media command
    media_parser = subparsers.add_parser('media', help='Analyze multimedia with AI')
    media_parser.add_argument('operation', choices=['describe_video', 'describe_image', 'transcribe', 'speak', 'caption'],
                             help='Media operation')
    media_parser.add_argument('--file', help='Input file')
    media_parser.add_argument('--text', help='Text for TTS')
    media_parser.add_argument('--model', default=None, help='AI model (default: from SQ_MODEL config)')
    media_parser.add_argument('--prompt', help='Custom prompt for AI analysis')
    media_parser.add_argument('--output', help='Output file')
    media_parser.add_argument('--mode', choices=['full', 'stream', 'diff'], default='full',
                             help='Video analysis mode: full (summary), stream (frame-by-frame), diff (changes)')
    
    # Service command
    service_parser = subparsers.add_parser('service', help='Manage background services')
    service_parser.add_argument('operation', choices=['start', 'stop', 'restart', 'status', 'install', 'uninstall', 'list'],
                               help='Service operation')
    service_parser.add_argument('--name', help='Service name')
    service_parser.add_argument('--command', help='Command to run')
    service_parser.add_argument('--dir', default='.', help='Working directory')
    
    # Voice command
    voice_parser = subparsers.add_parser('voice', help='Voice input/output (STT/TTS)')
    voice_parser.add_argument('operation', choices=['listen', 'speak', 'command', 'interactive'],
                             help='Voice operation')
    voice_parser.add_argument('--text', help='Text to speak')
    voice_parser.add_argument('--language', default='en', help='Language code')
    
    # Automation command
    auto_parser = subparsers.add_parser('auto', help='Desktop automation (mouse/keyboard)')
    auto_parser.add_argument('operation', choices=['click', 'move', 'type', 'press', 'hotkey', 'automate', 'screenshot'],
                            help='Automation operation')
    auto_parser.add_argument('--x', type=int, help='X coordinate')
    auto_parser.add_argument('--y', type=int, help='Y coordinate')
    auto_parser.add_argument('--text', help='Text to type')
    auto_parser.add_argument('--key', help='Key to press')
    auto_parser.add_argument('--keys', help='Key combination (e.g., ctrl+c)')
    auto_parser.add_argument('--task', help='Task description for AI automation')
    
    # VSCode Bot command
    bot_parser = subparsers.add_parser('bot', help='VSCode automation bot')
    bot_parser.add_argument('operation', choices=['click_button', 'find_button', 'generate_prompt', 'commit_changes', 'accept_changes', 'reject_changes', 'continue_work', 'watch'],
                           help='Bot operation')
    bot_parser.add_argument('--button', default='accept_all', help='Button to click (accept_all, reject_all, run, skip, continue)')
    bot_parser.add_argument('--iterations', type=int, default=5, help='Number of iterations')
    bot_parser.add_argument('--delay', type=float, default=2.0, help='Delay between actions')
    bot_parser.add_argument('--message', default='Auto commit by bot', help='Git commit message')
    bot_parser.add_argument('--task', default='continue development', help='Task description')
    bot_parser.add_argument('--workspace', default='.', help='Workspace directory')
    
    # Voice Mouse command
    voice_mouse_parser = subparsers.add_parser('voice-click', help='Voice-controlled mouse')
    voice_mouse_parser.add_argument('operation', nargs='?', default='listen_and_click',
                                   choices=['click', 'move', 'listen_and_click'],
                                   help='Voice mouse operation')
    voice_mouse_parser.add_argument('--command', help='Voice command (e.g., "kliknij w button zatwierdź")')
    voice_mouse_parser.add_argument('--language', default='pl', choices=['pl', 'en'], help='Language')
    voice_mouse_parser.add_argument('--iterations', type=int, default=10, help='Number of iterations for listen mode')
    voice_mouse_parser.add_argument('--confirm', action='store_true', default=True, help='Speak before clicking')
    
    # Deploy command
    deploy_parser = subparsers.add_parser('deploy', help='Deploy to K8s, Compose, Swarm')
    deploy_parser.add_argument('platform', choices=['k8s', 'kubernetes', 'compose', 'swarm', 'docker'],
                               help='Deployment platform')
    deploy_parser.add_argument('--apply', action='store_true', help='Apply deployment')
    deploy_parser.add_argument('--delete', action='store_true', help='Delete deployment')
    deploy_parser.add_argument('--update', action='store_true', help='Update deployment')
    deploy_parser.add_argument('--scale', type=int, metavar='REPLICAS', help='Scale replicas')
    deploy_parser.add_argument('--status', action='store_true', help='Get status')
    deploy_parser.add_argument('--logs', action='store_true', help='Get logs')
    deploy_parser.add_argument('--rollback', action='store_true', help='Rollback deployment')
    deploy_parser.add_argument('--file', '-f', help='Manifest/compose file')
    deploy_parser.add_argument('--namespace', '-n', default='default', help='K8s namespace')
    deploy_parser.add_argument('--name', help='Deployment/service name')
    deploy_parser.add_argument('--image', help='Docker image')
    deploy_parser.add_argument('--tag', default='latest', help='Image tag')
    deploy_parser.add_argument('--project', '-p', help='Compose project name')
    deploy_parser.add_argument('--stack', '-s', help='Swarm stack name')
    deploy_parser.add_argument('--context', help='K8s context')
    
    # Stream command (real-time video analysis)
    stream_parser = subparsers.add_parser('stream', help='Real-time stream analysis', parents=[format_parser])
    stream_parser.add_argument('source', choices=['rtsp', 'hls', 'youtube', 'twitch', 'screen', 'webcam', 'http'],
                              help='Stream source')
    stream_parser.add_argument('--url', '-u', help='Stream URL')
    stream_parser.add_argument('--mode', '-m', choices=['full', 'stream', 'diff'], default='diff',
                              help='Analysis mode (default: diff)')
    stream_parser.add_argument('--interval', '-i', type=int, default=5, help='Seconds between captures')
    stream_parser.add_argument('--duration', '-d', type=int, default=30, help='Total duration (0=infinite)')
    stream_parser.add_argument('--device', default='0', help='Webcam device')
    stream_parser.add_argument('--model', default=None, help='AI model (default: from SQ_MODEL config)')
    stream_parser.add_argument('--prompt', help='Custom prompt for AI')
    stream_parser.add_argument('--focus', '-f', 
                              help='Focus tracking: person, animal, vehicle, face, motion, package, intrusion')
    stream_parser.add_argument('--zone', help='Detection zone: x,y,w,h (e.g., 100,100,400,300)')
    stream_parser.add_argument('--sensitivity', choices=['low', 'medium', 'high'], default='medium',
                              help='Change detection sensitivity')
    stream_parser.add_argument('--continuous', '-c', action='store_true', help='Continuous monitoring')
    stream_parser.add_argument('--file', '-o', help='Save HTML report with images to file')
    
    # Network command (network scanning)
    network_parser = subparsers.add_parser('network', help='Network scanning and device discovery', parents=[format_parser])
    network_parser.add_argument('operation', choices=['scan', 'find', 'identify', 'ports'],
                               help='Network operation')
    network_parser.add_argument('query', nargs='?', help='Search query for find operation')
    network_parser.add_argument('--subnet', '-s', help='Subnet to scan (default: auto-detect)')
    network_parser.add_argument('--ip', help='IP address for identify/ports')
    network_parser.add_argument('--deep', action='store_true', help='Deep scan (slower, more info)')
    network_parser.add_argument('--timeout', type=int, default=10, help='Scan timeout')
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Configuration management')
    config_parser.add_argument('--web', '-w', action='store_true', help='Open web configuration panel')
    config_parser.add_argument('--show', '-s', action='store_true', help='Show current configuration')
    config_parser.add_argument('--set', nargs=2, metavar=('KEY', 'VALUE'), help='Set configuration value')
    config_parser.add_argument('--save', action='store_true', help='Save configuration to .env')
    config_parser.add_argument('--init', action='store_true', help='Create .env from .env.example')
    config_parser.add_argument('--port', type=int, default=8080, help='Web panel port (default: 8080)')
    
    # Tracking command
    tracking_parser = subparsers.add_parser('tracking', help='Object tracking and detection', parents=[format_parser])
    tracking_parser.add_argument('operation', choices=['detect', 'track', 'count', 'zones', 'heatmap'],
                                 help='Tracking operation')
    tracking_parser.add_argument('--url', '-u', required=True, help='Video source (RTSP URL or file)')
    tracking_parser.add_argument('--objects', '-o', default='person', 
                                help='Objects to detect (comma-separated: person,vehicle,animal)')
    tracking_parser.add_argument('--target', '-t', help='Specific target to track')
    tracking_parser.add_argument('--name', '-n', help='Name for tracked object')
    tracking_parser.add_argument('--zones', help='Zones to monitor (name:x,y,w,h|name2:x,y,w,h)')
    tracking_parser.add_argument('--duration', '-d', type=int, default=60, help='Duration in seconds')
    tracking_parser.add_argument('--interval', '-i', type=int, default=5, help='Interval between frames')
    tracking_parser.add_argument('--file', '-f', help='Save report to file')
    
    # Motion command (pixel-level diff + AI on regions)
    motion_parser = subparsers.add_parser('motion', help='Smart motion detection with region analysis', parents=[format_parser])
    motion_parser.add_argument('operation', choices=['diff', 'analyze', 'regions', 'heatmap'],
                               nargs='?', default='analyze', help='Operation (default: analyze)')
    motion_parser.add_argument('--url', '-u', required=True, help='Video source (RTSP URL or file)')
    motion_parser.add_argument('--threshold', '-t', type=int, default=25, 
                               help='Sensitivity 0-100, lower=more sensitive (default: 25)')
    motion_parser.add_argument('--min-region', type=int, default=500, 
                               help='Minimum region size in pixels (default: 500)')
    motion_parser.add_argument('--grid', '-g', type=int, default=8, help='Grid size for region detection')
    motion_parser.add_argument('--focus', '-f', default='person', help='Focus target for AI analysis')
    motion_parser.add_argument('--duration', '-d', type=int, default=30, help='Duration in seconds')
    motion_parser.add_argument('--interval', '-i', type=int, default=5, help='Interval between frames')
    motion_parser.add_argument('--file', '-o', help='Save HTML report with images')
    
    # Smart monitor command (buffered, adaptive)
    smart_parser = subparsers.add_parser('smart', help='Smart monitoring with buffering', parents=[format_parser])
    smart_parser.add_argument('operation', choices=['monitor', 'watch', 'zones'],
                              nargs='?', default='monitor', help='Operation (default: monitor)')
    smart_parser.add_argument('--url', '-u', required=True, help='Video source')
    smart_parser.add_argument('--min-interval', type=float, default=1.0, 
                              help='Min seconds between captures (default: 1)')
    smart_parser.add_argument('--max-interval', type=float, default=10.0,
                              help='Max seconds between captures (default: 10)')
    smart_parser.add_argument('--adaptive', action='store_true', default=True,
                              help='Adaptive capture rate (default: on)')
    smart_parser.add_argument('--buffer-size', type=int, default=50,
                              help='Frame buffer size (default: 50)')
    smart_parser.add_argument('--threshold', '-t', type=int, default=25,
                              help='Diff threshold 0-100 (default: 25)')
    smart_parser.add_argument('--min-change', type=float, default=0.5,
                              help='Min change pct to trigger (default: 0.5)')
    smart_parser.add_argument('--zones', help='Zones: name:x,y,w,h|name2:x,y,w,h')
    smart_parser.add_argument('--focus', '-f', default='person', help='AI focus')
    smart_parser.add_argument('--no-ai', action='store_true', help='Disable AI analysis')
    smart_parser.add_argument('--duration', '-d', type=int, default=60, help='Duration (seconds)')
    smart_parser.add_argument('--quality', '-q', type=int, default=90, help='Capture quality 1-100')
    smart_parser.add_argument('--file', '-o', help='Save HTML report')
    
    # Watch command - qualitative parameters (NEW!)
    watch_parser = subparsers.add_parser('watch', help='Watch stream with intuitive settings', parents=[format_parser])
    watch_parser.add_argument('intent', nargs='?', default=None, 
                              help='Natural language intent (e.g., "track person", "count cars")')
    watch_parser.add_argument('--url', '-u', required=False, help='Video source (or use SQ_DEFAULT_URL env)')
    watch_parser.add_argument('--sensitivity', '-s',
                              choices=['ultra', 'high', 'medium', 'low', 'minimal'],
                              default='medium', help='Detection sensitivity')
    watch_parser.add_argument('--detect', '-d',
                              choices=['person', 'people', 'face', 'vehicle', 'car', 
                                       'animal', 'pet', 'package', 'motion', 'intrusion', 'any'],
                              default='any', help='What to detect')
    watch_parser.add_argument('--speed',
                              choices=['realtime', 'fast', 'normal', 'slow', 'thorough'],
                              default='normal', help='Analysis speed')
    watch_parser.add_argument('--when', '-w',
                              choices=['appears', 'disappears', 'enters', 'leaves', 
                                       'moves', 'stops', 'changes'],
                              default='changes', help='When to trigger')
    watch_parser.add_argument('--alert', '-a',
                              choices=['none', 'log', 'sound', 'speak', 'slack', 'telegram'],
                              default='none', help='How to alert')
    watch_parser.add_argument('--duration', type=int, default=60, help='Duration in seconds')
    watch_parser.add_argument('--file', '-o', help='Save report to file (HTML or Markdown)')
    watch_parser.add_argument('--log', choices=['md'], help='Generate Markdown log (md)')
    # Notification options
    watch_parser.add_argument('--email', help='Email address for notifications')
    watch_parser.add_argument('--slack', help='Slack channel for notifications')
    watch_parser.add_argument('--telegram', help='Telegram chat ID for notifications')
    watch_parser.add_argument('--webhook', help='Webhook URL for notifications')
    watch_parser.add_argument('--notify-mode', choices=['instant', 'digest', 'summary'], 
                              default='digest', help='Notification mode')
    watch_parser.add_argument('--notify-interval', type=int, default=60, 
                              help='Digest interval in seconds')
    # Additional options
    watch_parser.add_argument('--tts', action='store_true', help='Enable text-to-speech')
    watch_parser.add_argument('--screenshot', action='store_true', help='Save screenshots')
    watch_parser.add_argument('--track', help='Track specific object type')
    watch_parser.add_argument('--count', help='Count specific object type')
    watch_parser.add_argument('--mode', choices=['yolo', 'llm', 'hybrid'], default='yolo',
                              help='Detection mode')
    watch_parser.add_argument('--fps', type=float, default=2.0, help='Frames per second')
    watch_parser.add_argument('--confidence', type=float, default=0.5, help='Detection confidence 0-1')
    
    # Live narrator command (TTS, triggers)
    live_parser = subparsers.add_parser('live', help='Live narration with TTS and triggers', parents=[format_parser])
    live_parser.add_argument('operation', choices=['narrator', 'watch', 'describe', 'reader'],
                             nargs='?', default='narrator', help='Operation: narrator, watch, describe, reader (OCR)')
    live_parser.add_argument('--url', '-u', required=True, help='Video source')
    live_parser.add_argument('--mode', '-m', choices=['full', 'diff', 'track'],
                             default='full', help='Mode: full (describe all), diff (only changes), track (follow object)')
    # Descriptive parameters (instead of numeric values)
    live_parser.add_argument('--analysis', choices=['quick', 'normal', 'deep', 'forensic'],
                             default='normal', help='Analysis depth: quick (fast), normal, deep (thorough), forensic')
    live_parser.add_argument('--motion', choices=['any', 'significant', 'objects', 'people'],
                             default='significant', help='Motion mode: any (sensitive), significant, objects, people')
    live_parser.add_argument('--frames', choices=['all', 'changed', 'keyframes', 'periodic'],
                             default='changed', help='Frame processing: all, changed (default), keyframes, periodic')
    live_parser.add_argument('--tts', action='store_true', help='Enable text-to-speech')
    live_parser.add_argument('--tts-all', action='store_true', help='TTS: speak every LLM response (debug mode)')
    live_parser.add_argument('--tts-diff', action='store_true', help='TTS: speak only when state/summary changes')
    live_parser.add_argument('--lang', '-l', default='en', help='TTS language (en, pl, de)')
    live_parser.add_argument('--trigger', '-t', help='Triggers: "person appears,door opens"')
    live_parser.add_argument('--focus', '-f', help='Focus on specific objects (e.g., person)')
    live_parser.add_argument('--interval', '-i', type=float, help='Seconds between checks (or use sensitivity)')
    live_parser.add_argument('--duration', '-d', type=int, default=60, help='Duration (seconds)')
    live_parser.add_argument('--threshold', type=int, help='Change threshold 0-100 (or use sensitivity)')
    live_parser.add_argument('--model', default=None, help='AI model (default: from SQ_MODEL config)')
    live_parser.add_argument('--webhook', help='Webhook URL for alerts')
    live_parser.add_argument('--file', '-o', help='Save report to file (HTML or Markdown)')
    live_parser.add_argument('--log', choices=['md'], help='Generate Markdown log (md)')
    live_parser.add_argument('--frames-dir', help='Directory to save captured frames (e.g. ./frames)')
    live_parser.add_argument('--lite', action='store_true', help='Lite mode: no images in memory (faster, less RAM)')
    live_parser.add_argument('--quiet', '-q', action='store_true', help='Quiet mode: minimal output')
    live_parser.add_argument('--guarder', action='store_true', help='Use small LLM (qwen2.5:3b) to validate responses before logging')
    live_parser.add_argument('--log-file', help='Save detailed timing logs to file (e.g. log.csv)')
    live_parser.add_argument('--log-format', choices=['csv', 'json', 'yaml', 'md', 'all'], default='csv',
                            help='Log format: csv, json, yaml, md (markdown), or all')
    live_parser.add_argument('--adaptive', action='store_true', default=True, help='Adaptive frame rate based on motion (default: on)')
    live_parser.add_argument('--no-adaptive', action='store_true', help='Disable adaptive frame rate')
    live_parser.add_argument('--fast', action='store_true', help='Fast mode: smaller model, lower resolution, aggressive caching')
    live_parser.add_argument('--intent', help='Natural language intent (e.g. "notify when someone enters", "track person")')
    live_parser.add_argument('--benchmark', action='store_true', help='Run performance benchmark before starting')
    live_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output: show all steps in real-time')
    live_parser.add_argument('--auto', action='store_true', help='Auto-configure based on hardware (detects CPU/GPU and optimizes)')
    live_parser.add_argument('--ramdisk', action='store_true', default=True, help='Use RAM disk for frame capture (default: on)')
    live_parser.add_argument('--no-ramdisk', action='store_true', help='Disable RAM disk, use temp files')
    live_parser.add_argument('--skip-checks', action='store_true', help='Skip dependency checks for faster startup')
    live_parser.add_argument('--turbo', action='store_true', help='Turbo mode: skip checks + fast model + aggressive caching')
    live_parser.add_argument('--realtime', action='store_true', help='Real-time viewer: stream DSL to browser (http://localhost:8766)')
    live_parser.add_argument('--dsl-only', action='store_true', help='DSL-only mode: skip LLM, use only OpenCV tracking (fast, up to 20 FPS)')
    live_parser.add_argument('--fps', type=float, default=None, help='Target FPS for real-time mode (default: 2 for normal, 10 for dsl-only)')
    # OCR Reader arguments
    live_parser.add_argument('--ocr', action='store_true', help='Enable OCR text extraction (for reader operation)')
    live_parser.add_argument('--ocr-engine', choices=['tesseract', 'easyocr', 'paddleocr'], default='tesseract',
                             help='OCR engine: tesseract (default), easyocr, paddleocr')
    live_parser.add_argument('--llm-query', '--query', help='Custom LLM query about the image')
    live_parser.add_argument('--continuous', action='store_true', help='Run continuously (for reader)')
    
    # Visualize command - real-time SVG visualization
    viz_parser = subparsers.add_parser('visualize', help='Real-time SVG visualization in browser')
    viz_parser.add_argument('--url', '-u', required=True, help='RTSP stream URL')
    viz_parser.add_argument('--port', '-p', type=int, default=8080, help='HTTP server port (default: 8080)')
    viz_parser.add_argument('--fps', type=float, default=1.0, help='Frames per second (default: 1)')
    viz_parser.add_argument('--width', type=int, default=320, help='Frame width (default: 320)')
    viz_parser.add_argument('--height', type=int, default=240, help='Frame height (default: 240)')
    viz_parser.add_argument('--simple', action='store_true', help='Use simple HTTP server (no WebSocket)')
    viz_parser.add_argument('--fast', action='store_true', help='Fast mode: lower resolution, higher FPS')
    viz_parser.add_argument('--video-mode', choices=['ws', 'hls', 'meta', 'webrtc'], default='ws', 
                            help='Video mode: ws (JPEG/WebSocket), hls (HTTP Live Streaming), meta (metadata-only), webrtc (ultra-low latency)')
    viz_parser.add_argument('--transport', choices=['tcp', 'udp'], default='tcp',
                            help='RTSP transport: tcp (stable) or udp (lower latency, may drop frames)')
    viz_parser.add_argument('--backend', choices=['opencv', 'gstreamer', 'pyav'], default='opencv',
                            help='Capture backend: opencv (default), gstreamer (faster), pyav (direct API)')
    viz_parser.add_argument('--turbo', action='store_true',
                            help='Turbo mode: PyAV + UDP + minimal analysis for fastest startup')
    
    # MQTT command - publish DSL to MQTT broker
    mqtt_parser = subparsers.add_parser('mqtt', help='Publish DSL metadata to MQTT broker')
    mqtt_parser.add_argument('--url', '-u', required=True, help='RTSP stream URL')
    mqtt_parser.add_argument('--broker', '-b', default='localhost', help='MQTT broker host (default: localhost)')
    mqtt_parser.add_argument('--mqtt-port', type=int, default=1883, help='MQTT broker port (default: 1883)')
    mqtt_parser.add_argument('--username', help='MQTT username')
    mqtt_parser.add_argument('--password', help='MQTT password')
    mqtt_parser.add_argument('--topic', '-t', default='streamware/dsl', help='MQTT topic prefix (default: streamware/dsl)')
    mqtt_parser.add_argument('--fps', type=float, default=5.0, help='Frames per second (default: 5)')
    mqtt_parser.add_argument('--width', type=int, default=320, help='Frame width (default: 320)')
    mqtt_parser.add_argument('--height', type=int, default=240, help='Frame height (default: 240)')
    mqtt_parser.add_argument('--threshold', type=float, default=2.0, help='Motion threshold %% to publish events (default: 2.0)')
    mqtt_parser.add_argument('--transport', choices=['tcp', 'udp'], default='tcp',
                            help='RTSP transport: tcp (stable) or udp (lower latency)')
    
    # Shell command - interactive LLM shell (NEW!)
    shell_parser = subparsers.add_parser('shell', help='Interactive LLM shell for natural language commands')
    shell_parser.add_argument('--model', '-m', default='llama3.2', help='LLM model (default: llama3.2)')
    shell_parser.add_argument('--provider', '-p', choices=['ollama', 'openai'], default='ollama',
                              help='LLM provider (default: ollama)')
    shell_parser.add_argument('--auto', '-a', action='store_true', help='Auto-execute commands without confirmation')
    shell_parser.add_argument('--verbose', '-v', action='store_true', help='Show LLM responses')
    
    # Functions command - list available functions (NEW!)
    funcs_parser = subparsers.add_parser('functions', help='List available functions for LLM')
    funcs_parser.add_argument('--category', '-c', help='Filter by category')
    funcs_parser.add_argument('--json', action='store_true', help='Output as JSON')
    funcs_parser.add_argument('--llm', action='store_true', help='Output for LLM context')
    
    # Voice Shell command - WebSocket voice interface (NEW!)
    voice_shell_parser = subparsers.add_parser('voice-shell', help='Voice-enabled shell with browser UI')
    voice_shell_parser.add_argument('--host', default='0.0.0.0', help='Host to bind (default: 0.0.0.0)')
    voice_shell_parser.add_argument('--port', '-p', type=int, default=8765, help='WebSocket port (default: 8765)')
    voice_shell_parser.add_argument('--model', '-m', default='llama3.2', help='LLM model (default: llama3.2)')
    voice_shell_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    voice_shell_parser.add_argument('--lang', '-l', default='en', help='Default language (en, pl, de)')
    
    # Accounting command - document scanning, OCR, invoices (NEW!)
    acc_parser = subparsers.add_parser('accounting', help='Księgowość: skanowanie dokumentów, OCR, faktury, paragony')
    acc_parser.add_argument('operation', choices=['scan', 'analyze', 'interactive', 'summary', 'export', 'list', 'create', 'engines', 'watch', 'batch', 'ask', 'auto', 'web', 'preview'],
                            nargs='?', default='interactive', help='Operacja (default: interactive)')
    acc_parser.add_argument('--project', '-p', default='default', help='Nazwa projektu księgowego')
    acc_parser.add_argument('--source', '-s', choices=['camera', 'screen', 'file'], default='screen',
                            help='Źródło obrazu: screen (domyślne), camera, file')
    acc_parser.add_argument('--file', '-f', help='Ścieżka do pliku obrazu')
    acc_parser.add_argument('--folder', help='Folder do obserwacji/przetwarzania (watch/batch)')
    acc_parser.add_argument('--type', '-t', choices=['invoice', 'receipt', 'contract', 'auto'], default='auto',
                            help='Typ dokumentu: invoice (faktura), receipt (paragon), contract (umowa), auto')
    acc_parser.add_argument('--ocr-engine', choices=['tesseract', 'easyocr', 'paddleocr', 'doctr', 'auto'], 
                            default='auto', help='Silnik OCR (default: auto - wybiera najlepszy)')
    acc_parser.add_argument('--lang', '-l', default='pol', help='Język OCR: pol, eng, deu (default: pol)')
    acc_parser.add_argument('--crop', action='store_true', default=True, help='Automatyczne przycinanie dokumentu')
    acc_parser.add_argument('--no-crop', action='store_true', help='Wyłącz przycinanie')
    acc_parser.add_argument('--preview', action='store_true', help='Pokaż podgląd ujęcia przed zapisem')
    acc_parser.add_argument('--confirm', action='store_true', help='Wymagaj potwierdzenia ujęcia (y/n)')
    acc_parser.add_argument('--tts', action='store_true', help='Odczytuj wyniki głosowo')
    acc_parser.add_argument('--format', choices=['csv', 'json'], default='csv', help='Format eksportu')
    acc_parser.add_argument('--question', '-q', help='Pytanie do asystenta (dla operacji ask)')
    acc_parser.add_argument('--interval', '-i', type=float, default=2.0, help='Interwał skanowania (sekundy)')
    acc_parser.add_argument('--no-browser', action='store_true', help='Nie otwieraj przeglądarki automatycznie (web)')
    acc_parser.add_argument('--port', type=int, default=8088, help='Port interfejsu web (web)')
    acc_parser.add_argument('--camera-device', type=int, default=0, help='Numer urządzenia kamery lokalnej (default: 0)')
    acc_parser.add_argument('--rtsp', help='URL kamery RTSP (np. rtsp://user:pass@192.168.1.100:554/stream)')
    acc_parser.add_argument('--camera', help='Nazwa kamery z .env (SQ_CAMERAS) lub indeks (0,1,2...)')
    acc_parser.add_argument('--receipt', '--paragon', action='store_true', help='Tryb wykrywania paragonów (zoptymalizowany)')
    acc_parser.add_argument('--invoice', '--faktura', action='store_true', help='Tryb wykrywania faktur (zoptymalizowany)')
    acc_parser.add_argument('--document', '--doc', action='store_true', help='Tryb wykrywania dokumentów ogólnych')
    acc_parser.add_argument('--detect-mode', choices=['fast', 'accurate', 'auto'], default='auto', help='Tryb detekcji: fast (szybki), accurate (dokładny), auto')
    
    # Global options
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--quiet', '-q', action='store_true', help='Quiet mode')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Enable diagnostics
    if args.debug:
        enable_diagnostics(level="DEBUG")
    
    try:
        # Route to handler
        if args.command == 'get':
            return handle_get(args)
        elif args.command == 'post':
            return handle_post(args)
        elif args.command == 'file':
            return handle_file(args)
        elif args.command == 'kafka':
            return handle_kafka(args)
        elif args.command == 'postgres':
            return handle_postgres(args)
        elif args.command == 'email':
            return handle_email(args)
        elif args.command == 'slack':
            return handle_slack(args)
        elif args.command == 'transform':
            return handle_transform(args)
        elif args.command == 'ssh':
            return handle_ssh(args)
        elif args.command == 'llm':
            return handle_llm(args)
        elif args.command == 'setup':
            return handle_setup(args)
        elif args.command == 'template':
            return handle_template(args)
        elif args.command == 'registry':
            return handle_registry(args)
        elif args.command == 'webapp':
            return handle_webapp(args)
        elif args.command == 'desktop':
            return handle_desktop(args)
        elif args.command == 'media':
            return handle_media(args)
        elif args.command == 'service':
            return handle_service(args)
        elif args.command == 'voice':
            return handle_voice(args)
        elif args.command == 'auto':
            return handle_auto(args)
        elif args.command == 'bot':
            return handle_bot(args)
        elif args.command == 'voice-click':
            return handle_voice_mouse(args)
        elif args.command == 'deploy':
            return handle_deploy(args)
        elif args.command == 'stream':
            return handle_stream(args)
        elif args.command == 'network':
            return handle_network(args)
        elif args.command == 'config':
            return handle_config(args)
        elif args.command == 'tracking':
            return handle_tracking(args)
        elif args.command == 'motion':
            return handle_motion(args)
        elif args.command == 'smart':
            return handle_smart(args)
        elif args.command == 'live':
            return handle_live(args)
        elif args.command == 'watch':
            return handle_watch(args)
        elif args.command == 'visualize':
            return handle_visualize(args)
        elif args.command == 'mqtt':
            return handle_mqtt(args)
        elif args.command == 'shell':
            return handle_shell(args)
        elif args.command == 'functions':
            return handle_functions(args)
        elif args.command == 'voice-shell':
            return handle_voice_shell(args)
        elif args.command == 'accounting':
            return handle_accounting(args)
        else:
            print(f"Unknown command: {args.command}", file=sys.stderr)
            return 1
            
    except StreamwareError as e:
        if not args.quiet:
            print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        if not args.quiet:
            print("\nInterrupted", file=sys.stderr)
        return 130
    except Exception as e:
        if not args.quiet:
            print(f"Error: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
