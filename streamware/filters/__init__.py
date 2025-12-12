"""
Filters Module - Response filtering and text processing.

Refactored from response_filter.py into modular components:
- significance.py: Check if response is significant
- tts.py: Text-to-speech formatting
- detection.py: Quick detection checks
- llm_analysis.py: LLM-based analysis

Usage:
    from streamware.filters import is_significant, format_for_tts, should_notify
"""

from .significance import (
    is_significant,
    is_significant_smart,
    should_notify,
    filter_response,
)

from .tts import (
    format_for_tts,
    clean_for_speech,
)

from .detection import (
    quick_person_check,
    quick_change_check,
    summarize_detection,
    extract_alert_info,
    extract_structured_fields,
)

from .llm_analysis import (
    validate_with_llm,
    is_significant_with_llm,
    summarize_session,
)

__all__ = [
    # Significance
    "is_significant",
    "is_significant_smart", 
    "should_notify",
    "filter_response",
    # TTS
    "format_for_tts",
    "clean_for_speech",
    # Detection
    "quick_person_check",
    "quick_change_check",
    "summarize_detection",
    "extract_alert_info",
    "extract_structured_fields",
    # LLM
    "validate_with_llm",
    "is_significant_with_llm",
    "summarize_session",
]
