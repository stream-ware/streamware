"""
Prompt Management for Streamware LLM Components

Centralizes all LLM prompts in editable text files.
Prompts can be customized by editing files in this directory or
overriding via environment variables.

Usage:
    from streamware.prompts import get_prompt, render_prompt

    # Get raw prompt template
    template = get_prompt("stream_diff")

    # Render prompt with variables
    prompt = render_prompt("stream_diff", focus="person", prev_description="...")
"""

import logging
import os
from pathlib import Path
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

# Directory containing prompt files
PROMPTS_DIR = Path(__file__).parent

# Cache for loaded prompts
_cache: Dict[str, str] = {}


def get_prompt(name: str, default: Optional[str] = None) -> str:
    """Load prompt template by name.

    Looks for:
    1. Environment variable SQ_PROMPT_{NAME} (uppercase)
    2. File prompts/{name}.txt
    3. File prompts/{name}.md
    4. Default value if provided

    Args:
        name: Prompt identifier (e.g., "stream_diff", "trigger_check")
        default: Default template if not found

    Returns:
        Prompt template string
    """
    # Check cache first
    if name in _cache:
        return _cache[name]

    # 1. Check environment variable
    env_key = f"SQ_PROMPT_{name.upper()}"
    env_value = os.environ.get(env_key)
    if env_value:
        _cache[name] = env_value
        return env_value

    # 2. Try .txt file
    txt_path = PROMPTS_DIR / f"{name}.txt"
    if txt_path.exists():
        template = txt_path.read_text(encoding="utf-8").strip()
        _cache[name] = template
        return template

    # 3. Try .md file
    md_path = PROMPTS_DIR / f"{name}.md"
    if md_path.exists():
        template = md_path.read_text(encoding="utf-8").strip()
        _cache[name] = template
        return template

    # 4. Return default or empty
    if default is not None:
        return default

    logger.warning(f"Prompt '{name}' not found in {PROMPTS_DIR}")
    return ""


def render_prompt(name: str, default: Optional[str] = None, **kwargs: Any) -> str:
    """Load and render prompt template with variables.

    Uses Python format strings. Template variables are wrapped in {braces}.

    Args:
        name: Prompt identifier
        default: Default template if not found
        **kwargs: Variables to substitute in template

    Returns:
        Rendered prompt string

    Example:
        render_prompt("stream_diff", focus="person", prev_desc="A person standing")
    """
    template = get_prompt(name, default)
    if not template:
        return ""

    try:
        return template.format(**kwargs)
    except KeyError as e:
        logger.warning(f"Missing variable {e} in prompt '{name}'")
        # Return template with unfilled variables
        return template


def list_prompts() -> Dict[str, str]:
    """List all available prompt files.

    Returns:
        Dict mapping prompt name to file path
    """
    prompts = {}
    for ext in (".txt", ".md"):
        for path in PROMPTS_DIR.glob(f"*{ext}"):
            name = path.stem
            if name not in prompts:  # .txt takes precedence
                prompts[name] = str(path)
    return prompts


def reload_prompts():
    """Clear prompt cache to force reload from files."""
    global _cache
    _cache = {}
