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
    watch_parser.add_argument('--url', '-u', required=True, help='Video source')
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
    
    # Live narrator command (TTS, triggers)
    live_parser = subparsers.add_parser('live', help='Live narration with TTS and triggers', parents=[format_parser])
    live_parser.add_argument('operation', choices=['narrator', 'watch', 'describe'],
                             nargs='?', default='narrator', help='Operation')
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


def handle_get(args) -> int:
    """Handle GET command"""
    # Add http:// if missing
    url = args.url
    if not url.startswith(('http://', 'https://')):
        url = f"http://{url}"
    
    # Build pipeline
    pipeline = Pipeline().http_get(url)
    
    if args.json:
        pipeline = pipeline.to_json()
    
    if args.csv:
        pipeline = pipeline.to_csv()
    
    if args.save:
        pipeline = pipeline.save(args.save)
    
    # Execute
    result = pipeline.run()
    
    # Output
    if not args.save and not args.quiet:
        if args.pretty and args.json:
            print(json.dumps(result, indent=2))
        else:
            print(result)
    
    return 0


def handle_post(args) -> int:
    """Handle POST command"""
    url = args.url
    if not url.startswith(('http://', 'https://')):
        url = f"http://{url}"
    
    # Load data
    data = None
    if args.data:
        if args.data.startswith('@'):
            with open(args.data[1:], 'r') as f:
                data = f.read()
        else:
            data = args.data
    
    # Build pipeline
    pipeline = Pipeline().http_post(url, data)
    
    if args.json:
        pipeline = pipeline.to_json()
    
    if args.save:
        pipeline = pipeline.save(args.save)
    
    result = pipeline.run()
    
    if not args.save and not args.quiet:
        print(result)
    
    return 0


def handle_file(args) -> int:
    """Handle FILE command"""
    pipeline = Pipeline().read_file(args.path)
    
    if args.json:
        pipeline = pipeline.to_json()
    
    if args.csv:
        pipeline = pipeline.to_csv()
    
    if args.base64:
        pipeline = pipeline.to_base64(decode=args.decode)
    
    if args.save:
        pipeline = pipeline.save(args.save)
    
    result = pipeline.run()
    
    if not args.save and not args.quiet:
        print(result)
    
    return 0


def handle_kafka(args) -> int:
    """Handle KAFKA command"""
    if args.consume or args.stream:
        pipeline = Pipeline().from_kafka(args.topic, group=args.group)
        
        if args.json:
            pipeline = pipeline.to_json()
        
        if args.stream:
            for item in pipeline.stream():
                print(item)
        else:
            result = pipeline.run()
            if not args.quiet:
                print(result)
    
    elif args.produce:
        if not args.data:
            print("Error: --data required for produce", file=sys.stderr)
            return 1
        
        pipeline = Pipeline().to_kafka(args.topic)
        result = pipeline.run(args.data)
        
        if not args.quiet:
            print(f"Produced to {args.topic}")
    
    return 0


def handle_postgres(args) -> int:
    """Handle POSTGRES command"""
    pipeline = Pipeline().from_postgres(args.sql)
    
    if args.json:
        pipeline = pipeline.to_json()
    
    if args.csv:
        pipeline = pipeline.to_csv()
    
    if args.save:
        pipeline = pipeline.save(args.save)
    
    result = pipeline.run()
    
    if not args.save and not args.quiet:
        print(result)
    
    return 0


def handle_email(args) -> int:
    """Handle EMAIL command"""
    body = args.body
    if args.file:
        with open(args.file, 'r') as f:
            body = f.read()
    
    if not body:
        print("Error: --body or --file required", file=sys.stderr)
        return 1
    
    pipeline = Pipeline().send_email(args.to, args.subject)
    result = pipeline.run(body)
    
    if not args.quiet:
        print(f"Email sent to {args.to}")
    
    return 0


def handle_slack(args) -> int:
    """Handle SLACK command"""
    import os
    token = args.token or os.environ.get('SLACK_BOT_TOKEN')
    
    if not token:
        print("Error: --token required or set SLACK_BOT_TOKEN", file=sys.stderr)
        return 1
    
    pipeline = Pipeline().send_slack(args.channel, token)
    result = pipeline.run(args.message)
    
    if not args.quiet:
        print(f"Message sent to #{args.channel}")
    
    return 0


def handle_transform(args) -> int:
    """Handle TRANSFORM command"""
    # Read input
    if args.input:
        with open(args.input, 'r') as f:
            data = f.read()
    else:
        data = sys.stdin.read()
    
    # Transform
    pipeline = Pipeline()
    
    if args.type == 'json':
        result = pipeline.to_json().run(data)
    elif args.type == 'csv':
        result = pipeline.to_csv().run(data)
    elif args.type == 'base64':
        result = pipeline.to_base64(decode=args.decode).run(data)
    else:
        result = data
    
    # Output
    if args.output:
        with open(args.output, 'w') as f:
            f.write(str(result))
    else:
        print(result)
    
    return 0


def handle_llm(args) -> int:
    """Handle LLM command"""
    # Get input
    if args.input:
        with open(args.input, 'r') as f:
            prompt = f.read()
    elif args.prompt:
        prompt = args.prompt
    else:
        # Read from stdin
        import sys
        prompt = sys.stdin.read()
    
    if not prompt:
        print("Error: No input provided", file=sys.stderr)
        return 1
    
    # Build URI based on operation
    provider_param = f"&provider={args.provider}" if args.provider else ""
    model_param = f"&model={args.model}" if args.model else ""
    
    if args.to_sql:
        uri = f"llm://sql?prompt={prompt}{provider_param}{model_param}"
        result = flow(uri).run()
        
        if not args.quiet:
            print("-- Generated SQL:")
            print(result)
        
        if args.execute:
            # Execute the SQL
            exec_result = flow(f"postgres://{result}").run()
            print("\n-- Result:")
            print(exec_result)
    
    elif args.to_sq:
        uri = f"llm://streamware?prompt={prompt}{provider_param}{model_param}"
        result = flow(uri).run()
        
        if not args.quiet:
            print("# Generated Streamware command:")
            print(result)
        
        if args.execute:
            # Execute the command
            import subprocess
            print("\n# Executing...")
            subprocess.run(result, shell=True)
    
    elif args.to_bash:
        uri = f"llm://convert?to=bash&prompt={prompt}{provider_param}{model_param}"
        result = flow(uri).run()
        
        if not args.quiet:
            print("# Generated bash command:")
            print(result)
        
        if args.execute:
            import subprocess
            print("\n# Executing...")
            subprocess.run(result, shell=True)
    
    elif args.analyze:
        uri = f"llm://analyze?prompt={prompt}{provider_param}{model_param}"
        result = flow(uri).run()
        
        if isinstance(result, dict):
            import json
            print(json.dumps(result, indent=2))
        else:
            print(result)
    
    elif args.summarize:
        uri = f"llm://summarize?prompt={prompt}{provider_param}{model_param}"
        result = flow(uri).run()
        print(result)
    
    else:
        # Default: generate
        uri = f"llm://generate?prompt={prompt}{provider_param}{model_param}"
        result = flow(uri).run()
        print(result)
    
    return 0


def handle_setup(args) -> int:
    """Handle setup command"""
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
            import json
            print(json.dumps(result, indent=2))
        
        return 0 if result.get("success", True) else 1
    except Exception as e:
        print(f"Setup failed: {e}", file=sys.stderr)
        return 1


def handle_template(args) -> int:
    """Handle template command"""
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
            import json
            print(json.dumps(result, indent=2))
        
        return 0
    except Exception as e:
        print(f"Template operation failed: {e}", file=sys.stderr)
        return 1


def handle_registry(args) -> int:
    """Handle registry command"""
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
            import json
            print(json.dumps(result, indent=2))
        
        return 0
    except Exception as e:
        print(f"Registry operation failed: {e}", file=sys.stderr)
        return 1


def handle_webapp(args) -> int:
    """Handle webapp command"""
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
            import json
            print(json.dumps(result, indent=2))
        
        return 0
    except Exception as e:
        print(f"WebApp operation failed: {e}", file=sys.stderr)
        return 1


def handle_desktop(args) -> int:
    """Handle desktop command"""
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
            import json
            print(json.dumps(result, indent=2))
        
        return 0
    except Exception as e:
        print(f"Desktop operation failed: {e}", file=sys.stderr)
        return 1


def handle_media(args) -> int:
    """Handle media command"""
    
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
            import json
            print(json.dumps(result, indent=2))
        
        return 0
    except Exception as e:
        print(f"Media operation failed: {e}", file=sys.stderr)
        return 1


def handle_service(args) -> int:
    """Handle service command"""
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
            import json
            print(json.dumps(result, indent=2))
        
        return 0
    except Exception as e:
        print(f"Service operation failed: {e}", file=sys.stderr)
        return 1


def handle_voice(args) -> int:
    """Handle voice command"""
    uri = f"voice://{args.operation}?"
    
    if args.text:
        uri += f"text={args.text}&"
    if args.language:
        uri += f"language={args.language}&"
    
    try:
        result = flow(uri).run()
        
        if not args.quiet:
            import json
            print(json.dumps(result, indent=2))
        
        return 0
    except Exception as e:
        print(f"Voice operation failed: {e}", file=sys.stderr)
        return 1


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


def handle_auto(args) -> int:
    """Handle automation command"""
    
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
            import json
            print(json.dumps(result, indent=2))
        
        return 0
    except Exception as e:
        print(f"Automation operation failed: {e}", file=sys.stderr)
        return 1


def handle_bot(args) -> int:
    """Handle bot command"""
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
            import json
            print(json.dumps(result, indent=2))
        
        return 0
    except Exception as e:
        print(f"Bot operation failed: {e}", file=sys.stderr)
        return 1


def handle_voice_mouse(args) -> int:
    """Handle voice-click command"""
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
            import json
            print(json.dumps(result, indent=2))
        
        return 0
    except Exception as e:
        print(f"Voice mouse operation failed: {e}", file=sys.stderr)
        return 1


def handle_deploy(args) -> int:
    """Handle deploy command"""
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
    
    # Build URI
    platform = args.platform
    uri = f"deploy://{operation}?platform={platform}"
    
    if args.file:
        uri += f"&file={args.file}"
    if args.namespace:
        uri += f"&namespace={args.namespace}"
    if args.name:
        uri += f"&name={args.name}"
    if args.image:
        uri += f"&image={args.image}&tag={args.tag}"
    if args.scale:
        uri += f"&replicas={args.scale}"
    if args.project:
        uri += f"&project={args.project}"
    if args.stack:
        uri += f"&stack={args.stack}"
    if args.context:
        uri += f"&context={args.context}"
    
    # Execute
    try:
        result = flow(uri).run()
        
        if not args.quiet:
            if isinstance(result, dict):
                import json
                print(json.dumps(result, indent=2))
            else:
                print(result)
        
        return 0 if result.get("success", True) else 1
        
    except Exception as e:
        print(f"Deployment failed: {e}", file=sys.stderr)
        return 1


def handle_ssh(args) -> int:
    """Handle SSH command"""
    # Build URI
    uri_parts = [f"ssh://{args.host}"]
    params = [f"user={args.user}", f"port={args.port}"]
    
    if args.key:
        params.append(f"key={args.key}")
    
    # Determine operation
    if args.upload:
        uri = f"ssh://upload?host={args.host}&{'&'.join(params)}"
        if args.remote:
            uri += f"&remote={args.remote}"
        
        result = flow(uri).run(args.upload)
        
        if not args.quiet:
            print(f"✓ Uploaded {args.upload} to {args.host}:{args.remote or '/tmp'}")
        
    elif args.download:
        uri = f"ssh://download?host={args.host}&{'&'.join(params)}"
        uri += f"&remote={args.download}"
        if args.local:
            uri += f"&local={args.local}"
        
        result = flow(uri).run()
        
        if not args.quiet:
            print(f"✓ Downloaded {args.download} from {args.host}")
    
    elif args.exec:
        uri = f"ssh://exec?host={args.host}&{'&'.join(params)}"
        uri += f"&command={args.exec}"
        
        result = flow(uri).run()
        
        if not args.quiet:
            print(f"Exit code: {result.get('exit_code', 0)}")
            if result.get('stdout'):
                print(result['stdout'])
            if result.get('stderr'):
                print(result['stderr'], file=sys.stderr)
    
    elif args.deploy:
        uri = f"ssh://deploy?host={args.host}&{'&'.join(params)}"
        if args.remote:
            uri += f"&path={args.remote}"
        if args.restart:
            uri += f"&restart={args.restart}"
        
        result = flow(uri).run(args.deploy)
        
        if not args.quiet:
            print(f"✓ Deployed {args.deploy} to {args.host}")
            if args.restart:
                print(f"✓ Restarted service: {args.restart}")
    
    else:
        print("Error: Specify --upload, --download, --exec, or --deploy", file=sys.stderr)
        return 1
    
    return 0


def handle_stream(args) -> int:
    """Handle stream command for real-time video analysis"""
    
    # Show examples if URL required but missing
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
    
    # Check URL requirement
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
    
    # Enable frame saving if --file is specified
    save_frames = getattr(args, 'file', None) is not None
    if save_frames:
        uri += "save_frames=true&"
    
    try:
        result = flow(uri).run()
        
        # Save HTML report with images
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
    import base64
    from datetime import datetime
    from pathlib import Path
    
    # Create directory if it doesn't exist
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
        import json
        print(json.dumps(result, indent=2))
        return
    
    if fmt == "table":
        _print_stream_table(result)
        return
    
    # Default: YAML with diff-style
    _print_stream_yaml(result)


def _print_stream_yaml(result: dict):
    """Print stream result as YAML with clear change indicators"""
    timeline = result.get("timeline", [])
    changes = result.get("significant_changes", 0)
    frames = result.get("frames_analyzed", len(timeline))
    source = result.get("source", "")
    mode = result.get("mode", "diff")
    
    # Header
    print(f"# Stream Analysis")
    print(f"# Source: {source}")
    print(f"# Mode: {mode}")
    print(f"# Frames: {frames}, Changes: {changes}")
    print("---")
    print()
    
    # Status summary
    if changes == 0:
        print("status: ✅ NO_CHANGES")
    elif changes == 1:
        print("status: ⚠️ MINOR_ACTIVITY")
    else:
        print(f"status: 🔴 ACTIVITY_DETECTED ({changes} changes)")
    print()
    
    # Timeline with clear indicators
    print("timeline:")
    for event in timeline:
        frame = event.get("frame", 0)
        ts = event.get("timestamp", "")
        event_type = event.get("type", "")
        desc = event.get("changes", "")
        
        # Clear change indicator
        if event_type == "change":
            indicator = "🔴 CHANGE"
        else:
            indicator = "⚪ stable"
        
        print(f"  - frame: {frame}")
        print(f"    time: \"{ts}\"")
        print(f"    status: {indicator}")
        
        # Short description for no_change, full for change
        if event_type == "change":
            # Parse structured changes if present
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
                # Truncate long descriptions
                short = desc[:200].replace("\n", " ").strip()
                print(f"    description: \"{short}...\"")
        print()
    
    # Summary
    print("# Summary")
    print("summary:")
    print(f"  total_frames: {frames}")
    print(f"  changes_detected: {changes}")
    print(f"  change_ratio: {changes/frames*100:.1f}%" if frames > 0 else "  change_ratio: 0%")
    
    # Quick status for scripting
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
    
    # Table header
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


def _get_output_format(args) -> str:
    """Determine output format from global args (yaml is default)"""
    if getattr(args, 'json', False):
        return "json"
    if getattr(args, 'table', False):
        return "table"
    if getattr(args, 'html', False):
        return "html"
    # yaml is default
    return "yaml"


def handle_network(args) -> int:
    """Handle network scanning command"""
    
    # Show examples if needed
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
    
    # Validate
    if op == "find" and not args.query:
        show_examples("network find", examples["find"], "query")
        return 1
    if op in ["identify", "ports"] and not args.ip:
        show_examples(f"network {op}", examples.get(op, []), "ip")
        return 1
    
    # Determine output format from global flags
    output_format = _get_output_format(args)
    
    # Build URI
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
        import json
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
    
    # Header
    if op == "find" and query:
        print(f"# Network Search: '{query}'")
        print(f"# Found: {result.get('matched_devices', len(devices))} devices")
    else:
        print(f"# Network Scan: {result.get('subnet', 'N/A')}")
        print(f"# Total: {result.get('total_devices', len(devices))} devices")
    print("---")
    print()
    
    # Group by type
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
            
            # Connection info (RTSP, print URLs, etc.)
            conn = dev.get('connection', {})
            if conn:
                if 'rtsp' in conn:
                    print(f"    rtsp:")
                    for url in conn['rtsp'][:2]:  # Show first 2 URLs
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
    
    # Summary
    print("# Summary")
    print("summary:")
    for dtype in sorted(by_type.keys()):
        print(f"  {dtype}: {len(by_type[dtype])}")


def _print_network_table(result: dict, op: str, query: str = None):
    """Print result as ASCII table"""
    devices = result.get("devices", [])
    
    # Header
    if op == "find" and query:
        print(f"# Network Search: '{query}' - Found {len(devices)} devices")
    else:
        print(f"# Network Scan: {result.get('subnet', 'N/A')} - {len(devices)} devices")
    print()
    
    # Table header
    print("+" + "-" * 17 + "+" + "-" * 22 + "+" + "-" * 19 + "+" + "-" * 20 + "+")
    print(f"| {'IP':<15} | {'Hostname':<20} | {'MAC':<17} | {'Type':<18} |")
    print("+" + "=" * 17 + "+" + "=" * 22 + "+" + "=" * 19 + "+" + "=" * 20 + "+")
    
    # Sort by type, then IP
    for device in sorted(devices, key=lambda d: (d.get('type', 'zzz'), d.get('ip', ''))):
        ip = device.get('ip', '')[:15]
        hostname = (device.get('hostname') or 'N/A')[:20]
        mac = (device.get('mac') or 'N/A')[:17]
        dtype = device.get('description', 'Unknown')[:18]
        print(f"| {ip:<15} | {hostname:<20} | {mac:<17} | {dtype:<18} |")
    
    print("+" + "-" * 17 + "+" + "-" * 22 + "+" + "-" * 19 + "+" + "-" * 20 + "+")
    
    # Summary by type
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
    
    # Web panel
    if args.web:
        run_config_web(port=args.port)
        return 0
    
    # Show configuration
    if args.show:
        # Use the new diagnostic printer
        from .diagnostics import print_active_configuration
        print_active_configuration()
        return 0
    
    # Set value
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
    
    # Save to .env (full save only when explicitly requested)
    if args.save:
        config.save(full=True)
        print(f"💾 Configuration saved to .env (full)")
        return 0
    
    # Init .env from .env.example
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
    
    # Default: show help
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


def handle_tracking(args) -> int:
    """Handle object tracking command"""
    from .core import flow
    import json
    
    op = args.operation
    url = args.url
    
    # Build URI
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
        
        # Output format
        fmt = _get_output_format(args)
        
        if fmt == "json":
            print(json.dumps(result, indent=2))
        else:
            _print_tracking_yaml(result, op)
        
        # Save report if requested
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
    
    # Status
    total = summary.get("total_objects", 0)
    print(f"\nstatus: {'🔴 OBJECTS_DETECTED' if total > 0 else '✅ NO_OBJECTS'}")
    print(f"total_objects: {total}")
    
    # By type
    by_type = summary.get("by_type", {})
    if by_type:
        print("\nby_type:")
        for obj_type, count in by_type.items():
            print(f"  {obj_type}: {count}")
    
    # Objects
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
    
    # Events (for zones)
    events = result.get("events", [])
    if events:
        print(f"\nevents: # {len(events)} total")
        for event in events[:10]:
            icon = "➡️" if event.get("type") == "zone_enter" else "⬅️"
            print(f"  - {icon} [{event.get('timestamp')}] {event.get('object_type')} {event.get('type')} {event.get('zone')}")
    
    # Statistics (for count)
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
    from .core import flow
    import json
    from pathlib import Path
    
    op = getattr(args, 'operation', 'analyze') or 'analyze'
    url = args.url
    
    # Build URI
    uri = f"motion://{op}?source={url}"
    uri += f"&threshold={args.threshold}"
    uri += f"&min_region={getattr(args, 'min_region', 500)}"
    uri += f"&grid={args.grid}"
    uri += f"&focus={args.focus}"
    uri += f"&duration={args.duration}"
    uri += f"&interval={args.interval}"
    
    # Enable frame saving for reports
    if getattr(args, 'file', None):
        uri += "&save_frames=true"
    
    try:
        result = flow(uri).run()
        
        # Save HTML report if requested
        if getattr(args, 'file', None):
            _save_motion_html_report(result, args.file)
            print(f"📄 Report saved: {args.file}")
        
        # Output format
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
    
    # Status
    if changes == 0:
        print("status: ✅ NO_MOTION")
    else:
        print(f"status: 🔴 MOTION_DETECTED ({changes} changes)")
    print()
    
    # Timeline
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
            
            # Show region analyses if available
            region_analyses = frame.get("region_analyses", [])
            if region_analyses:
                print(f"    analysis:")
                for ra in region_analyses[:2]:
                    region = ra.get("region", {})
                    analysis = ra.get("analysis", "")[:150]
                    print(f"      - region: ({region.get('x')},{region.get('y')}) {region.get('width')}x{region.get('height')}")
                    print(f"        change: {region.get('change_percent')}%")
                    print(f"        description: \"{analysis}...\"")
            
            # Show summary
            summary = frame.get("changes", "")
            if summary and not region_analyses:
                print(f"    summary: \"{summary[:200]}...\"")
        print()
    
    # Summary
    print("# Summary")
    print("summary:")
    print(f"  frames: {frames}")
    print(f"  changes: {changes}")
    print(f"  change_ratio: {(changes/frames*100):.1f}%" if frames > 0 else "  change_ratio: 0%")


def _save_motion_html_report(result: dict, output_file: str):
    """Save motion analysis as HTML report"""
    from datetime import datetime
    from pathlib import Path
    
    # Create directory
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
        
        # Show region analyses
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
            <p class="mt-1">Method: Pixel-level diff → Region extraction → AI analysis on changed regions only</p>
        </footer>
    </div>
</body>
</html>
"""
    
    with open(output_path, "w") as f:
        f.write(html)


def handle_smart(args) -> int:
    """Handle smart monitoring command"""
    from .core import flow
    import json
    from pathlib import Path
    
    op = getattr(args, 'operation', 'monitor') or 'monitor'
    url = args.url
    
    # Build URI
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
    
    # Enable frame saving for reports
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
        
        # Save HTML report if requested
        if getattr(args, 'file', None):
            _save_smart_html_report(result, args.file)
            print(f"📄 Report saved: {args.file}")
        
        # Output format
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
    
    # Config
    print("config:")
    print(f"  interval: {config.get('min_interval', '?')}s - {config.get('max_interval', '?')}s")
    print(f"  adaptive: {config.get('adaptive', False)}")
    print(f"  buffer: {config.get('buffer_size', '?')}")
    print(f"  threshold: {config.get('threshold', '?')}")
    print()
    
    # Status
    if changes == 0:
        print("status: ✅ NO_CHANGES")
    else:
        print(f"status: 🔴 CHANGES_DETECTED ({changes})")
    print()
    
    # Stats
    print("stats:")
    print(f"  frames_captured: {captured}")
    print(f"  frames_with_changes: {changes}")
    print(f"  buffer_overflows: {result.get('buffer_overflows', 0)}")
    print()
    
    # Timeline (only changes)
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
            <p class="mt-1">Features: Frame buffering • Adaptive capture • Region analysis</p>
        </footer>
    </div>
</body>
</html>
"""
    
    with open(output_path, "w") as f:
        f.write(html)


def handle_watch(args) -> int:
    """Handle watch command with qualitative parameters"""
    from .core import flow
    from .presets import get_preset, describe_settings
    import json
    
    # Get optimized settings from qualitative params
    settings = get_preset(
        sensitivity=args.sensitivity,
        detect=args.detect,
        speed=args.speed
    )
    
    # Show what settings are being used
    desc = describe_settings(args.sensitivity, args.detect, args.speed)
    print(f"\n🎯 Watch Mode: {desc}")
    print(f"   Source: {args.url[:50]}...")
    print(f"   Duration: {args.duration}s")
    if args.alert != "none":
        print(f"   Alert: {args.alert}")
    print()
    
    # Build URI with optimized numeric parameters
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
        
        # Process alerts
        if args.alert != "none":
            changes = result.get("significant_changes", 0)
            if changes > 0:
                _trigger_alert(args.alert, args.detect, changes, args.url)
        
        # Output
        fmt = _get_output_format(args)
        
        if fmt == "json":
            print(json.dumps(result, indent=2, default=str))
        else:
            _print_watch_yaml(result, args)
        
        # Save HTML report or Markdown log
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
            print("\a")  # Terminal bell
    
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
                
                # Show AI analysis if available
                analyses = entry.get("region_analyses", [])
                if analyses:
                    desc = analyses[0].get("description", "")
                    print(f"    description: \"{desc}\"")


def _save_watch_report(result: dict, args):
    """Save watch report as HTML"""
    import os
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
            
            # Add image if available
            img = entry.get("image_base64", "")
            if img:
                html += f'<img class="frame" src="data:image/jpeg;base64,{img}">'
            
            # Add descriptions
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
    """Save watch result as Markdown log (configuration + change events)."""
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


def handle_live(args) -> int:
    """Handle live narration command"""
    from .core import flow
    # IMPORTANT: Import component to register it (lazy imports don't auto-register)
    from .components.live_narrator import LiveNarratorComponent
    import json
    
    op = getattr(args, 'operation', 'narrator') or 'narrator'
    url = args.url
    
    if not url:
        print("❌ Error: --url parameter is required (and cannot be empty).", file=sys.stderr)
        print("\nExamples:")
        print("  sq live narrator --url rtsp://192.168.1.100/stream")
        print("  sq live narrator --url /path/to/video.mp4")
        return 1
    
    # Auto-configure based on hardware
    auto_config = None
    if getattr(args, 'auto', False):
        from .performance_manager import auto_configure
        print("\n🔧 Auto-configuring based on hardware...", flush=True)
        auto_config = auto_configure()
        
        # Apply auto-config settings
        if not getattr(args, 'model', None):
            args.model = auto_config.vision_model
        if not getattr(args, 'interval', None):
            args.interval = auto_config.base_interval
        print()
    
    # Run benchmark if requested
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
    
    # Run startup checks (Ollama, models, TTS) - skip in test mode
    from .config import config
    
    vision_model = getattr(args, 'model', None) or config.get("SQ_MODEL", "llava:7b")
    guarder_model = config.get("SQ_GUARDER_MODEL", "gemma:2b")
    check_tts = getattr(args, 'tts', False)
    
    # Debug TTS flag
    if check_tts:
        print(f"🔊 TTS requested via --tts flag")
    
    # TURBO mode: skip checks + fast model + aggressive caching
    if getattr(args, 'turbo', False):
        print("🚀 TURBO mode: skip checks + fast model + aggressive caching")
        args.skip_checks = True
        args.fast = True
        if not getattr(args, 'model', None):
            # Use smaller/faster model for turbo mode
            args.model = 'llava:7b'  # Default fast model
        vision_model = args.model
    
    # FAST mode: auto-select smaller model if not specified
    if getattr(args, 'fast', False) and not getattr(args, 'model', None):
        # Try to use fastest available vision model
        fast_models = ['moondream', 'moondream:latest', 'llava:7b', 'bakllava']
        from .setup_utils import check_ollama_model
        for fast_model in fast_models:
            if check_ollama_model(fast_model):
                args.model = fast_model
                vision_model = fast_model
                print(f"⚡ Fast mode enabled: using {fast_model} model, aggressive caching")
                break
    
    # Skip checks if --skip-checks or model is not valid
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
    
    # Handle --intent for natural language configuration
    intent_str = getattr(args, 'intent', None)
    if intent_str and isinstance(intent_str, str):
        from .detection_pipeline import parse_user_intent
        intent, intent_params = parse_user_intent(intent_str)
        
        print(f"🎯 Intent: {intent.name}")
        print(f"   Focus: {intent_params.get('focus', 'person')}")
        print(f"   Sensitivity: {intent_params.get('sensitivity', 'medium')}")
        
        # Override mode and focus from intent
        mode = "track"
        if not getattr(args, 'focus', None):
            args.focus = intent_params.get('focus', 'person')
        
        # Set intent in config for pipeline to use
        config.set("SQ_INTENT", intent_str)
        config.set("SQ_INTENT_TYPE", intent.name)
    
    # Fast mode: use smaller model and aggressive optimization
    if getattr(args, 'fast', False):
        print("⚡ Fast mode enabled: using llava:7b model, aggressive caching")
        # Use llava:7b as default fast vision model
        from .setup_utils import check_ollama_model
        if not getattr(args, 'model', None):
            if check_ollama_model("llava:7b")[0]:
                args.model = "llava:7b"
            elif check_ollama_model("moondream")[0]:
                args.model = "moondream"
        # Set aggressive optimization
        config.set("SQ_FAST_MODE", "true")
    
    # Build URI
    uri = f"live://{op}?source={url}"
    tts_value = 'true' if args.tts else 'false'
    uri += f"&tts={tts_value}"

    # TTS mode selection
    tts_mode = 'normal'
    if getattr(args, 'tts_all', False):
        tts_mode = 'all'
    elif getattr(args, 'tts_diff', False):
        tts_mode = 'diff'
    uri += f"&tts_mode={tts_mode}"
    
    # Debug: show TTS status
    if args.tts:
        print(f"🔊 TTS enabled (--tts flag detected, mode={tts_mode})")
    uri += f"&mode={mode}"
    uri += f"&duration={args.duration}"
    
    # Descriptive parameters
    analysis = getattr(args, 'analysis', 'normal') or 'normal'
    motion = getattr(args, 'motion', 'significant') or 'significant'
    frames = getattr(args, 'frames', 'changed') or 'changed'
    
    uri += f"&analysis={analysis}"
    uri += f"&motion={motion}"
    uri += f"&frames_mode={frames}"
    
    # Add focus from args or intent
    focus = getattr(args, 'focus', None)
    if focus:
        uri += f"&focus={focus}"
    
    # Add intent if specified
    if intent_str and isinstance(intent_str, str):
        import urllib.parse
        uri += f"&intent={urllib.parse.quote(intent_str)}"
    
    # Add verbose flag
    if getattr(args, 'verbose', False):
        uri += "&verbose=true"
    
    # Add ramdisk flag
    use_ramdisk = getattr(args, 'ramdisk', True) and not getattr(args, 'no_ramdisk', False)
    uri += f"&ramdisk={'true' if use_ramdisk else 'false'}"
    
    # Optional frames output directory
    if getattr(args, 'frames_dir', None):
        uri += f"&frames_dir={args.frames_dir}"
    
    # Explicit numeric params (override descriptive presets)
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
    if getattr(args, 'model', None):
        uri += f"&model={args.model}"
    if getattr(args, 'lite', False):
        uri += "&lite=true"
    if getattr(args, 'quiet', False):
        uri += "&quiet=true"
    if getattr(args, 'realtime', False):
        uri += "&realtime=true"
    if getattr(args, 'dsl_only', False):
        uri += "&dsl_only=true"
    if getattr(args, 'fps', None):
        uri += f"&target_fps={args.fps}"
    
    # Enable guarder if requested
    if getattr(args, 'guarder', False):
        from .config import config
        config.set("SQ_USE_GUARDER", "true")
    
    # Setup timing logger if --log-file specified
    log_file = getattr(args, 'log_file', None)
    log_format = getattr(args, 'log_format', 'csv')
    if log_file and isinstance(log_file, str):
        from .timing_logger import set_log_file
        set_log_file(log_file, verbose=getattr(args, 'verbose', False))
        print(f"📊 Timing logs will be saved to: {log_file} (format: {log_format})")
        # Also pass through URI so component can access it
        uri += f"&log_file={log_file}&log_format={log_format}"
    
    # Show header only if not quiet and not structured format
    fmt = _get_output_format(args)
    # For structured output (json/yaml), suppress live prints
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
        
        # Save HTML report or Markdown log if requested
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
        .analysis-box span {{ display: inline-block; margin-right: 20px; }}
        .no-image {{ background: #0f0f23; padding: 30px; text-align: center; border-radius: 8px; color: #666; }}
        @media (max-width: 768px) {{
            .entry {{ grid-template-columns: 1fr; }}
        }}
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
            <div class="config-item">
                <div class="config-label">Model</div>
                <div>{config.get('model', 'unknown')}</div>
            </div>
            <div class="config-item">
                <div class="config-label">Mode</div>
                <div>{config.get('mode', mode)}</div>
            </div>
            <div class="config-item">
                <div class="config-label">Focus</div>
                <div>{config.get('focus', 'general')}</div>
            </div>
            <div class="config-item">
                <div class="config-label">Interval</div>
                <div>{config.get('interval', 3)}s</div>
            </div>
            <div class="config-item">
                <div class="config-label">Diff Threshold</div>
                <div>{config.get('diff_threshold', 15)}</div>
            </div>
            <div class="config-item">
                <div class="config-label">Min Change</div>
                <div>{config.get('min_change', 0.5)}%</div>
            </div>
            <div class="config-item">
                <div class="config-label">TTS</div>
                <div>{'✅ Enabled' if config.get('tts_enabled') else '❌ Disabled'}</div>
            </div>
            <div class="config-item">
                <div class="config-label">Source</div>
                <div style="font-size: 0.8em; word-break: break-all;">{source[:80]}...</div>
            </div>
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
        analysis = entry.get("analysis", {})
        frame_num = entry.get("frame", i+1)
        
        # Original image
        orig_html = f'<img src="data:image/jpeg;base64,{original_b64}" alt="Original">' if original_b64 else '<div class="no-image">No image</div>'
        
        # Annotated image (what LLM saw)
        if annotated_b64:
            annot_html = f'<img src="data:image/jpeg;base64,{annotated_b64}" alt="LLM View">'
        elif original_b64:
            annot_html = f'<img src="data:image/jpeg;base64,{original_b64}" alt="LLM View">'
        else:
            annot_html = '<div class="no-image">No annotation</div>'
        
        # Analysis info
        motion_pct = analysis.get("motion_percent", 0)
        has_motion = analysis.get("has_motion", False)
        likely_person = analysis.get("likely_person", False)
        person_conf = analysis.get("person_confidence", 0)
        
        analysis_html = ""
        if analysis:
            analysis_html = f'''
            <div class="analysis-box">
                <span>🎯 Motion: {motion_pct:.1f}%</span>
                <span>👤 Person likely: {"Yes" if likely_person else "No"} ({person_conf:.0%})</span>
                <span>🔍 Regions: {len(analysis.get("motion_regions", []))}</span>
            </div>'''
        
        html += f"""
    <div class="entry {triggered_class}">
        <div class="time">
            {'🔴 TRIGGER - ' if entry.get('triggered') else '📷 '}
            Frame #{frame_num} | {ts}
        </div>
        <div class="images-row">
            <div class="image-box">
                {orig_html}
                <div class="image-label">📷 Original Frame</div>
            </div>
            <div class="image-box">
                {annot_html}
                <div class="image-label">🔍 What LLM Analyzed (with motion boxes)</div>
            </div>
        </div>
        <div class="desc">{desc}</div>
        {analysis_html}
    </div>
"""
    
    html += f"""
    <footer style="text-align: center; margin-top: 30px; padding: 20px; color: #666; border-top: 1px solid #333;">
        Generated by Streamware at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
        <a href="https://github.com/streamware" style="color: #667eea;">github.com/streamware</a>
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
    lines.append(f"- **Interval**: `{config.get('interval', 3)}s`")
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
                joined = ", ".join(matches)
                lines.append(f"  - **Matches**: {joined}")
            lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")

    print(f"📄 Markdown log saved: {output_path}")


def _print_live_yaml(result: dict, mode: str = "full"):
    """Print live narrator result as YAML"""
    op = result.get("operation", "narrator")
    config = result.get("config", {})
    
    print(f"# Live Narrator - {op} ({mode} mode)")
    print("---")
    print()
    
    # Show config
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
            for entry in history[-10:]:  # Last 10
                triggered = "🔴 " if entry.get("triggered") else ""
                print(f"  - time: \"{entry.get('timestamp', '')[:19]}\"")
                print(f"    {triggered}description: \"{entry.get('description', '')}\"")
                if entry.get("matches"):
                    print(f"    matches: {entry.get('matches')}")


def handle_visualize(args) -> int:
    """Handle real-time visualization command."""
    from .realtime_visualizer import start_visualizer
    
    # Fast mode: lower resolution, higher FPS
    width = args.width
    height = args.height
    fps = args.fps
    video_mode = getattr(args, 'video_mode', 'ws')
    transport = getattr(args, 'transport', 'tcp')
    backend = getattr(args, 'backend', 'opencv')
    
    if getattr(args, 'fast', False):
        width = min(width, 320)
        height = min(height, 240)
        fps = min(15, max(fps, 10))
        print("⚡ Fast mode enabled")
    
    # TURBO mode: maximum speed settings
    if getattr(args, 'turbo', False):
        backend = 'pyav'
        transport = 'udp'
        video_mode = 'meta'
        width = min(width, 320)
        height = min(height, 240)
        fps = max(fps, 10)
        print("🚀 TURBO mode: PyAV + UDP + metadata-only")
    
    mode_label = "HLS + WebSocket overlay" if video_mode == "hls" else "JPEG over WebSocket"
    
    print(f"\n🎯 Starting Real-time Motion Visualizer")
    print(f"   URL: {args.url}")
    print(f"   Port: {args.port}")
    print(f"   FPS: {fps}")
    print(f"   Size: {width}x{height}")
    print(f"   Mode: {video_mode.upper()}")
    print(f"   Backend: {backend.upper()}")
    print(f"   Transport: {transport.upper()}")
    print(f"\n   Open http://localhost:{args.port} in browser\n")
    
    try:
        start_visualizer(
            rtsp_url=args.url,
            port=args.port,
            fps=fps,
            width=width,
            height=height,
            use_simple=getattr(args, 'simple', False),
            video_mode=video_mode,
            transport=transport,
            backend=backend,
        )
    except KeyboardInterrupt:
        print("\n🛑 Visualizer stopped")
    
    return 0


def handle_mqtt(args) -> int:
    """Handle MQTT DSL publisher command."""
    from .realtime_visualizer import start_mqtt_publisher
    
    print(f"\n📡 Starting MQTT DSL Publisher")
    print(f"   RTSP: {args.url}")
    print(f"   Broker: {args.broker}:{args.mqtt_port}")
    print(f"   Topic: {args.topic}/*")
    print(f"   FPS: {args.fps}")
    print(f"   Motion threshold: {args.threshold}%")
    print()
    
    try:
        start_mqtt_publisher(
            rtsp_url=args.url,
            mqtt_broker=args.broker,
            mqtt_port=args.mqtt_port,
            mqtt_username=args.username,
            mqtt_password=args.password,
            topic_prefix=args.topic,
            fps=args.fps,
            width=args.width,
            height=args.height,
            motion_threshold=args.threshold,
        )
    except KeyboardInterrupt:
        print("\n🛑 MQTT Publisher stopped")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
