"""
Response Filter for Streamware

Filters LLM responses to reduce noise and only keep significant events.
Prevents logging/speaking "nothing happened" messages.

Usage:
    from streamware.response_filter import is_significant, filter_response

    response = llm_client.analyze_image(...)
    if is_significant(response):
        log(response)
        speak(response)
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

__all__ = [
    "is_significant",
    "filter_response",
    "extract_alert_info",
    "should_notify",
    "format_for_tts",
    "is_significant_smart",
    "summarize_detection",
    "check_guarder_model_available",
]


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
    # Structured responses (from our prompts)
    r"VISIBLE:\s*NO",
    r"PRESENT:\s*NO",
    r"CHANGED:\s*NO",
    r"MATCH:\s*NO",
    r"ALERT:\s*NO",
    r"OBJECT:\s*none",
    r"COUNT:\s*0",
    # Polish (if used)
    r"brak\s+(zmian|ruchu|osób)",
    r"nic\s+(się\s+nie\s+)?zmieniło",
]

# Patterns indicating significant change (must NOT be preceded by "no")
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


def is_significant(response: str, mode: str = "general") -> bool:
    """Check if LLM response contains meaningful information.
    
    Args:
        response: LLM response text
        mode: Analysis mode (general, track, diff, trigger)
        
    Returns:
        True if response indicates something worth reporting
    """
    if not response or not response.strip():
        return False
    
    response_lower = response.lower().strip()
    
    # Very short responses are usually noise
    if len(response_lower) < 5:
        return False
    
    # Check for noise patterns FIRST (strict matching)
    for pattern in NOISE_PATTERNS:
        if re.search(pattern, response_lower, re.IGNORECASE):
            return False
    
    # Check for significant patterns (explicit detection)
    for pattern in SIGNIFICANT_PATTERNS:
        if re.search(pattern, response, re.IGNORECASE):
            return True
    
    # Default: consider significant if response has substance
    # (not matched as noise, so probably contains useful info)
    word_count = len(response_lower.split())
    return word_count >= 2


def filter_response(response: str, mode: str = "general") -> Optional[str]:
    """Return response only if significant, else None.
    
    Args:
        response: LLM response text
        mode: Analysis mode
        
    Returns:
        Response text if significant, None otherwise
    """
    if is_significant(response, mode):
        return response.strip()
    return None


def extract_alert_info(response: str) -> Tuple[bool, str]:
    """Extract alert status and reason from structured response.
    
    Args:
        response: LLM response in structured format
        
    Returns:
        (is_alert, reason) tuple
    """
    is_alert = False
    reason = ""
    
    # Check for ALERT: YES pattern
    alert_match = re.search(r"ALERT:\s*(YES|NO)", response, re.IGNORECASE)
    if alert_match:
        is_alert = alert_match.group(1).upper() == "YES"
    
    # Extract reason if alert
    if is_alert:
        reason_match = re.search(r"REASON:\s*(.+?)(?:\n|$)", response, re.IGNORECASE)
        if reason_match:
            reason = reason_match.group(1).strip()
            if reason == "-":
                reason = ""
    
    return is_alert, reason


def extract_structured_fields(response: str) -> dict:
    """Parse structured response into dict.
    
    Expected format:
        PRESENT: YES
        LOCATION: center
        STATE: standing
        ...
    
    Returns:
        Dict with parsed fields
    """
    fields = {}
    
    patterns = [
        ("present", r"PRESENT:\s*(YES|NO)"),
        ("visible", r"VISIBLE:\s*(YES|NO)"),
        ("changed", r"CHANGED:\s*(YES|NO)"),
        ("alert", r"ALERT:\s*(YES|NO)"),
        ("match", r"MATCH:\s*(YES|NO)"),
        ("count", r"COUNT:\s*(\d+)"),
        ("location", r"LOCATION:\s*(.+?)(?:\n|$)"),
        ("state", r"STATE:\s*(.+?)(?:\n|$)"),
        ("action", r"ACTION:\s*(.+?)(?:\n|$)"),
        ("movement", r"MOVEMENT:\s*(.+?)(?:\n|$)"),
        ("object", r"OBJECT:\s*(.+?)(?:\n|$)"),
        ("subject", r"SUBJECT:\s*(.+?)(?:\n|$)"),
        ("reason", r"REASON:\s*(.+?)(?:\n|$)"),
        ("confidence", r"CONFIDENCE:\s*(HIGH|MEDIUM|LOW)"),
        ("what", r"WHAT:\s*(.+?)(?:\n|$)"),
        ("where", r"WHERE:\s*(.+?)(?:\n|$)"),
    ]
    
    for name, pattern in patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if value and value != "-":
                fields[name] = value
    
    return fields


def should_notify(response: str, mode: str = "general") -> bool:
    """Determine if response warrants notification (TTS, webhook).
    
    More strict than is_significant - only for alerts.
    
    Args:
        response: LLM response
        mode: Analysis mode
        
    Returns:
        True if should trigger notification
    """
    if not response:
        return False
    
    response_lower = response.lower()
    
    # Skip noise patterns - don't notify for these
    noise_patterns = [
        "no person", "no change", "nothing", "unclear", 
        "not visible", "empty", "no movement", "no_change",
        "no clear person", "no human", "no individual"
    ]
    if any(p in response_lower for p in noise_patterns):
        return False
    
    # In track mode, notify for ANY person-related activity
    # We want to be informed about movements and presence
    if mode == "track":
        # Activity keywords that always warrant notification
        activity_keywords = [
            "walking", "moving", "standing", "running", "entering", "leaving",
            "approaching", "sitting", "working", "looking", "reaching",
            "holding", "carrying", "talking", "using", "typing", "reading"
        ]
        if any(kw in response_lower for kw in activity_keywords):
            return True
        
        # Person-related words - notify if detected
        person_keywords = ["person", "man", "woman", "someone", "human", "people",
                          "individual", "figure", "they", "he", "she"]
        for kw in person_keywords:
            if kw in response_lower:
                # Make sure it's not negated
                negations = ["no ", "not ", "without ", "lack of ", "no_"]
                is_negated = any(neg + kw in response_lower for neg in negations)
                if not is_negated:
                    return True
    
    # Check structured fields
    fields = extract_structured_fields(response)
    
    # Explicit alert
    if fields.get("alert", "").upper() == "YES":
        return True
    
    # Person/object detected in track mode
    if mode == "track":
        if fields.get("present", "").upper() == "YES":
            return True
        if fields.get("visible", "").upper() == "YES":
            return True
    
    # Change detected in diff mode
    if mode == "diff":
        if fields.get("changed", "").upper() == "YES":
            return True
    
    # Trigger match
    if fields.get("match", "").upper() == "YES":
        return True
    
    return False


def format_for_tts(response: str) -> str:
    """Format response for text-to-speech (shorter, cleaner).
    
    Args:
        response: LLM response
        
    Returns:
        Cleaned text suitable for TTS
    """
    fields = extract_structured_fields(response)
    
    # Build TTS-friendly message
    parts = []
    
    if fields.get("object") and fields.get("object") != "none":
        parts.append(fields["object"])
    
    if fields.get("location") and fields.get("location") != "-":
        parts.append(f"at {fields['location']}")
    
    if fields.get("state") and fields.get("state") != "-":
        parts.append(fields["state"])
    
    if fields.get("action") and fields.get("action") != "-":
        parts.append(fields["action"])
    
    if fields.get("reason") and fields.get("reason") != "-":
        parts.append(f"Alert: {fields['reason']}")
    
    if parts:
        return ". ".join(parts)
    
    # Fallback: clean the raw response
    text = response.replace("\n", ". ").strip()
    text = re.sub(r"[A-Z]+:\s*", "", text)  # Remove field labels
    text = re.sub(r"\s+", " ", text)
    return text[:200]


def check_guarder_model_available(model: str = "qwen2.5:3b") -> Tuple[bool, str]:
    """Check if guarder model is available in Ollama.
    
    Returns:
        (available, actual_model_name) tuple
    """
    import requests
    from .config import config
    
    ollama_url = config.get("SQ_OLLAMA_URL", "http://localhost:11434")
    
    try:
        resp = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if resp.ok:
            models = [m.get("name", "") for m in resp.json().get("models", [])]
            
            # Check exact match first
            if model in models:
                return True, model
            if f"{model}:latest" in models:
                return True, f"{model}:latest"
            
            # Check base name match
            base_name = model.split(":")[0]
            for m in models:
                if m.startswith(base_name):
                    return True, m
            
            # Check for alternative small models (fallback)
            small_models = ["gemma:2b", "phi3:mini", "llama3.2:latest", "deepseek-r1:1.5b"]
            for sm in small_models:
                if sm in models:
                    return True, sm
                # Check base name
                sm_base = sm.split(":")[0]
                for m in models:
                    if m.startswith(sm_base):
                        return True, m
            
            return False, f"Model {model} not found. Install with: ollama pull {model}"
        else:
            return False, "Cannot connect to Ollama"
    except Exception as e:
        return False, f"Ollama not available: {e}"


def ensure_guarder_model(model: str = "qwen2.5:3b", interactive: bool = True) -> bool:
    """Ensure guarder model is available, offer to install if not.
    
    Args:
        model: Model name
        interactive: If True, prompt user to install
        
    Returns:
        True if model is available
    """
    import subprocess
    
    available, message = check_guarder_model_available(model)
    
    if available:
        return True
    
    print(f"\n⚠️  {message}")
    
    if not interactive:
        return False
    
    # Offer installation
    print(f"\n   Guarder model '{model}' is needed for smart response filtering.")
    print("   Recommended models (small, fast):")
    print("   1. qwen2.5:3b  - Best quality (2GB)")
    print("   2. gemma:2b   - Fastest (1.6GB)")
    print("   3. phi3:mini   - Good balance (2.3GB)")
    print("   4. Skip        - Use regex filtering only")
    
    try:
        choice = input("\n   Install model? [1-4, default=1]: ").strip() or "1"
        
        models_map = {
            "1": "qwen2.5:3b",
            "2": "gemma:2b",
            "3": "phi3:mini",
        }
        
        if choice in models_map:
            selected = models_map[choice]
            print(f"\n   Pulling {selected}... (this may take a few minutes)")
            result = subprocess.run(
                ["ollama", "pull", selected],
                capture_output=False,
            )
            if result.returncode == 0:
                print(f"   ✅ {selected} installed successfully")
                # Update config
                from .config import config
                config.set("SQ_GUARDER_MODEL", selected)
                return True
            else:
                print(f"   ❌ Failed to install {selected}")
                return False
        else:
            print("   Skipping guarder model installation.")
            return False
            
    except (EOFError, KeyboardInterrupt):
        print("\n   Skipping.")
        return False


_last_summary: str = ""  # Track last summary for deduplication


def quick_person_check(
    image_path,
    focus: str = "person",
    model: str = "gemma:2b",
    timeout: int = 10,
) -> Tuple[bool, float]:
    """Quick check if person/object is in frame using small LLM.
    
    Much faster than full description - just YES/NO answer.
    Use this BEFORE calling expensive vision LLM.
    
    Args:
        image_path: Path to image
        focus: What to look for
        model: Small LLM model
        timeout: Request timeout
        
    Returns:
        (has_person, confidence) tuple
    """
    import requests
    from .config import config
    from .image_optimize import prepare_image_for_llm_base64
    
    ollama_url = config.get("SQ_OLLAMA_URL", "http://localhost:11434")
    
    # Prepare small image for speed
    try:
        image_data = prepare_image_for_llm_base64(image_path, preset="fast")
    except Exception:
        return True, 0.5  # Assume yes if can't load
    
    prompt = f"""Look at this image. Is there a {focus} visible?
Answer ONLY with: YES or NO"""

    try:
        resp = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "images": [image_data],
                "stream": False,
            },
            timeout=timeout,
        )
        
        if resp.ok:
            answer = resp.json().get("response", "").strip().upper()
            if "YES" in answer:
                return True, 0.9
            elif "NO" in answer:
                return False, 0.9
            else:
                return True, 0.5  # Unclear, assume yes
        
        return True, 0.5
        
    except Exception:
        return True, 0.5  # On error, assume yes (don't skip)


def quick_change_check(
    current_summary: str,
    previous_summary: str,
    model: str = "gemma:2b",
    timeout: int = 8,
) -> Tuple[bool, str]:
    """Quick check if there's a meaningful change between two states.
    
    Faster than full summarization - just compares two short texts.
    
    Args:
        current_summary: Current state description
        previous_summary: Previous state description
        model: Small LLM model
        timeout: Request timeout
        
    Returns:
        (has_change, reason) tuple
    """
    import requests
    from .config import config
    
    if not previous_summary:
        return True, "first_detection"
    
    ollama_url = config.get("SQ_OLLAMA_URL", "http://localhost:11434")
    
    prompt = f"""Compare these two camera observations:
BEFORE: "{previous_summary}"
NOW: "{current_summary}"

Is there a MEANINGFUL change? (person appeared/left, moved, different action)
Answer ONLY: YES or NO"""

    try:
        resp = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
            },
            timeout=timeout,
        )
        
        if resp.ok:
            answer = resp.json().get("response", "").strip().upper()
            if "YES" in answer:
                return True, "change_detected"
            elif "NO" in answer:
                return False, "no_change"
        
        return True, "unclear"
        
    except Exception:
        return True, "error"


def summarize_detection(
    response: str,
    focus: str = "person",
    model: str = "qwen2.5:3b",
    timeout: int = 15,
    prev_summary: str = None,
) -> Tuple[bool, str]:
    """Use small LLM to summarize detection into one short sentence.
    
    Converts verbose LLM output into simple status like:
    - "Person sitting at desk, using computer"
    - "Person walking left toward door"
    - "No person visible"
    
    Also compares with previous summary to avoid duplicate reports.
    
    Args:
        response: Verbose LLM response
        focus: What we're tracking (person, vehicle, etc.)
        model: Small LLM model name
        timeout: Request timeout
        prev_summary: Previous summary to compare against
        
    Returns:
        (should_report, short_summary) tuple
    """
    global _last_summary
    import requests
    from .config import config
    
    ollama_url = config.get("SQ_OLLAMA_URL", "http://localhost:11434")
    
    # Use module-level last summary if not provided
    if prev_summary is None:
        prev_summary = _last_summary
    
    # Build prompt with previous context for comparison
    prev_context = ""
    compare_mode = False
    if prev_summary:
        compare_mode = True
        prev_context = f"""
PREVIOUS STATE: "{prev_summary}"

IMPORTANT: Compare current detection with previous state.
- If the MEANING is the same (same person, same location, same activity) → respond "NO_CHANGE"
- Only report if there's a REAL change: person appeared/left, moved to different location, started different activity
- Minor wording differences are NOT changes. "Person at desk" and "Seated person at computer" = NO_CHANGE
"""
    
    # Different prompts for first detection vs comparison
    if compare_mode:
        prompt = f"""Compare these two camera states and decide if there's a meaningful change.

PREVIOUS: "{prev_summary}"
CURRENT: "{response}"

If the situation is essentially the SAME (same person, same place, same activity):
→ Respond exactly: NO_CHANGE

If something CHANGED (person appeared/left, moved, different action):
→ Respond with short summary: "Person: [what changed]"

Examples:
- "Person at desk" vs "Seated person at computer" → NO_CHANGE
- "Person at desk" vs "Person walking to door" → Person: walking to door
- "No person" vs "Person detected" → Person: appeared

Respond with ONLY "NO_CHANGE" or a short summary:"""
    else:
        # Simpler prompt for small models
        prompt = f"""Summarize in max 8 words. Focus: {focus}.

Input: {response[:200]}

Output format: "{focus.title()}: [what they're doing]" or "No {focus} visible"

Output:"""

    try:
        resp = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
            },
            timeout=timeout,
        )
        
        if resp.ok:
            summary = resp.json().get("response", "").strip()
            
            # Strip common LLM preambles (case-insensitive)
            preambles = [
                "sure, here is the summary:",
                "sure, here's the summary:",
                "sure, heres the summary:",
                "sure, here is a summary:",
                "sure, here's a summary:",
                "sure, heres a summary:",
                "sure! here is",
                "sure! here's",
                "here is the summary:",
                "here's the summary:",
                "heres the summary:",
                "here is a short summary:",
                "here's a short summary:",
                "summary:",
                "the summary is:",
                "the current state is",
                "based on the",
                "i can see",
                "in this image",
            ]
            summary_lower = summary.lower()
            for preamble in preambles:
                if summary_lower.startswith(preamble):
                    summary = summary[len(preamble):].strip()
                    break
            
            # Also strip "sure" patterns via regex - catch all variants
            import re
            # Strip "Sure. Here's..." "Sure, here is..." etc.
            summary = re.sub(r'^sure[,!.\s]+(here\'?s?|heres|the)[\s\S]*?[:]\s*', '', summary, flags=re.IGNORECASE).strip()
            summary = re.sub(r'^sure[,!.\s]+', '', summary, flags=re.IGNORECASE).strip()
            # Strip "Here is/Here's..."
            summary = re.sub(r'^here\'?s?\s+(is\s+)?(a\s+)?(the\s+)?(summary|description)[:\s]*', '', summary, flags=re.IGNORECASE).strip()
            # Strip "The current state is..."
            summary = re.sub(r'^the\s+(current\s+)?(state|situation)\s+(is|shows)[:\s]*', '', summary, flags=re.IGNORECASE).strip()
            # Strip "Based on..."
            summary = re.sub(r'^based\s+on[\s\S]*?[,:]', '', summary, flags=re.IGNORECASE).strip()
            # Strip if it's just "you requested:" or similar
            summary = re.sub(r'^(the\s+)?summary\s+(you\s+)?requested[:\s]*', '', summary, flags=re.IGNORECASE).strip()
            
            # Strip template patterns that shouldn't be in output
            if '[' in summary and ']' in summary:
                # Looks like template: [Activity] [position]
                if any(t in summary.lower() for t in ['[activity]', '[position', '[direction', '[action]']):
                    summary = ""  # Invalid template response
            
            # If summary is empty or just punctuation, it was garbage
            if not summary or summary in ['.', ':', '-', '...']:
                summary = ""
            
            # If focus is person but response doesn't mention person, use original response
            # Don't add fake "Person:" prefix to non-person responses
            if focus.lower() in ("person", "people", "human"):
                person_words = ["person", "man", "woman", "someone", "human", "people", 
                               "individual", "figure", "he", "she", "they"]
                has_person_word = any(w in summary.lower() for w in person_words)
                has_person_word_orig = any(w in response.lower() for w in person_words)
                
                if not has_person_word and not has_person_word_orig:
                    # Model didn't see a person - return original truncated response
                    # Don't fake "Person:" prefix
                    summary = response[:60].strip() if response else ""
            
            # Clean up the response
            summary = summary.replace('"', '').replace("'", "")
            # Remove markdown formatting
            summary = re.sub(r'\*\*([^*]+)\*\*', r'\1', summary)  # **bold** -> bold
            summary = re.sub(r'\*([^*]+)\*', r'\1', summary)      # *italic* -> italic
            summary = re.sub(r'^#+\s*', '', summary)              # # headers
            # Take only first line if multiple
            summary = summary.split('\n')[0].strip()
            # Limit length
            if len(summary) > 80:
                summary = summary[:77] + "..."
            
            # Check if NO_CHANGE (only valid if we had a previous summary)
            if compare_mode and ("no_change" in summary.lower() or "no change" in summary.lower()):
                # Double-check: if previous had person and current says no person, that's a change!
                prev_had_person = focus.lower() in prev_summary.lower() and "no " + focus.lower() not in prev_summary.lower()
                curr_no_person = any(p in response.lower() for p in ["no person", "no clear person", "not visible", "no " + focus.lower()])
                curr_has_person = focus.lower() in response.lower() and not curr_no_person
                prev_no_person = "no " + focus.lower() in prev_summary.lower() or "no person" in prev_summary.lower()
                
                # Person appeared or left - that's always a change
                if (prev_had_person and curr_no_person) or (prev_no_person and curr_has_person):
                    # Force a new summary
                    if curr_no_person:
                        summary = f"No {focus} visible"
                        _last_summary = summary
                        return True, summary
                    else:
                        summary = f"{focus.title()}: appeared"
                        _last_summary = summary
                        return True, summary
                
                # Check for activity keywords that should NOT be filtered as "no change"
                activity_keywords = ["walking", "moving", "standing", "running", "entering", "leaving", 
                                     "approaching", "exiting", "got up", "sat down", "turned", "reached"]
                if any(kw in response.lower() for kw in activity_keywords):
                    # Activity detected in response - don't mark as no change
                    # Re-summarize focusing on the activity
                    for kw in activity_keywords:
                        if kw in response.lower():
                            summary = f"{focus.title()}: {kw}"
                            _last_summary = summary
                            return True, summary
                
                return False, _last_summary or "No change"
            
            # Determine if significant
            summary_lower = summary.lower()
            
            # Activity keywords - always significant
            activity_keywords = ["walking", "moving", "standing", "running", "entering", "leaving", 
                                 "approaching", "exiting", "got up", "sat down", "turned", "reached",
                                 "working", "typing", "reading", "talking", "using", "sitting",
                                 "looking", "holding", "reaching", "picking", "placing", "carrying"]
            has_activity = any(kw in summary_lower for kw in activity_keywords)
            
            # Person-related keywords - also significant
            person_keywords = ["person", "man", "woman", "someone", "human", "people", 
                               "individual", "figure", "they", "he", "she"]
            has_person = any(kw in summary_lower for kw in person_keywords)
            
            # Noise patterns - ONLY filter if explicitly negative
            noise_patterns = [
                "no person visible", "no one visible", "empty room", "nothing detected",
                "unclear image", "cannot see", "not visible"
            ]
            is_explicit_noise = any(p in summary_lower for p in noise_patterns)
            
            # If we have person OR activity, it's significant
            is_significant = (has_person or has_activity) and not is_explicit_noise
            
            # Legacy is_noise for backwards compatibility
            is_noise = is_explicit_noise and not has_activity and not has_person
            
            # Update last summary for next comparison (always update if we got a real summary)
            if not is_noise and "no_change" not in summary.lower():
                _last_summary = summary
            
            return not is_noise, summary
        else:
            return True, response[:80]  # Fallback to truncated original
            
    except requests.exceptions.Timeout:
        logger.debug("LLM summarization timeout")
        return True, response[:80]
    except Exception as e:
        logger.debug(f"LLM summarization failed: {e}")
        return True, response[:80]


def validate_with_llm(
    response: str,
    context: str = "",
    model: str = "qwen2.5:3b",
    timeout: int = 10,
) -> Tuple[bool, str]:
    """Use small LLM to validate AND summarize response.
    
    Args:
        response: LLM response to validate
        context: Additional context (focus, mode, etc.)
        model: Small LLM model name
        timeout: Request timeout
        
    Returns:
        (should_report, short_summary) tuple
    """
    # Extract focus from context
    focus = "person"
    if "focus:" in context.lower():
        parts = context.lower().split("focus:")
        if len(parts) > 1:
            focus = parts[1].split()[0].strip()
    
    return summarize_detection(response, focus=focus, model=model, timeout=timeout)


def is_significant_smart(
    response: str,
    mode: str = "general",
    focus: str = "person",
    guarder_model: str = None,
    fallback_to_regex: bool = True,
    tracking_data: Dict = None,
) -> Tuple[bool, str]:
    """Smart significance check - uses LLM to analyze with tracking metadata.
    
    Combines:
    - Vision LLM response (what the image shows)
    - Tracking data from DSL (object positions, movement, state)
    
    Optimized: skips guarder LLM if vision response is already short/clear.
    
    Args:
        response: Vision LLM response text
        mode: Analysis mode
        focus: What we're tracking (person, vehicle, etc.)
        guarder_model: Model for summarization (None = use config)
        fallback_to_regex: If LLM fails, use simple truncation
        tracking_data: Dict with tracking metadata from ObjectTracker/DSL
        
    Returns:
        (is_significant, short_summary) tuple
    """
    from .config import config
    
    if not response or not response.strip():
        return False, "No data"
    
    response_clean = response.replace('\n', ' ').strip()
    response_lower = response_clean.lower()
    
    # OPTIMIZATION: Skip guarder LLM for clear responses
    # This saves 2-4 seconds per frame
    
    # Check if it's a clear negative (regardless of length)
    if response_lower.startswith(f"no {focus}") or response_lower.startswith("no person"):
        return False, f"No {focus} visible"
    
    # For short responses, extract info from tracking data
    if len(response_clean) < 80:
        # Check if it's a clear positive with activity
        if response_lower.startswith("yes") or f"yes, there is a {focus}" in response_lower:
            # Extract activity from tracking data
            tracking_data = tracking_data or {}
            direction = tracking_data.get("direction", "")
            state = tracking_data.get("person_state", "")
            dsl_desc = tracking_data.get("description", "")
            
            # Build summary from tracking
            if dsl_desc and len(dsl_desc) < 50:
                return True, dsl_desc
            elif direction and direction not in ("unknown", "stationary"):
                return True, f"{focus.title()} {direction}"
            elif state and state not in ("unknown", "not_visible"):
                return True, f"{focus.title()} {state.replace('_', ' ')}"
            else:
                return True, f"{focus.title()} visible"
    
    # For longer responses, use guarder LLM with tracking data
    if guarder_model is None:
        guarder_model = config.get("SQ_GUARDER_MODEL", "gemma:2b")
    
    available, actual_model = check_guarder_model_available(guarder_model)
    
    if available:
        is_significant_result, summary = _analyze_with_tracking_llm(
            response, 
            focus=focus, 
            model=actual_model,
            tracking_data=tracking_data or {}
        )
        return is_significant_result, summary
    else:
        # Fallback: simple truncation
        short = response_clean[:80]
        if len(response_clean) > 80:
            short += "..."
        return True, short


def _analyze_with_tracking_llm(
    response: str,
    focus: str = "person",
    model: str = "gemma:2b",
    tracking_data: Dict = None,
    timeout: int = 10,
) -> Tuple[bool, str]:
    """Use LLM to analyze vision response with tracking metadata from DSL.
    
    Combines:
    - Vision description (what the image shows)
    - Tracking data (object positions, movement direction, state)
    
    Returns:
        (is_target_present, short_summary)
    """
    import requests
    from .config import config
    from .prompts import get_prompt
    
    ollama_url = config.get("SQ_OLLAMA_URL", "http://localhost:11434")
    tracking_data = tracking_data or {}
    
    # Build tracking context from DSL data
    tracking_context = _build_tracking_context(tracking_data, focus)
    
    # Load prompt from file or use default
    prompt_template = get_prompt("analyze_with_tracking")
    if not prompt_template:
        prompt_template = """Analyze this scene:

VISION: {vision_description}

TRACKING DATA:
{tracking_context}

TARGET: {focus}

Based on both vision and tracking data:
1. Is {focus} present? (yes/no)
2. What is their activity/state?
3. Movement direction?

Reply format:
PRESENT: yes/no
SUMMARY: [short description for TTS, max 10 words]"""
    
    prompt = prompt_template.format(
        vision_description=response[:300],
        tracking_context=tracking_context,
        focus=focus
    )
    
    try:
        resp = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": 50,
                    "temperature": 0.1,
                }
            },
            timeout=timeout,
        )
        
        if resp.ok:
            data = resp.json()
            llm_response = data.get("response", "").strip()
            return _parse_tracking_response(llm_response, focus, original_vision=response)
        else:
            return True, response[:60]
            
    except Exception as e:
        return True, response[:60]


def _build_tracking_context(tracking_data: Dict, focus: str) -> str:
    """Build compact tracking context from DSL data.
    
    Uses new LLM-optimized format (~60 bytes vs ~500 bytes old format).
    """
    # Try to use frame_deltas if available for ultra-compact format
    frame_deltas = tracking_data.get("frame_deltas")
    if frame_deltas:
        try:
            from .llm_motion_prompt import generate_motion_context
            return generate_motion_context(frame_deltas, focus=focus)
        except Exception:
            pass  # Fall through to legacy format
    
    # Compact legacy format
    parts = []
    
    # Motion + objects (most important)
    motion_pct = tracking_data.get("motion_percent", 0)
    obj_count = tracking_data.get("object_count", 0)
    direction = tracking_data.get("direction", "")
    state = tracking_data.get("person_state", "")
    
    # Build one-liner: "Motion: 5% | 2 objects | moving RIGHT | walking"
    info = []
    if motion_pct > 0:
        info.append(f"Motion:{motion_pct:.0f}%")
    if obj_count > 0:
        info.append(f"{obj_count}obj")
    if direction and direction not in ("unknown", "stationary"):
        info.append(direction)
    if state and state not in ("unknown", "not_visible"):
        info.append(state.replace("_", " "))
    
    if info:
        parts.append(" | ".join(info))
    
    # Position (compact)
    position = tracking_data.get("position")
    if position:
        x, y = position.get("x", 0.5), position.get("y", 0.5)
        pos_str = ""
        if x < 0.33: pos_str = "L"
        elif x > 0.66: pos_str = "R"
        else: pos_str = "C"
        if y < 0.33: pos_str = "top-" + pos_str
        elif y > 0.66: pos_str = "bot-" + pos_str
        parts.append(f"@{pos_str}")
    
    # DSL description (if short)
    dsl_desc = tracking_data.get("description", "")
    if dsl_desc and len(dsl_desc) < 40:
        parts.append(f'"{dsl_desc}"')
    
    return " ".join(parts) if parts else "No tracking"


def _parse_tracking_response(llm_response: str, focus: str, original_vision: str = "") -> Tuple[bool, str]:
    """Parse LLM response with tracking analysis.
    
    Prioritizes vision LLM's determination of presence over guarder's interpretation.
    """
    # Clean markdown formatting
    clean_response = llm_response.replace("**", "").replace("*", "").strip()
    original_lower = original_vision.lower() if original_vision else ""
    
    # FIRST: Check if original vision response clearly says no target
    # This takes priority over guarder's interpretation
    if original_lower.startswith(f"no {focus}") or f"no {focus} visible" in original_lower:
        return False, f"No {focus} visible"
    
    is_present = False
    summary = ""
    
    # Try to parse structured format: PRESENT: yes/no | SUMMARY: ...
    if "|" in clean_response:
        parts = clean_response.split("|")
        for part in parts:
            part_lower = part.strip().lower()
            if part_lower.startswith("present:"):
                value = part_lower.replace("present:", "").strip()
                is_present = value.startswith("yes") or value == "true"
            elif part_lower.startswith("summary:"):
                summary = part.split(":", 1)[1].strip() if ":" in part else ""
    else:
        # Try line-by-line parsing
        for line in clean_response.split('\n'):
            line_lower = line.lower().strip()
            if line_lower.startswith("present:"):
                value = line_lower.replace("present:", "").strip()
                is_present = value.startswith("yes") or value == "true"
            elif line_lower.startswith("summary:"):
                summary = line.split(":", 1)[1].strip() if ":" in line else ""
    
    # If no structured response, extract from text
    if not summary:
        resp_lower = clean_response.lower()
        
        # Detect presence - check for negatives first
        if f"no {focus}" in resp_lower or "not present" in resp_lower or "not visible" in resp_lower:
            is_present = False
            summary = f"No {focus} visible"
        elif "yes" in resp_lower or (focus in resp_lower and f"no {focus}" not in resp_lower):
            is_present = True
            # Extract activity words
            activities = ["sitting", "standing", "walking", "working", "moving", "entering", "leaving"]
            for act in activities:
                if act in resp_lower:
                    summary = f"{focus.title()} {act}"
                    break
            if not summary:
                summary = f"{focus.title()} present"
    
    # Clean up summary
    summary = summary.strip().replace("[", "").replace("]", "")
    if not summary or summary == "5 words max":
        summary = f"{focus.title()} detected" if is_present else f"No {focus} visible"
    
    return is_present, summary


def _analyze_with_llm(
    response: str,
    focus: str = "person",
    model: str = "gemma:2b",
    timeout: int = 8,
) -> Tuple[bool, str]:
    """Legacy: Use small LLM to analyze vision response (without tracking).
    
    Returns:
        (is_target_present, short_summary)
    """
    # Delegate to new function without tracking data
    return _analyze_with_tracking_llm(response, focus, model, {}, timeout)


def _parse_simple_response(llm_summary: str, original_response: str, focus: str) -> Tuple[bool, str]:
    """Parse simple LLM summary response.
    
    The LLM was asked to summarize in 5 words and say if target is present.
    We analyze both the summary and original response.
    """
    llm_lower = llm_summary.lower()
    orig_lower = original_response.lower()
    
    # Check if target is NOT present (negative indicators)
    negative_indicators = ["no", "not", "none", "absent", "empty", "without"]
    is_negative = any(f"{ind} {focus}" in llm_lower or f"{ind} {focus}" in orig_lower 
                      for ind in negative_indicators)
    
    # Also check original response for clear negatives
    if orig_lower.startswith("no ") or "no person visible" in orig_lower or "not visible" in orig_lower:
        is_negative = True
    
    # Check for positive presence
    is_present = not is_negative and (
        focus in llm_lower or 
        focus in orig_lower or
        "yes" in llm_lower
    )
    
    # Use LLM summary if short enough, otherwise truncate original
    summary = llm_summary if len(llm_summary) < 60 else llm_summary[:57] + "..."
    
    # If negative, make it clear
    if is_negative:
        summary = f"No {focus} visible"
    
    return is_present, summary


def _parse_analysis_response(llm_response: str, focus: str) -> Tuple[bool, str]:
    """Parse the structured LLM analysis response."""
    lines = llm_response.strip().split('\n')
    
    is_present = False
    activity = "none"
    summary = ""
    
    for line in lines:
        line_lower = line.lower().strip()
        if line_lower.startswith("present:"):
            value = line_lower.replace("present:", "").strip()
            is_present = value in ("yes", "true", "1")
        elif line_lower.startswith("activity:"):
            activity = line.split(":", 1)[1].strip() if ":" in line else "none"
        elif line_lower.startswith("summary:"):
            summary = line.split(":", 1)[1].strip() if ":" in line else ""
    
    # Build final summary
    if not summary:
        if is_present:
            summary = f"{focus.title()}: {activity}" if activity != "none" else f"{focus.title()} visible"
        else:
            summary = f"No {focus} visible"
    
    # Determine if significant (target present = significant)
    return is_present, summary


def is_significant_with_llm(
    response: str,
    mode: str = "general",
    use_llm: bool = True,  # Changed default to True
    guarder_model: str = "qwen2.5:3b",
) -> bool:
    """Check significance with LLM validation (default) or regex fallback.
    
    Args:
        response: LLM response text
        mode: Analysis mode
        use_llm: If True (default), use small LLM for validation
        guarder_model: Model for validation
        
    Returns:
        True if significant
    """
    if use_llm:
        result, _ = is_significant_smart(response, mode, guarder_model)
        return result
    else:
        return is_significant(response, mode)


def summarize_session(responses: List[str], mode: str = "general") -> str:
    """Create summary from multiple responses.
    
    Args:
        responses: List of LLM responses
        mode: Analysis mode
        
    Returns:
        Summary text
    """
    significant = [r for r in responses if is_significant(r, mode)]
    
    if not significant:
        return "No significant events detected."
    
    alerts = [r for r in significant if should_notify(r, mode)]
    
    summary_parts = [
        f"Total events: {len(significant)}",
        f"Alerts: {len(alerts)}",
    ]
    
    if alerts:
        summary_parts.append("\nKey alerts:")
        for alert in alerts[:5]:  # Max 5 alerts
            fields = extract_structured_fields(alert)
            reason = fields.get("reason", "")
            if reason:
                summary_parts.append(f"  - {reason}")
    
    return "\n".join(summary_parts)
