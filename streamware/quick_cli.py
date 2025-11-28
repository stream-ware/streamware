"""
Quick CLI - Simplified shell interface for Streamware

Provides shorter, more intuitive commands for common operations.
"""

import sys
import argparse
import json
from pathlib import Path
from typing import Any, Optional
from .core import flow
from .dsl import Pipeline, quick
from .diagnostics import enable_diagnostics
from .exceptions import StreamwareError


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
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # GET command
    get_parser = subparsers.add_parser('get', help='HTTP GET request')
    get_parser.add_argument('url', help='URL to fetch (http:// optional)')
    get_parser.add_argument('--json', action='store_true', help='Parse as JSON')
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
                           default='openai', help='LLM provider')
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
    media_parser.add_argument('--model', default='llava', help='AI model')
    media_parser.add_argument('--prompt', help='Custom prompt for AI analysis')
    media_parser.add_argument('--output', help='Output file')
    
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
        elif args.command == 'deploy':
            return handle_deploy(args)
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
    provider = args.provider
    model_param = f"&model={args.model}" if args.model else ""
    
    if args.to_sql:
        uri = f"llm://sql?prompt={prompt}&provider={provider}{model_param}"
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
        uri = f"llm://streamware?prompt={prompt}&provider={provider}{model_param}"
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
        uri = f"llm://convert?to=bash&prompt={prompt}&provider={provider}{model_param}"
        result = flow(uri).run()
        
        if not args.quiet:
            print("# Generated bash command:")
            print(result)
        
        if args.execute:
            import subprocess
            print("\n# Executing...")
            subprocess.run(result, shell=True)
    
    elif args.analyze:
        uri = f"llm://analyze?prompt={prompt}&provider={provider}{model_param}"
        result = flow(uri).run()
        
        if isinstance(result, dict):
            import json
            print(json.dumps(result, indent=2))
        else:
            print(result)
    
    elif args.summarize:
        uri = f"llm://summarize?prompt={prompt}&provider={provider}{model_param}"
        result = flow(uri).run()
        print(result)
    
    else:
        # Default: generate
        uri = f"llm://generate?prompt={prompt}&provider={provider}{model_param}"
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


def handle_auto(args) -> int:
    """Handle automation command"""
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


if __name__ == '__main__':
    sys.exit(main())
