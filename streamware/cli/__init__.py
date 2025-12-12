"""
Streamware CLI Module

Modular command-line interface with LLM-powered natural language parsing.

Usage:
    from streamware.cli import run_cli, parse_args
    
    args = parse_args()
    run_cli(args)
"""

from .main import main, run_cli
from .parser import create_parser, parse_args
from .handlers import (
    handle_watch,
    handle_live,
    handle_detect,
    handle_config,
    handle_test,
)

__all__ = [
    "main",
    "run_cli",
    "create_parser",
    "parse_args",
    "handle_watch",
    "handle_live",
    "handle_detect",
    "handle_config",
    "handle_test",
]
