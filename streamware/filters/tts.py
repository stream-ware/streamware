"""
TTS Formatting

Text-to-speech formatting and cleaning functions.
Extracted from response_filter.py.
"""

import re
from typing import Optional


def format_for_tts(response: str) -> str:
    """
    Format response for text-to-speech.
    
    - Removes technical details
    - Shortens long descriptions
    - Makes text more natural to speak
    
    Args:
        response: Raw LLM response
    
    Returns:
        TTS-friendly text
    """
    if not response:
        return ""
    
    text = response.strip()
    
    # Extract SUMMARY if present
    match = re.search(r"SUMMARY:\s*(.+?)(?:\n|$)", text, re.IGNORECASE)
    if match:
        text = match.group(1).strip()
    
    # Clean for speech
    text = clean_for_speech(text)
    
    # Limit length for TTS
    if len(text) > 150:
        # Find sentence boundary
        sentences = re.split(r'[.!?]', text)
        result = []
        length = 0
        for s in sentences:
            s = s.strip()
            if not s:
                continue
            if length + len(s) > 150:
                break
            result.append(s)
            length += len(s)
        text = ". ".join(result)
        if text and not text.endswith(('.', '!', '?')):
            text += "."
    
    return text


def clean_for_speech(text: str) -> str:
    """
    Clean text for natural speech.
    
    - Removes technical jargon
    - Expands abbreviations
    - Removes formatting
    """
    if not text:
        return ""
    
    # Remove markdown
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'`+', '', text)
    text = re.sub(r'#+\s*', '', text)
    
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    
    # Remove technical prefixes
    prefixes = [
        r"^VISIBLE:\s*(YES|NO)\s*",
        r"^PRESENT:\s*(YES|NO)\s*",
        r"^ALERT:\s*(YES|NO)\s*",
        r"^SUMMARY:\s*",
        r"^DESCRIPTION:\s*",
    ]
    for p in prefixes:
        text = re.sub(p, '', text, flags=re.IGNORECASE)
    
    # Expand common abbreviations
    abbreviations = {
        r'\bppl\b': 'people',
        r'\bw/\b': 'with',
        r'\bw/o\b': 'without',
        r'\bb/c\b': 'because',
        r'\bFPS\b': 'frames per second',
        r'\bLLM\b': 'AI model',
        r'\bYOLO\b': 'detector',
    }
    for abbr, expansion in abbreviations.items():
        text = re.sub(abbr, expansion, text, flags=re.IGNORECASE)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remove leading conjunctions
    text = re.sub(r'^(and|but|so|then)\s+', '', text, flags=re.IGNORECASE)
    
    return text


def shorten_for_tts(text: str, max_words: int = 20) -> str:
    """Shorten text to max words for TTS."""
    words = text.split()
    if len(words) <= max_words:
        return text
    
    result = ' '.join(words[:max_words])
    if not result.endswith(('.', '!', '?')):
        result += '...'
    return result


def make_natural(text: str) -> str:
    """Make text sound more natural when spoken."""
    if not text:
        return ""
    
    # Capitalize first letter
    text = text[0].upper() + text[1:] if len(text) > 1 else text.upper()
    
    # Add period if missing
    if text and not text.endswith(('.', '!', '?', ':')):
        text += '.'
    
    return text
