#!/usr/bin/env python3
"""
Natural Language Configuration Demo
Shows how to use natural language to configure Streamware.
"""

from streamware.intent import parse_intent, apply_intent, EXAMPLES

def demo_parsing():
    """Demonstrate parsing various natural language commands."""
    
    print("=" * 60)
    print("NATURAL LANGUAGE PARSING DEMO")
    print("=" * 60)
    print()
    
    # Test commands in English and Polish
    commands = [
        # English
        "track person",
        "count people in the room",
        "describe what's happening",
        "fast detection of cars",
        "alert when someone enters",
        
        # Polish
        "śledź osoby",
        "ile osób",
        "opisz co się dzieje",
        "powiadom gdy ktoś wchodzi",
        "szybko wykrywaj ruch",
    ]
    
    for cmd in commands:
        intent = parse_intent(cmd)
        print(f'"{cmd}"')
        print(f"  → {intent.describe()}")
        print(f"  → action={intent.action}, target={intent.target}, fps={intent.fps}")
        print()


def demo_apply():
    """Demonstrate applying intent to config."""
    from streamware.config import config
    
    print("=" * 60)
    print("APPLYING INTENT TO CONFIG")
    print("=" * 60)
    print()
    
    intent = parse_intent("track person fast")
    apply_intent(intent)
    
    print("Config after applying intent:")
    print(f"  SQ_STREAM_FPS: {config.get('SQ_STREAM_FPS')}")
    print(f"  SQ_STREAM_MODE: {config.get('SQ_STREAM_MODE')}")
    print(f"  SQ_STREAM_FOCUS: {config.get('SQ_STREAM_FOCUS')}")
    print()


def demo_to_cli():
    """Demonstrate generating CLI arguments."""
    
    print("=" * 60)
    print("GENERATING CLI ARGUMENTS")
    print("=" * 60)
    print()
    
    intent = parse_intent("alert when someone enters")
    args = intent.to_cli_args()
    
    print(f"Intent: {intent.describe()}")
    print(f"CLI args: {' '.join(args)}")
    print()


def demo_to_env():
    """Demonstrate generating environment variables."""
    
    print("=" * 60)
    print("GENERATING ENVIRONMENT VARIABLES")
    print("=" * 60)
    print()
    
    intent = parse_intent("describe scene slowly")
    env = intent.to_env()
    
    print(f"Intent: {intent.describe()}")
    print("Environment variables:")
    for key, value in env.items():
        print(f"  {key}={value}")
    print()


if __name__ == "__main__":
    demo_parsing()
    demo_apply()
    demo_to_cli()
    demo_to_env()
