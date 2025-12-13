"""
Camera Utilities Module

Functions for camera detection, configuration and management.
"""

import socket
from typing import Dict, List, Any, Optional
from pathlib import Path

from .scanner_config import get_combined_config


def load_env_config() -> Dict[str, Any]:
    """Load all configuration from .env file. Uses scanner_config module."""
    return get_combined_config()


def load_camera_config_from_env() -> Dict[str, Any]:
    """Load camera configuration from .env file (backward compatibility)."""
    return get_combined_config()


def list_available_cameras(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """List all available cameras from config."""
    cameras = []
    
    # Add cameras from SQ_CAMERAS
    for name, url in config.get("cameras_list", []):
        cameras.append({
            "name": name,
            "url": url,
            "source": "SQ_CAMERAS",
        })
    
    # Add default URL if not already in list
    default_url = config.get("default_url")
    if default_url:
        urls_in_list = [c["url"] for c in cameras]
        if default_url not in urls_in_list:
            cameras.insert(0, {
                "name": "default",
                "url": default_url,
                "source": "SQ_DEFAULT_URL",
            })
    
    return cameras


def find_free_port(start_port: int = 8088, max_attempts: int = 10) -> int:
    """Find a free port starting from start_port."""
    for i in range(max_attempts):
        port = start_port + i
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('0.0.0.0', port))
                return port
        except OSError:
            continue
    return start_port + max_attempts


def mask_rtsp_url(url: str) -> str:
    """Mask password in RTSP URL for display."""
    if not url:
        return ""
    import re
    return re.sub(r'://([^:]+):([^@]+)@', r'://\1:****@', url)
