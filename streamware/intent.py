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
    
    # Notifications
    "email": ["email", "mail", "send message", "wyślij", "e-mail"],
    "slack": ["slack", "slack message"],
    "telegram": ["telegram", "tg"],
    "webhook": ["webhook", "http", "api", "post to"],
    "save": ["save", "record", "zapisz", "nagraj"],
    "screenshot": ["screenshot", "capture", "zrzut", "zdjęcie"],
    
    # Notification mode
    "instant": ["instant", "immediately", "natychmiast", "od razu", "each time", "every time"],
    "digest": ["digest", "batch", "zbiorczo", "co minutę", "every minute"],
    "summary": ["summary", "report", "raport", "podsumowanie", "at end", "na koniec"],
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
    
    # Notifications
    notify_email: Optional[str] = None      # Email address
    notify_slack: Optional[str] = None      # Slack channel
    notify_telegram: Optional[str] = None   # Telegram chat_id
    notify_webhook: Optional[str] = None    # Webhook URL
    save_recording: bool = False            # Save video recording
    save_screenshot: bool = False           # Save screenshots on detection
    
    # Notification strategy
    notify_mode: str = "digest"             # instant, digest, summary
    notify_interval: int = 60               # Seconds between digest emails
    notify_cooldown: int = 300              # Min seconds between same alerts
    
    def to_env(self) -> Dict[str, str]:
        """Convert to environment variables."""
        env = {
            "SQ_STREAM_FPS": str(self.fps),
            "SQ_STREAM_MODE": self.mode,
            "SQ_STREAM_FOCUS": self.target,
            "SQ_MODEL": self.llm_model if self.llm else "none",
            "SQ_USE_GUARDER": str(self.guarder).lower(),
            "SQ_YOLO_SKIP_LLM_THRESHOLD": "1.0" if self.llm else "0.3",
        }
        if self.notify_email:
            env["SQ_NOTIFY_EMAIL"] = self.notify_email
        if self.notify_slack:
            env["SQ_NOTIFY_SLACK"] = self.notify_slack
        if self.notify_telegram:
            env["SQ_NOTIFY_TELEGRAM"] = self.notify_telegram
        if self.notify_webhook:
            env["SQ_NOTIFY_WEBHOOK"] = self.notify_webhook
        if self.save_recording:
            env["SQ_SAVE_RECORDING"] = "true"
        if self.save_screenshot:
            env["SQ_SAVE_SCREENSHOT"] = "true"
        # Notification strategy
        env["SQ_NOTIFY_MODE"] = self.notify_mode
        env["SQ_NOTIFY_INTERVAL"] = str(self.notify_interval)
        env["SQ_NOTIFY_COOLDOWN"] = str(self.notify_cooldown)
        return env
    
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
        elif self.action == "detect":
            parts.append(f"Wykrywam {self.target}")
        
        if self.trigger:
            triggers_pl = {"enter": "wejściu", "leave": "wyjściu", "move": "ruchu"}
            parts.append(f"przy {triggers_pl.get(self.trigger, self.trigger)}")
        
        parts.append(f"({self.fps} FPS)")
        
        if self.llm:
            parts.append(f"z LLM ({self.llm_model})")
        else:
            parts.append("tylko YOLO")
        
        # Add notifications
        notifs = []
        if self.notify_email:
            notifs.append(f"📧 {self.notify_email}")
        if self.notify_slack:
            notifs.append(f"💬 Slack: {self.notify_slack}")
        if self.notify_telegram:
            notifs.append(f"📱 Telegram: {self.notify_telegram}")
        if self.notify_webhook:
            notifs.append(f"🔗 Webhook")
        if self.save_screenshot:
            notifs.append("📷 Screenshot")
        if self.save_recording:
            notifs.append("🎥 Recording")
        
        if notifs:
            parts.append("→ " + ", ".join(notifs))
        
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
    
    # Parse notifications
    # Extract email addresses
    email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
    email_match = re.search(email_pattern, text)
    if email_match:
        intent.notify_email = email_match.group()
    
    # Extract webhook URLs
    url_pattern = r'https?://[\w\.-]+[/\w\.-]*'
    url_match = re.search(url_pattern, text)
    if url_match:
        intent.notify_webhook = url_match.group()
    
    # Check for notification keywords
    if any(kw in text_lower for kw in INTENT_KEYWORDS.get("slack", [])):
        # Extract slack channel if present (#channel or @user)
        slack_match = re.search(r'[#@][\w-]+', text)
        intent.notify_slack = slack_match.group() if slack_match else "#general"
    
    if any(kw in text_lower for kw in INTENT_KEYWORDS.get("telegram", [])):
        # Extract telegram chat_id if present
        tg_match = re.search(r'@[\w]+|\d{5,}', text)
        intent.notify_telegram = tg_match.group() if tg_match else None
    
    # Check for save options
    if any(kw in text_lower for kw in INTENT_KEYWORDS.get("save", [])):
        intent.save_recording = True
    
    if any(kw in text_lower for kw in INTENT_KEYWORDS.get("screenshot", [])):
        intent.save_screenshot = True
    
    # Detect notification mode
    if any(kw in text_lower for kw in INTENT_KEYWORDS.get("instant", [])):
        intent.notify_mode = "instant"
    elif any(kw in text_lower for kw in INTENT_KEYWORDS.get("summary", [])):
        intent.notify_mode = "summary"
    else:
        intent.notify_mode = "digest"  # Default: batch every 60s
    
    # Extract custom interval (e.g., "every 5 minutes")
    interval_match = re.search(r'every\s+(\d+)\s*(min|minute|sec|second|m|s)', text_lower)
    if interval_match:
        value = int(interval_match.group(1))
        unit = interval_match.group(2)
        if unit.startswith('m'):
            intent.notify_interval = value * 60
        else:
            intent.notify_interval = value
    
    return intent


def apply_intent(intent: Intent):
    """Apply intent to streamware config and save user data."""
    from .config import config
    
    for key, value in intent.to_env().items():
        config.set(key, value)
    
    # Auto-save user-provided notification targets to .env for future use
    saved = []
    if intent.notify_email:
        current = config.get("SQ_EMAIL_TO", "")
        if intent.notify_email not in current:
            config.set("SQ_EMAIL_TO", intent.notify_email)
            saved.append(f"email: {intent.notify_email}")
    
    if intent.notify_slack and intent.notify_slack != "#general":
        config.set("SQ_SLACK_CHANNEL", intent.notify_slack)
        saved.append(f"slack: {intent.notify_slack}")
    
    if intent.notify_telegram:
        config.set("SQ_TELEGRAM_CHAT_ID", intent.notify_telegram)
        saved.append(f"telegram: {intent.notify_telegram}")
    
    if intent.notify_webhook:
        config.set("SQ_WEBHOOK_URL", intent.notify_webhook)
        saved.append(f"webhook: {intent.notify_webhook[:30]}...")
    
    # Save to .env file if any new data
    if saved:
        try:
            config.save()
            print(f"💾 Saved to .env: {', '.join(saved)}")
        except Exception as e:
            print(f"⚠️  Could not save to .env: {e}")
    
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
