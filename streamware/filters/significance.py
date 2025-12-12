"""
Significance Filters

Check if responses contain meaningful/significant information.
Extracted from response_filter.py.
"""

import re
import logging
from typing import Optional, Tuple, Dict, List

logger = logging.getLogger(__name__)


# =============================================================================
# PATTERNS
# =============================================================================

# Patterns indicating no significant change
NOISE_PATTERNS = [
    # English
    r"no\s+significant\s+(changes?|motion|movement|activity)",
    r"no\s+(person|people|object|vehicle|animal)\s*(visible|detected|found|present)?",
    r"nothing\s+(to\s+report|detected|visible|happening|changed)",
    r"no\s+movement\s+detected",
    r"no\s+changes?\s+(detected|observed|noted|visible)",
    r"target\s+not\s+visible",
    r"scene\s+(unchanged|static|same)",
    r"^no$",
    r"^none$",
    r"^-+$",
    # Structured responses
    r"VISIBLE:\s*NO",
    r"PRESENT:\s*NO",
    r"CHANGED:\s*NO",
    r"MATCH:\s*NO",
    r"ALERT:\s*NO",
    r"OBJECT:\s*none",
    r"COUNT:\s*0",
    # Polish
    r"brak\s+(zmian|ruchu|osób)",
    r"nic\s+(się\s+nie\s+)?zmieniło",
]

# Patterns indicating significant change
SIGNIFICANT_PATTERNS = [
    r"VISIBLE:\s*YES",
    r"PRESENT:\s*YES",
    r"CHANGED:\s*YES",
    r"MATCH:\s*YES",
    r"ALERT:\s*YES",
    r"(?<!no\s)person\s+(detected|visible|appeared|entered)",
    r"(?<!no\s)movement\s+(detected|observed)",
    r"new\s+(object|person|vehicle)",
    r"COUNT:\s*[1-9]",
]

# Compiled patterns for performance
_NOISE_COMPILED = [re.compile(p, re.IGNORECASE) for p in NOISE_PATTERNS]
_SIGNIFICANT_COMPILED = [re.compile(p, re.IGNORECASE) for p in SIGNIFICANT_PATTERNS]


# =============================================================================
# CORE FUNCTIONS
# =============================================================================

def is_significant(response: str, mode: str = "general") -> bool:
    """
    Check if LLM response contains meaningful information.
    
    Args:
        response: LLM response text
        mode: Detection mode (general, security, tracking, etc.)
    
    Returns:
        True if response contains significant information
    """
    if not response or not response.strip():
        return False
    
    text = response.strip().lower()
    
    # Check for explicit significant patterns first
    for pattern in _SIGNIFICANT_COMPILED:
        if pattern.search(response):
            return True
    
    # Check for noise patterns
    for pattern in _NOISE_COMPILED:
        if pattern.search(text):
            return False
    
    # Short responses are usually not significant
    if len(text) < 10:
        return False
    
    # Default: if it's not noise and has content, it's likely significant
    return True


def is_significant_smart(
    response: str,
    focus: str = "person",
    mode: str = "track",
    tracking_data: Optional[Dict] = None,
    confidence_threshold: float = 0.5,
) -> Tuple[bool, str]:
    """
    Smart significance check with optional LLM validation.
    
    Returns:
        Tuple of (is_significant, summary_text)
    """
    if not response or not response.strip():
        return False, ""
    
    # Quick pattern check first
    if not is_significant(response, mode):
        return False, ""
    
    # Extract short summary
    summary = _extract_summary(response)
    
    # Check if focus target is mentioned
    if focus and focus.lower() not in response.lower():
        # Target not mentioned - might still be significant for other reasons
        pass
    
    return True, summary


def should_notify(response: str, mode: str = "general") -> bool:
    """
    Check if response warrants a notification (TTS, email, etc.).
    
    More strict than is_significant - only notify for important events.
    """
    if not is_significant(response, mode):
        return False
    
    text = response.lower()
    
    # Check for notification-worthy patterns
    notify_patterns = [
        r"person\s+(detected|entered|appeared|visible)",
        r"alert",
        r"warning",
        r"movement\s+detected",
        r"new\s+object",
        r"intruder",
        r"unauthorized",
    ]
    
    for pattern in notify_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    
    # Mode-specific checks
    if mode == "security":
        return True  # Security mode: notify on any significant event
    
    return False


def filter_response(response: str, mode: str = "general") -> Optional[str]:
    """
    Filter response and return cleaned version if significant.
    
    Returns:
        Cleaned response if significant, None otherwise
    """
    if not is_significant(response, mode):
        return None
    
    # Clean up response
    text = response.strip()
    
    # Remove common prefixes
    prefixes_to_remove = [
        "Based on the image,",
        "Looking at the image,",
        "I can see that",
        "The image shows",
    ]
    
    for prefix in prefixes_to_remove:
        if text.lower().startswith(prefix.lower()):
            text = text[len(prefix):].strip()
    
    return text


# =============================================================================
# HELPERS
# =============================================================================

def _extract_summary(response: str, max_length: int = 80) -> str:
    """Extract a short summary from response."""
    # Check for SUMMARY: prefix
    match = re.search(r"SUMMARY:\s*(.+?)(?:\n|$)", response, re.IGNORECASE)
    if match:
        return match.group(1).strip()[:max_length]
    
    # Take first sentence
    sentences = re.split(r'[.!?]', response)
    if sentences:
        first = sentences[0].strip()
        if len(first) <= max_length:
            return first
        return first[:max_length-3] + "..."
    
    return response[:max_length]
