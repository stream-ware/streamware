"""
CLI Main Entry Point

Streamware command-line interface main module.
"""

import sys
from typing import List, Optional

from .parser import create_parser, parse_args
from .handlers import (
    handle_watch,
    handle_live,
    handle_detect,
    handle_config,
    handle_test,
    handle_shell,
    handle_functions,
)


def run_cli(args=None) -> int:
    """
    Run the CLI with given arguments.
    
    Args:
        args: Command line arguments (default: sys.argv[1:])
    
    Returns:
        Exit code (0 = success)
    """
    parsed = parse_args(args)
    
    # Route to appropriate handler
    handlers = {
        "watch": handle_watch,
        "live": handle_live,
        "detect": handle_detect,
        "config": handle_config,
        "test": handle_test,
        "shell": handle_shell,
        "functions": handle_functions,
    }
    
    command = parsed.command
    
    if not command:
        # No command specified - show help
        parser = create_parser()
        parser.print_help()
        return 0
    
    handler = handlers.get(command)
    if handler:
        return handler(parsed)
    else:
        print(f"Unknown command: {command}")
        return 1


def main():
    """Main entry point."""
    try:
        sys.exit(run_cli())
    except KeyboardInterrupt:
        print("\n🛑 Interrupted")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
