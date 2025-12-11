"""
Streamware Intent-based Configuration
Natural language interface for video analysis.

Usage:
    # Natural language commands
    sq watch "tell me when someone enters"
    sq watch "count people in the room"
    sq watch "describe what's happening"
    sq watch "alert if car approaches"
    
    # Or in Python
    from streamware.intent import parse_intent
    config = parse_intent("track person and notify when they leave")
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import re


# =============================================================================
# INTENT PATTERNS - Natural language to config mapping
# =============================================================================

# Keywords for different intents
INTENT_KEYWORDS = {
    # What to do
    "track": ["track", "follow", "śledzić", "śledź", "obserwuj", "watch"],
    "count": ["count", "how many", "liczba", "ile ", "policz"],  # Note: "ile " with space to avoid matching "detailed"
    "describe": ["describe", "what is", "co się dzieje", "opisz", "tell me about", "detailed", "szczegółowo"],
    "alert": ["alert", "notify", "warn", "powiadom", "alarm", "ostrzeż"],
    "detect": ["detect", "find", "spot", "wykryj", "znajdź"],
    
    # What to look for
    "person": ["person", "people", "someone", "człowiek", "osoba", "ludzie", "ktoś"],
    "car": ["car", "vehicle", "samochód", "samochodów", "pojazd", "auto", "aut"],
    "animal": ["animal", "pet", "zwierzę", "zwierzak"],
    "cat": ["cat", "kot", "kitty"],
    "dog": ["dog", "pies", "doggy"],
    "bird": ["bird", "ptak"],
    "package": ["package", "delivery", "paczka", "przesyłka"],
    "motion": ["motion", "movement", "ruch"],
    
    # When/How
    "enter": ["enter", "enters", "entering", "wchodzi", "wejście", "pojawia"],
    "leave": ["leave", "leaves", "leaving", "exit", "wychodzi", "opuszcza", "znika"],
    "move": ["move", "moving", "porusza", "rusza"],
    "approach": ["approach", "approaching", "zbliża", "nadchodzi"],
    
    # Speed/Quality
    "fast": ["fast", "quick", "szybko", "szybki"],
    "slow": ["slow", "detailed", "wolno", "szczegółowo", "dokładnie"],
    "realtime": ["realtime", "instant", "natychmiast", "w czasie rzeczywistym"],
}

# Intent templates
INTENT_TEMPLATES = {
    # Simple detection
    "detect_{target}": {
        "patterns": [
            r"(detect|find|spot|wykryj|znajdź)\s+(person|car|animal|cat|dog|bird)",
            r"(czy jest|is there)\s+(person|car|animal|cat|dog|bird)",
        ],
        "config": lambda m: {"focus": m.group(2), "mode": "track", "llm": False}
    },
    
    # Tracking with events
    "track_{target}": {
        "patterns": [
            r"(track|follow|śledzić|śledź|obserwuj)\s+(person|people|car|animal|cat|dog)",
            r"(watch for|czekaj na)\s+(person|people|car|animal)",
        ],
        "config": lambda m: {"focus": m.group(2), "mode": "track", "track": True, "llm": False}
    },
    
    # Counting
    "count_{target}": {
        "patterns": [
            r"(count|how many|ile|policz)\s+(person|people|car|animal)",
            r"(liczba|number of)\s+(person|people|car|animal)",
        ],
        "config": lambda m: {"focus": m.group(2), "mode": "count", "llm": False}
    },
    
    # Description
    "describe": {
        "patterns": [
            r"(describe|opisz|what is happening|co się dzieje)",
            r"(tell me about|powiedz co|opowiedz)",
        ],
        "config": lambda m: {"mode": "describe", "llm": True, "llm_model": "llava:7b"}
    },
    
    # Alerts
    "alert_enter": {
        "patterns": [
            r"(alert|notify|powiadom).*(enter|wchodzi|pojawia)",
            r"(tell me when|powiedz gdy).*(enter|wchodzi|someone comes)",
        ],
        "config": lambda m: {"mode": "track", "tts": True, "trigger": "enter"}
    },
    
    "alert_leave": {
        "patterns": [
            r"(alert|notify|powiadom).*(leave|wychodzi|znika)",
            r"(tell me when|powiedz gdy).*(leave|exits|wychodzi)",
        ],
        "config": lambda m: {"mode": "track", "tts": True, "trigger": "leave"}
    },
}


@dataclass
class Intent:
    """Parsed user intent."""
    raw_text: str
    action: str = "track"           # track, count, describe, alert
    target: str = "person"          # person, car, animal, motion
    trigger: Optional[str] = None   # enter, leave, move, approach
    speed: str = "normal"           # fast, normal, slow, realtime
    
    # Generated config
    fps: float = 1.0
    mode: str = "track"
    llm: bool = False
    llm_model: str = "llava:7b"
    track: bool = True
    tts: bool = True
    tts_mode: str = "diff"
    guarder: bool = False
    
    def to_env(self) -> Dict[str, str]:
        """Convert to environment variables."""
        return {
            "SQ_STREAM_FPS": str(self.fps),
            "SQ_STREAM_MODE": self.mode,
            "SQ_STREAM_FOCUS": self.target,
            "SQ_MODEL": self.llm_model if self.llm else "none",
            "SQ_USE_GUARDER": str(self.guarder).lower(),
            "SQ_YOLO_SKIP_LLM_THRESHOLD": "1.0" if self.llm else "0.3",
        }
    
    def describe(self) -> str:
        """Human-readable description of intent."""
        parts = []
        
        if self.action == "track":
            parts.append(f"Śledzę {self.target}")
        elif self.action == "count":
            parts.append(f"Liczę {self.target}")
        elif self.action == "describe":
            parts.append("Opisuję scenę")
        elif self.action == "alert":
            parts.append(f"Powiadamiam o {self.target}")
        
        if self.trigger:
            triggers_pl = {"enter": "wejściu", "leave": "wyjściu", "move": "ruchu"}
            parts.append(f"przy {triggers_pl.get(self.trigger, self.trigger)}")
        
        parts.append(f"({self.fps} FPS)")
        
        if self.llm:
            parts.append(f"z LLM ({self.llm_model})")
        else:
            parts.append("tylko YOLO")
        
        return " ".join(parts)
    
    def to_cli_args(self) -> List[str]:
        """Convert to CLI arguments."""
        args = [
            "--mode", self.mode,
            "--focus", self.target,
        ]
        if self.tts:
            args.append("--tts")
            if self.tts_mode == "diff":
                args.append("--tts-diff")
        return args


def parse_intent(text: str) -> Intent:
    """Parse natural language text into Intent.
    
    Examples:
        "track person" → track mode, focus person
        "count people in room" → count mode, focus person
        "tell me when someone enters" → track mode, trigger enter, tts
        "describe what's happening" → describe mode, llm enabled
        "fast detection of cars" → fast fps, focus car
    """
    text_lower = text.lower().strip()
    intent = Intent(raw_text=text)
    
    # Detect action
    for action, keywords in [
        ("count", INTENT_KEYWORDS["count"]),
        ("describe", INTENT_KEYWORDS["describe"]),
        ("alert", INTENT_KEYWORDS["alert"]),
        ("track", INTENT_KEYWORDS["track"]),
        ("detect", INTENT_KEYWORDS["detect"]),
    ]:
        if any(kw in text_lower for kw in keywords):
            intent.action = action
            break
    
    # Detect target
    for target, keywords in [
        ("person", INTENT_KEYWORDS["person"]),
        ("car", INTENT_KEYWORDS["car"]),
        ("cat", INTENT_KEYWORDS["cat"]),
        ("dog", INTENT_KEYWORDS["dog"]),
        ("bird", INTENT_KEYWORDS["bird"]),
        ("animal", INTENT_KEYWORDS["animal"]),
        ("motion", INTENT_KEYWORDS["motion"]),
    ]:
        if any(kw in text_lower for kw in keywords):
            intent.target = target
            break
    
    # Detect trigger
    for trigger, keywords in [
        ("enter", INTENT_KEYWORDS["enter"]),
        ("leave", INTENT_KEYWORDS["leave"]),
        ("move", INTENT_KEYWORDS["move"]),
        ("approach", INTENT_KEYWORDS["approach"]),
    ]:
        if any(kw in text_lower for kw in keywords):
            intent.trigger = trigger
            break
    
    # Detect speed
    for speed, keywords in [
        ("realtime", INTENT_KEYWORDS["realtime"]),
        ("fast", INTENT_KEYWORDS["fast"]),
        ("slow", INTENT_KEYWORDS["slow"]),
    ]:
        if any(kw in text_lower for kw in keywords):
            intent.speed = speed
            break
    
    # Apply configuration based on action
    if intent.action == "track":
        intent.mode = "track"
        intent.track = True
        intent.llm = False
        intent.fps = 1.0
    elif intent.action == "count":
        intent.mode = "track"  # Use tracking for counting
        intent.track = True
        intent.llm = False
        intent.fps = 1.0
    elif intent.action == "describe":
        intent.mode = "full"
        intent.track = False
        intent.llm = True
        intent.llm_model = "llava:7b"
        intent.fps = 0.2
        intent.guarder = True
    elif intent.action == "alert":
        intent.mode = "track"
        intent.track = True
        intent.llm = False
        intent.tts = True
        intent.fps = 1.0
    elif intent.action == "detect":
        intent.mode = "track"
        intent.track = False
        intent.llm = False
        intent.fps = 2.0
    
    # Apply speed modifier
    if intent.speed == "realtime":
        intent.fps = 5.0
    elif intent.speed == "fast":
        intent.fps = 2.0
    elif intent.speed == "slow":
        intent.fps = 0.5
        if not intent.llm:
            intent.llm = True
            intent.guarder = True
    
    return intent


def apply_intent(intent: Intent):
    """Apply intent to streamware config."""
    from .config import config
    
    for key, value in intent.to_env().items():
        config.set(key, value)
    
    print(f"✅ Intent: {intent.describe()}")
    print(f"   Raw: \"{intent.raw_text}\"")


# =============================================================================
# NATURAL LANGUAGE EXAMPLES
# =============================================================================

EXAMPLES = {
    # English
    "track person": "Śledzenie osób (1 FPS, YOLO)",
    "track people entering": "Śledzenie wchodzących osób",
    "count people": "Liczenie osób w kadrze",
    "tell me when someone enters": "Powiadomienie o wejściu",
    "describe what's happening": "Szczegółowy opis sceny (LLM)",
    "fast detection of cars": "Szybkie wykrywanie aut (2 FPS)",
    "alert when car approaches": "Alarm przy zbliżaniu się auta",
    
    # Polish
    "śledź osoby": "Śledzenie osób",
    "ile osób": "Liczenie osób",
    "powiadom gdy ktoś wchodzi": "Powiadomienie o wejściu",
    "opisz co się dzieje": "Opis sceny (LLM)",
    "szybko wykrywaj ruch": "Szybkie wykrywanie ruchu",
}


def show_examples():
    """Show example intents."""
    print("Natural language examples:\n")
    for text, description in EXAMPLES.items():
        intent = parse_intent(text)
        print(f'  "{text}"')
        print(f"    → {intent.describe()}")
        print()


# =============================================================================
# CLI
# =============================================================================

def intent_cli():
    """CLI for intent-based configuration."""
    import sys
    
    if len(sys.argv) < 2:
        print("Streamware - Natural Language Configuration")
        print()
        print("Usage:")
        print("  sq intent \"<natural language command>\"")
        print()
        print("Examples:")
        show_examples()
        return
    
    # Join all args as intent text
    text = " ".join(sys.argv[1:])
    
    # Remove quotes if present
    text = text.strip("'\"")
    
    intent = parse_intent(text)
    print(f"Intent: {intent.describe()}")
    print()
    print("Generated config:")
    for key, value in intent.to_env().items():
        print(f"  {key}={value}")


if __name__ == "__main__":
    intent_cli()
