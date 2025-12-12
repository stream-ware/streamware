"""
LLM Analysis

LLM-based response validation and analysis.
Extracted from response_filter.py.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple

from ..config import config

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_ANALYSIS_MODEL = "qwen2.5:3b"


# =============================================================================
# LLM VALIDATION
# =============================================================================

def validate_with_llm(
    response: str,
    focus: str = "person",
    model: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Validate response significance using LLM.
    
    Uses a small LLM to determine if the response is truly significant.
    
    Args:
        response: Response text to validate
        focus: What we're looking for
        model: LLM model to use
    
    Returns:
        Tuple of (is_significant, reason)
    """
    if not response:
        return False, "Empty response"
    
    model = model or config.get("SQ_ANALYSIS_MODEL", DEFAULT_ANALYSIS_MODEL)
    ollama_url = config.get("SQ_OLLAMA_URL", DEFAULT_OLLAMA_URL)
    
    prompt = f"""Analyze this detection response and determine if it's significant.

Response: "{response[:500]}"
Looking for: {focus}

Answer with:
SIGNIFICANT: YES or NO
REASON: brief explanation

Only answer YES if the response clearly indicates the target was detected or something important happened."""

    try:
        import requests
        
        result = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
            },
            timeout=10
        )
        
        if result.ok:
            llm_response = result.json().get("response", "")
            
            # Parse response
            sig_match = re.search(r"SIGNIFICANT:\s*(YES|NO)", llm_response, re.IGNORECASE)
            reason_match = re.search(r"REASON:\s*(.+?)(?:\n|$)", llm_response, re.IGNORECASE)
            
            is_sig = sig_match and sig_match.group(1).upper() == "YES"
            reason = reason_match.group(1).strip() if reason_match else ""
            
            return is_sig, reason
            
    except Exception as e:
        logger.debug(f"LLM validation failed: {e}")
    
    # Fallback to simple check
    return focus.lower() in response.lower(), "Fallback check"


def is_significant_with_llm(
    response: str,
    focus: str = "person",
    confidence_threshold: float = 0.5,
) -> Tuple[bool, str, float]:
    """
    Check significance with LLM and return confidence.
    
    Returns:
        Tuple of (is_significant, summary, confidence)
    """
    is_sig, reason = validate_with_llm(response, focus)
    
    # Estimate confidence based on reason
    confidence = 0.8 if is_sig else 0.2
    
    if "clearly" in reason.lower() or "definitely" in reason.lower():
        confidence = 0.95
    elif "might" in reason.lower() or "possibly" in reason.lower():
        confidence = 0.6
    
    summary = reason if is_sig else ""
    
    return is_sig, summary, confidence


# =============================================================================
# SESSION SUMMARY
# =============================================================================

def summarize_session(
    responses: List[str],
    mode: str = "general",
    max_items: int = 10,
) -> str:
    """
    Create summary of multiple responses from a session.
    
    Args:
        responses: List of response texts
        mode: Detection mode
        max_items: Maximum items to include
    
    Returns:
        Session summary text
    """
    if not responses:
        return "No events recorded"
    
    # Filter significant responses
    from .significance import is_significant
    
    significant = [r for r in responses if is_significant(r, mode)]
    
    if not significant:
        return f"Session ended. {len(responses)} frames analyzed, no significant events."
    
    # Group similar responses
    unique_events = []
    seen = set()
    
    for resp in significant:
        # Normalize for comparison
        normalized = resp.lower().strip()[:50]
        if normalized not in seen:
            seen.add(normalized)
            unique_events.append(resp)
            if len(unique_events) >= max_items:
                break
    
    # Build summary
    summary_parts = [
        f"Session summary ({len(significant)} events):",
    ]
    
    for i, event in enumerate(unique_events, 1):
        # Shorten event
        short = event[:80] + "..." if len(event) > 80 else event
        summary_parts.append(f"  {i}. {short}")
    
    if len(significant) > len(unique_events):
        summary_parts.append(f"  ... and {len(significant) - len(unique_events)} more events")
    
    return "\n".join(summary_parts)


def analyze_with_tracking(
    response: str,
    tracking_data: Dict,
    focus: str = "person",
) -> Tuple[bool, str]:
    """
    Analyze response with tracking context.
    
    Args:
        response: LLM response
        tracking_data: Object tracking data
        focus: Focus target
    
    Returns:
        Tuple of (is_significant, analysis)
    """
    # Check if tracking shows target
    tracked_objects = tracking_data.get("objects", [])
    focus_objects = [
        obj for obj in tracked_objects
        if obj.get("class", "").lower() == focus.lower()
    ]
    
    if not focus_objects:
        return False, "Target not tracked"
    
    # Build context
    obj = focus_objects[0]
    track_id = obj.get("track_id", "unknown")
    frames_seen = obj.get("frames_seen", 0)
    
    if frames_seen < 3:
        return True, f"New {focus} detected (ID: {track_id})"
    else:
        return True, f"{focus.title()} tracked (ID: {track_id}, {frames_seen} frames)"
