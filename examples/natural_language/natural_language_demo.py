#!/usr/bin/env python3
"""
Natural Language Configuration Demo
Shows how to use natural language to configure Streamware.

NEW: Uses LLM-based parsing for better understanding.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from streamware.intent import parse_intent, apply_intent
from streamware.llm_intent import parse_command
from streamware.function_registry import registry, get_llm_context


def demo_llm_parsing():
    """Demonstrate LLM-based parsing (NEW - recommended)."""
    
    print("=" * 60)
    print("LLM-BASED PARSING (NEW)")
    print("=" * 60)
    print()
    
    commands = [
        "detect person and email admin@company.com immediately",
        "track cars for 10 minutes",
        "count people every minute",
        "describe scene and speak",
        "alert when someone enters via slack",
    ]
    
    for cmd in commands:
        print(f'"{cmd}"')
        try:
            intent = parse_command(cmd)
            print(f"  → {intent.describe()}")
            print(f"  → CLI: {intent.to_cli_string()}")
            if intent.llm_model:
                print(f"  → Parsed by: {intent.llm_model}")
            else:
                print(f"  → Fallback: heuristics")
        except Exception as e:
            print(f"  → Error: {e}")
        print()


def demo_heuristic_parsing():
    """Demonstrate heuristic-based parsing (fallback)."""
    
    print("=" * 60)
    print("HEURISTIC PARSING (FALLBACK)")
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


def demo_function_registry():
    """Demonstrate function registry for LLM."""
    
    print("=" * 60)
    print("FUNCTION REGISTRY")
    print("=" * 60)
    print()
    
    print("Available functions for LLM:")
    for cat in registry.categories():
        print(f"\n{cat.upper()}:")
        for fn in registry.get_by_category(cat):
            print(f"  - {fn.name}: {fn.description}")
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
    
    # Using LLM intent
    intent = parse_command("detect person and email admin@company.com immediately")
    
    print(f"Intent: {intent.describe()}")
    print(f"CLI: {intent.to_cli_string()}")
    print(f"Args: {intent.to_cli_args()}")
    print()


def demo_to_env():
    """Demonstrate generating environment variables."""
    
    print("=" * 60)
    print("GENERATING ENVIRONMENT VARIABLES")
    print("=" * 60)
    print()
    
    intent = parse_command("describe scene with screenshot")
    env = intent.to_env()
    
    print(f"Intent: {intent.describe()}")
    print("Environment variables:")
    for key, value in env.items():
        print(f"  {key}={value}")
    print()


def demo_shell_usage():
    """Show how to use the interactive shell."""
    
    print("=" * 60)
    print("INTERACTIVE SHELL USAGE")
    print("=" * 60)
    print()
    
    print("""
Start interactive shell:
    $ sq shell

Example session:
    sq> detect person and email me@company.com immediately
    ✅ Start person detection, send email immediately
       Command: sq watch --detect person --email me@company.com --notify-mode instant
       Execute? [Y/n]: y

    sq> track cars for 10 minutes
    ✅ Track car objects for 600 seconds
       Command: sq watch --track car --fps 2 --duration 600

    sq> functions
    (lists all available functions)

    sq> stop
    sq> exit

With auto-execute:
    $ sq shell --auto

List functions:
    $ sq functions
    $ sq functions --json
    $ sq functions --llm
""")


if __name__ == "__main__":
    # Show new LLM-based features first
    demo_llm_parsing()
    demo_function_registry()
    demo_shell_usage()
    
    # Then traditional demos
    demo_heuristic_parsing()
    demo_apply()
    demo_to_cli()
    demo_to_env()
