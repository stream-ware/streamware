"""
CLI Argument Parser

Defines all CLI arguments and subcommands.
"""

import argparse
from typing import List, Optional

from ..config import config


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser."""
    parser = argparse.ArgumentParser(
        prog="sq",
        description="Streamware - AI-powered video stream analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sq watch "detect person and email me@example.com immediately"
  sq watch --url rtsp://... --detect person --tts
  sq live --url rtsp://... --mode hybrid
  sq config --show
  sq test camera
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Watch command (main command with natural language support)
    _add_watch_parser(subparsers)
    
    # Live command
    _add_live_parser(subparsers)
    
    # Detect command
    _add_detect_parser(subparsers)
    
    # Config command
    _add_config_parser(subparsers)
    
    # Test command
    _add_test_parser(subparsers)
    
    # Version
    parser.add_argument("--version", action="version", version="%(prog)s 1.0.0")
    
    return parser


def _add_watch_parser(subparsers):
    """Add watch subcommand parser."""
    watch = subparsers.add_parser(
        "watch",
        help="Watch video stream with natural language commands",
        description="Monitor video stream using natural language or explicit options"
    )
    
    # Natural language intent (positional, optional)
    watch.add_argument(
        "intent",
        nargs="?",
        help="Natural language command (e.g., 'detect person and email me@x.com')"
    )
    
    # Source
    watch.add_argument("--url", "-u", help="Video source URL (RTSP, file, webcam)")
    watch.add_argument("--source", "-s", help="Alias for --url")
    
    # Detection
    watch.add_argument("--detect", "-d", help="What to detect (person, car, motion, etc.)")
    watch.add_argument("--mode", "-m", choices=["yolo", "llm", "hybrid"], default="hybrid",
                       help="Detection mode")
    watch.add_argument("--confidence", "-c", type=float, default=0.5,
                       help="Detection confidence threshold (0-1)")
    watch.add_argument("--fps", type=float, default=2.0,
                       help="Processing frames per second")
    
    # Notifications
    watch.add_argument("--email", "-e", help="Email address for notifications")
    watch.add_argument("--slack", help="Slack channel for notifications")
    watch.add_argument("--telegram", help="Telegram chat ID for notifications")
    watch.add_argument("--webhook", help="Webhook URL for notifications")
    watch.add_argument("--notify-mode", choices=["instant", "digest", "summary"],
                       default="digest", help="Notification frequency")
    watch.add_argument("--notify-interval", type=int, default=60,
                       help="Digest interval in seconds")
    
    # Output
    watch.add_argument("--screenshot", action="store_true", help="Save detection screenshots")
    watch.add_argument("--record", action="store_true", help="Record video")
    watch.add_argument("--tts", action="store_true", help="Enable text-to-speech")
    watch.add_argument("--quiet", "-q", action="store_true", help="Minimal output")
    watch.add_argument("--output", "-o", help="Output directory")
    
    # Duration
    watch.add_argument("--duration", "-t", type=int, default=60,
                       help="Duration in seconds (0 = infinite)")
    
    # Advanced
    watch.add_argument("--use-llm", action="store_true",
                       help="Use LLM for intent parsing (default: auto)")
    watch.add_argument("--llm-model", help="Specific LLM model to use")
    watch.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    watch.add_argument("--log-file", help="Log file path")


def _add_live_parser(subparsers):
    """Add live subcommand parser."""
    live = subparsers.add_parser(
        "live",
        help="Real-time video narration",
        description="Live video stream analysis with TTS narration"
    )
    
    live.add_argument("--url", "-u", required=True, help="Video source URL")
    live.add_argument("--mode", "-m", choices=["yolo", "llm", "hybrid"], default="hybrid")
    live.add_argument("--focus", "-f", help="Focus object (person, car, etc.)")
    live.add_argument("--tts", action="store_true", help="Enable TTS")
    live.add_argument("--duration", "-t", type=int, default=60)
    live.add_argument("--fps", type=float, default=2.0)
    live.add_argument("--quiet", "-q", action="store_true")
    live.add_argument("--verbose", "-v", action="store_true")


def _add_detect_parser(subparsers):
    """Add detect subcommand parser."""
    detect = subparsers.add_parser(
        "detect",
        help="Single-frame detection",
        description="Analyze a single frame or image"
    )
    
    detect.add_argument("source", help="Image file or video URL")
    detect.add_argument("--target", "-t", default="all", help="What to detect")
    detect.add_argument("--mode", "-m", choices=["yolo", "llm", "hybrid"], default="hybrid")
    detect.add_argument("--output", "-o", help="Output file")
    detect.add_argument("--format", "-f", choices=["json", "yaml", "text"], default="json")


def _add_config_parser(subparsers):
    """Add config subcommand parser."""
    cfg = subparsers.add_parser(
        "config",
        help="Configuration management",
        description="View and modify Streamware configuration"
    )
    
    cfg.add_argument("--show", action="store_true", help="Show current config")
    cfg.add_argument("--set", nargs=2, metavar=("KEY", "VALUE"), help="Set config value")
    cfg.add_argument("--get", metavar="KEY", help="Get config value")
    cfg.add_argument("--reset", action="store_true", help="Reset to defaults")
    cfg.add_argument("--diagnose", action="store_true", help="Run diagnostics")


def _add_test_parser(subparsers):
    """Add test subcommand parser."""
    test = subparsers.add_parser(
        "test",
        help="Test components",
        description="Test various Streamware components"
    )
    
    test.add_argument("component", choices=["camera", "email", "tts", "yolo", "llm", "all"],
                      help="Component to test")
    test.add_argument("--url", "-u", help="URL for camera test")
    test.add_argument("--to", help="Email address for email test")


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = create_parser()
    return parser.parse_args(args)


def get_default_url() -> Optional[str]:
    """Get default video URL from config."""
    return config.get("SQ_DEFAULT_URL") or None
