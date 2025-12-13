"""
CLI Handlers - Basic I/O Operations

Handlers for: get, post, file, kafka, postgres, email, slack, transform, llm
"""

import sys
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse


def _get_pipeline():
    """Lazy import for Pipeline."""
    from .dsl import Pipeline
    return Pipeline


def _get_flow():
    """Lazy import for flow."""
    from .core import flow
    return flow


def handle_get(args) -> int:
    """Handle GET command"""
    Pipeline = _get_pipeline()
    
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
    Pipeline = _get_pipeline()
    
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
    Pipeline = _get_pipeline()
    
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
    Pipeline = _get_pipeline()
    
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
    Pipeline = _get_pipeline()
    
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
    Pipeline = _get_pipeline()
    
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
    Pipeline = _get_pipeline()
    
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
    Pipeline = _get_pipeline()
    
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
    flow = _get_flow()
    
    # Get input
    if args.input:
        with open(args.input, 'r') as f:
            prompt = f.read()
    elif args.prompt:
        prompt = args.prompt
    else:
        # Read from stdin
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
