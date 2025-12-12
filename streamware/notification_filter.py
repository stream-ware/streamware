"""
Intelligent Notification Filter using LLM.

Uses a small, fast LLM (qwen2.5:3b) to decide whether a notification
should be sent based on context, intent, and actual content.

This replaces simple heuristics with intelligent understanding.
"""

import requests
from typing import Optional, Dict, Any
from dataclasses import dataclass

from .config import config


@dataclass
class NotificationDecision:
    """Result of notification filter decision."""
    should_notify: bool
    reason: str
    confidence: float
    modified_message: Optional[str] = None


class NotificationFilter:
    """
    LLM-based intelligent notification filter.
    
    Instead of simple string matching like:
        is_static = "scene is still" in description
        
    We use an LLM to understand context and intent:
        - Is this a meaningful detection?
        - Does it match what the user wanted to track?
        - Is this a significant event worth notifying?
    """
    
    def __init__(
        self,
        model: Optional[str] = None,
        ollama_url: Optional[str] = None,
        timeout: int = 10,
    ):
        # Try configured model, fall back to available small models
        self.model = model or config.get("SQ_NOTIFICATION_FILTER_MODEL", "qwen2.5:7b")
        self.ollama_url = ollama_url or config.get("SQ_OLLAMA_URL", "http://localhost:11434")
        self.timeout = int(config.get("SQ_NOTIFICATION_FILTER_TIMEOUT", str(timeout)))
        self.enabled = config.get("SQ_NOTIFICATION_FILTER_ENABLED", "true").lower() == "true"
        
        # Check if model is available, fall back if not
        self._verify_model()
        
        # Cache for similar decisions (avoid redundant LLM calls)
        self._cache: Dict[str, NotificationDecision] = {}
        self._cache_max = 100
    
    def _verify_model(self):
        """Verify model availability, fall back to alternatives if needed."""
        try:
            resp = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if resp.ok:
                models = [m["name"] for m in resp.json().get("models", [])]
                if self.model not in models:
                    # Get fallbacks from config (centralized)
                    fallback_str = config.get("SQ_FALLBACK_MODELS", "qwen2.5:7b,gemma:2b,llama3.2:latest,phi3:mini")
                    fallbacks = [m.strip() for m in fallback_str.split(",") if m.strip()]
                    
                    for fb in fallbacks:
                        if fb in models:
                            print(f"⚠️  Notification filter: {self.model} not found, using {fb}")
                            self.model = fb
                            return
                    # No suitable model, disable LLM filtering
                    print(f"⚠️  Notification filter: No suitable model, using heuristics")
                    self.enabled = False
        except:
            pass  # Keep configured model
    
    def should_notify(
        self,
        description: str,
        focus: str = "person",
        context: Optional[Dict[str, Any]] = None,
    ) -> NotificationDecision:
        """
        Decide whether to send notification based on description.
        
        Args:
            description: The detection/narration description
            focus: What the user is tracking (person, car, motion, etc.)
            context: Additional context (previous state, motion percent, etc.)
            
        Returns:
            NotificationDecision with should_notify, reason, confidence
        """
        if not self.enabled:
            # Fallback to simple heuristic when disabled
            return self._fallback_decision(description, focus)
        
        # Check cache
        cache_key = f"{focus}:{description[:100]}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Build prompt
        prompt = self._build_prompt(description, focus, context)
        
        try:
            decision = self._query_llm(prompt)
            
            # Cache result
            if len(self._cache) >= self._cache_max:
                self._cache.clear()
            self._cache[cache_key] = decision
            
            return decision
            
        except Exception as e:
            # On error, use fallback
            return self._fallback_decision(description, focus)
    
    def _build_prompt(
        self, 
        description: str, 
        focus: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build the decision prompt."""
        context_str = ""
        if context:
            if context.get("motion_percent") is not None:
                context_str += f"Motion level: {context['motion_percent']:.1f}%\n"
            if context.get("previous_state"):
                context_str += f"Previous state: {context['previous_state']}\n"
            if context.get("frame_num"):
                context_str += f"Frame number: {context['frame_num']}\n"
        
        return f"""You are a notification filter for a video surveillance system.

The user wants to track: {focus}
Current description: "{description}"
{context_str}

Decide if this warrants sending a notification (email/alert).

SEND notification when:
- Target ({focus}) is detected/visible
- Target is entering/leaving frame
- Significant event related to target
- User would want to know about this

DO NOT send notification when:
- Scene is static with no target visible
- Generic descriptions without target
- "No motion" or "no significant motion"
- Redundant/repeated information

Respond with EXACTLY one line in format:
NOTIFY: [yes/no] | REASON: [brief reason] | CONFIDENCE: [0.0-1.0]

Example responses:
NOTIFY: yes | REASON: Person detected in frame | CONFIDENCE: 0.9
NOTIFY: no | REASON: Static scene, no person visible | CONFIDENCE: 0.95
"""
    
    def _query_llm(self, prompt: str) -> NotificationDecision:
        """Query the LLM for a decision."""
        response = requests.post(
            f"{self.ollama_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temperature for consistent decisions
                    "num_predict": 100,  # Short response
                }
            },
            timeout=self.timeout,
        )
        
        if not response.ok:
            raise Exception(f"LLM error: {response.status_code}")
        
        text = response.json().get("response", "").strip()
        return self._parse_response(text)
    
    def _parse_response(self, text: str) -> NotificationDecision:
        """Parse LLM response into decision."""
        text = text.upper()
        
        # Parse NOTIFY
        should_notify = "NOTIFY: YES" in text or "NOTIFY:YES" in text
        
        # Parse REASON
        reason = "LLM decision"
        if "REASON:" in text:
            reason_start = text.find("REASON:") + 7
            reason_end = text.find("|", reason_start)
            if reason_end == -1:
                reason_end = len(text)
            reason = text[reason_start:reason_end].strip()
        
        # Parse CONFIDENCE
        confidence = 0.8
        if "CONFIDENCE:" in text:
            try:
                conf_start = text.find("CONFIDENCE:") + 11
                conf_str = text[conf_start:].split()[0].strip()
                confidence = float(conf_str)
            except:
                pass
        
        return NotificationDecision(
            should_notify=should_notify,
            reason=reason.lower(),
            confidence=confidence,
        )
    
    def _fallback_decision(self, description: str, focus: str) -> NotificationDecision:
        """Simple heuristic fallback when LLM unavailable."""
        lower = description.lower()
        
        # Check for static/empty scene indicators
        static_indicators = [
            "scene is still",
            "no person",
            "no significant motion",
            "no motion",
            "no " + focus.lower(),
            "not visible",
        ]
        
        is_static = any(ind in lower for ind in static_indicators)
        
        # Check for target detection
        has_target = focus.lower() in lower and "no " + focus.lower() not in lower
        
        # Log decision for debugging
        print(f"📧 [NotifyFilter] desc='{description[:50]}' focus={focus} static={is_static} target={has_target}", flush=True)
        
        if is_static and not has_target:
            print(f"📧 [NotifyFilter] → SKIP (static scene)", flush=True)
            return NotificationDecision(
                should_notify=False,
                reason=f"Static scene, no {focus} detected",
                confidence=0.7,
            )
        
        if has_target:
            print(f"📧 [NotifyFilter] → SEND ({focus} detected)", flush=True)
            return NotificationDecision(
                should_notify=True,
                reason=f"{focus.title()} detected",
                confidence=0.8,
            )
        
        # Default: send if not clearly static
        return NotificationDecision(
            should_notify=not is_static,
            reason="Unclear, using default",
            confidence=0.5,
        )


# Singleton instance
_filter_instance: Optional[NotificationFilter] = None


def get_notification_filter() -> NotificationFilter:
    """Get the notification filter singleton."""
    global _filter_instance
    if _filter_instance is None:
        _filter_instance = NotificationFilter()
    return _filter_instance


def should_notify(
    description: str,
    focus: str = "person",
    context: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Quick helper to check if notification should be sent.
    
    Usage:
        if should_notify("Person visible in frame", focus="person"):
            send_email(...)
    """
    filter = get_notification_filter()
    decision = filter.should_notify(description, focus, context)
    return decision.should_notify
