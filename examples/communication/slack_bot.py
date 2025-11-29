#!/usr/bin/env python3
"""
Slack Bot - Send messages to Slack channels

Requirements:
    export SLACK_TOKEN=xoxb-your-token

Related:
    - docs/v2/components/COMMUNICATION.md
    - streamware/components/slack.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from streamware import flow


def send_message(channel: str, message: str, token: str = None):
    """Send message to Slack channel"""
    token = token or os.environ.get("SLACK_TOKEN")
    if not token:
        print("❌ SLACK_TOKEN not set")
        return
    
    uri = f"slack://send?channel={channel}&message={message}&token={token}"
    result = flow(uri).run()
    return result


def demo():
    print("=" * 60)
    print("SLACK BOT DEMO")
    print("=" * 60)
    
    print("\n📋 Usage examples:")
    print("   # Send message")
    print("   sq slack general --message 'Hello team!'")
    print("")
    print("   # With token")
    print("   sq slack #alerts --message 'Server down!' --token xoxb-...")
    print("")
    print("   # Python")
    print("   from streamware import flow")
    print("   flow('slack://send?channel=general&message=Hello').run()")
    
    print("\n🔧 Setup:")
    print("   export SLACK_TOKEN=xoxb-your-token")
    
    if len(sys.argv) >= 3:
        channel = sys.argv[1]
        message = sys.argv[2]
        print(f"\n📤 Sending to #{channel}: {message}")
        result = send_message(channel, message)
        print(f"✅ {result}")


if __name__ == "__main__":
    demo()
