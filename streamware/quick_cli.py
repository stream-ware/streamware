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
