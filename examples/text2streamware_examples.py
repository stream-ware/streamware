#!/usr/bin/env python3
"""
Text to Streamware Examples - Qwen2.5 14B

Demonstrates natural language to Streamware Quick commands using Qwen2.5 14B.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from streamware import flow
from streamware.components.text2streamware import text_to_sq, explain_command, optimize_command


def example_1_basic_conversion():
    """Example 1: Basic Text to sq Conversion"""
    print("\n=== Example 1: Basic Conversion ===")
    
    requests = [
        "upload file to server",
        "get all users from database",
        "send email to admin",
        "download backup from FTP",
        "check server health",
    ]
    
    for req in requests:
        print(f"\n📝 Request: {req}")
        
        # Convert using Qwen2.5
        cmd = text_to_sq(req, model="qwen2.5:14b")
        print(f"🤖 Command: {cmd}")


def example_2_complex_requests():
    """Example 2: Complex Multi-step Requests"""
    print("\n=== Example 2: Complex Requests ===")
    
    requests = [
        "get users from API, filter active ones, and save to CSV",
        "upload deployment package to production server and restart service",
        "query database for last week's orders and send report via email",
        "monitor disk space and alert on Slack if above 90%",
        "backup database and upload to three different servers",
    ]
    
    for req in requests:
        print(f"\n📝 Request: {req}")
        
        cmd = text_to_sq(req, model="qwen2.5:14b")
        print(f"🤖 Command: {cmd}")


def example_3_explain_commands():
    """Example 3: Explain Existing Commands"""
    print("\n=== Example 3: Command Explanation ===")
    
    commands = [
        "sq ssh prod.com --deploy app.tar.gz --restart myapp",
        "sq postgres \"SELECT * FROM users WHERE created_at > NOW() - INTERVAL '7 days'\" --csv",
        "sq kafka events --consume --json --stream",
    ]
    
    for cmd in commands:
        print(f"\n💻 Command: {cmd}")
        
        explanation = explain_command(cmd, model="qwen2.5:14b")
        print(f"📖 Explanation: {explanation}")


def example_4_optimize_commands():
    """Example 4: Optimize Commands"""
    print("\n=== Example 4: Command Optimization ===")
    
    commands = [
        "streamware \"http://api.example.com/data\" --pipe \"transform://json\" --pipe \"file://write?path=output.json\"",
        "sq file input.json --json | sq postgres \"INSERT INTO table VALUES (...)\"",
    ]
    
    for cmd in commands:
        print(f"\n📝 Original: {cmd}")
        
        optimized = optimize_command(cmd, model="qwen2.5:14b")
        print(f"⚡ Optimized: {optimized}")


def example_5_interactive_assistant():
    """Example 5: Interactive Assistant"""
    print("\n=== Example 5: Interactive Assistant ===")
    
    print("""
    # Interactive Streamware Assistant with Qwen2.5
    
    while true; do
        read -p "What do you want to do? " request
        
        # Generate command
        cmd=$(sq llm "$request" --to-sq --provider ollama --model qwen2.5:14b)
        
        echo "Generated: $cmd"
        
        # Confirm and execute
        read -p "Execute? (y/n) " confirm
        if [[ "$confirm" == "y" ]]; then
            eval "$cmd"
        fi
    done
    """)


def example_6_automation_builder():
    """Example 6: Automation Script Builder"""
    print("\n=== Example 6: Automation Builder ===")
    
    print("""
    # Build automation scripts using natural language
    
    # User describes workflow
    workflow="
    1. Check server health every 5 minutes
    2. If unhealthy, restart service
    3. Send notification to Slack
    4. Log the incident to database
    "
    
    # Generate script
    sq llm "$workflow" --to-bash --provider ollama --model qwen2.5:14b > monitor.sh
    
    # Review and deploy
    cat monitor.sh
    chmod +x monitor.sh
    ./monitor.sh
    """)


def example_7_email_to_command():
    """Example 7: Email-Driven Commands"""
    print("\n=== Example 7: Email to Command ===")
    
    print("""
    # Process emails and convert to commands with Qwen2.5
    
    while true; do
        # Get command emails
        emails=$(sq email ops@company.com --subject "EXECUTE:" --unread --save /tmp/emails.json)
        
        # Process each email
        for email in $(cat /tmp/emails.json | jq -r '.[].body'); do
            echo "Email request: $email"
            
            # Convert to sq command using Qwen2.5
            cmd=$(python3 << EOF
from streamware.components.text2streamware import text_to_sq
print(text_to_sq("$email", model="qwen2.5:14b"))
EOF
            )
            
            echo "Generated command: $cmd"
            
            # Execute with safety check
            if [[ "$cmd" =~ ^sq ]]; then
                eval "$cmd"
                
                # Report success
                sq slack ops --message "✓ Executed: $cmd" --token $SLACK_TOKEN
            else
                sq slack ops --message "✗ Invalid command generated" --token $SLACK_TOKEN
            fi
        done
        
        sleep 60
    done
    """)


def example_8_voice_to_command():
    """Example 8: Voice Commands"""
    print("\n=== Example 8: Voice to Command ===")
    
    print("""
    # Voice-controlled Streamware
    
    # 1. Record voice
    arecord -d 5 -f cd -t wav voice.wav
    
    # 2. Transcribe with Whisper (local)
    text=$(whisper voice.wav --model base --output_format txt)
    
    # 3. Convert to sq command with Qwen2.5
    cmd=$(python3 << EOF
from streamware.components.text2streamware import text_to_sq
print(text_to_sq("$text", model="qwen2.5:14b"))
EOF
    )
    
    echo "You said: $text"
    echo "Command: $cmd"
    
    # 4. Execute
    read -p "Execute? (y/n) " confirm
    [[ "$confirm" == "y" ]] && eval "$cmd"
    """)


def example_9_ai_devops_assistant():
    """Example 9: AI DevOps Assistant"""
    print("\n=== Example 9: AI DevOps Assistant ===")
    
    print("""
    # AI-powered DevOps operations
    
    #!/bin/bash
    # devops-ai.sh
    
    assistant() {
        local task="$1"
        
        echo "🤖 AI DevOps Assistant"
        echo "Task: $task"
        
        # Generate command with Qwen2.5
        cmd=$(python3 -c "
from streamware.components.text2streamware import text_to_sq
print(text_to_sq('$task', model='qwen2.5:14b'))
")
        
        echo "Generated: $cmd"
        
        # Safety validation
        if [[ "$cmd" =~ (rm -rf|sudo|DELETE|DROP) ]]; then
            echo "⚠️  Dangerous operation detected!"
            read -p "Confirm execution? (yes/no) " confirm
            [[ "$confirm" != "yes" ]] && return 1
        fi
        
        # Execute
        eval "$cmd"
        
        # Log
        sq postgres "INSERT INTO devops_log (task, command, timestamp) 
            VALUES ('$task', '$cmd', NOW())"
    }
    
    # Usage examples
    assistant "deploy application to production"
    assistant "backup all databases"
    assistant "check disk space on all servers"
    assistant "restart failed services"
    """)


def example_10_smart_pipeline_builder():
    """Example 10: Smart Pipeline Builder"""
    print("\n=== Example 10: Pipeline Builder ===")
    
    print("""
    # Build complex pipelines with natural language
    
    #!/usr/bin/env python3
    from streamware.components.text2streamware import text_to_sq
    
    def build_pipeline(description):
        '''Build pipeline from description'''
        
        print(f"Building pipeline: {description}")
        
        # Split into steps
        steps = description.split(',')
        
        commands = []
        for step in steps:
            step = step.strip()
            cmd = text_to_sq(step, model="qwen2.5:14b")
            commands.append(cmd)
            print(f"  Step: {step}")
            print(f"  Command: {cmd}")
        
        # Create pipeline script
        script = "#!/bin/bash\\nset -e\\n\\n"
        for i, cmd in enumerate(commands):
            script += f"# Step {i+1}\\n"
            script += f"{cmd}\\n\\n"
        
        return script
    
    # Example usage
    pipeline_desc = '''
        get data from API,
        transform to CSV,
        upload to FTP server,
        send notification to Slack
    '''
    
    script = build_pipeline(pipeline_desc)
    
    # Save and execute
    with open('pipeline.sh', 'w') as f:
        f.write(script)
    
    import os
    os.chmod('pipeline.sh', 0o755)
    
    print("\\nGenerated pipeline.sh:")
    print(script)
    """)


def main():
    """Run all examples"""
    print("=" * 70)
    print("TEXT TO STREAMWARE EXAMPLES - Qwen2.5 14B")
    print("=" * 70)
    
    examples = [
        example_1_basic_conversion,
        example_2_complex_requests,
        example_3_explain_commands,
        example_4_optimize_commands,
        example_5_interactive_assistant,
        example_6_automation_builder,
        example_7_email_to_command,
        example_8_voice_to_command,
        example_9_ai_devops_assistant,
        example_10_smart_pipeline_builder,
    ]
    
    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"\nNote: {example.__name__} - {e}")
            print("(Make sure Qwen2.5 14B is installed: ollama pull qwen2.5:14b)")
    
    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70)
    print("\n🚀 Quick Start:")
    print("  # Install Qwen2.5 14B")
    print("  ollama pull qwen2.5:14b")
    print()
    print("  # Test conversion")
    print('  python3 -c "from streamware.components.text2streamware import text_to_sq; print(text_to_sq(\\'upload file to server\\'))"')
    print()
    print("  # Interactive mode")
    print("  sq llm 'your request' --to-sq --provider ollama --model qwen2.5:14b")


if __name__ == "__main__":
    main()
