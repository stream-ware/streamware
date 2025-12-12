"""
LLM-based Intent Parser for Streamware

Replaces hardcoded heuristics with LLM-generated structured output.
Uses local Ollama or OpenAI API to parse natural language commands.

Usage:
    from streamware.llm_intent import parse_command
    
    result = parse_command("detect person and email tom@sapletta.com immediately")
    print(result.cli_args)  # ['--detect', 'person', '--email', 'tom@sapletta.com', '--notify-mode', 'instant']
"""

import json
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import requests

from .config import config


# =============================================================================
# STRUCTURED OUTPUT SCHEMA
# =============================================================================

INTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["detect", "track", "count", "describe", "monitor", "watch"],
            "description": "Primary action to perform"
        },
        "target": {
            "type": "string",
            "description": "What to detect/track (person, car, animal, motion, etc.)"
        },
        "mode": {
            "type": "string",
            "enum": ["yolo", "llm", "hybrid"],
            "description": "Detection mode"
        },
        "notification": {
            "type": "object",
            "properties": {
                "email": {"type": "string", "description": "Email address for notifications"},
                "slack": {"type": "string", "description": "Slack channel"},
                "telegram": {"type": "string", "description": "Telegram chat ID"},
                "webhook": {"type": "string", "description": "Webhook URL"},
                "mode": {
                    "type": "string",
                    "enum": ["instant", "digest", "summary"],
                    "description": "Notification frequency"
                },
                "interval": {"type": "integer", "description": "Digest interval in seconds"}
            }
        },
        "output": {
            "type": "object",
            "properties": {
                "screenshot": {"type": "boolean", "description": "Save screenshots"},
                "recording": {"type": "boolean", "description": "Save video recording"},
                "tts": {"type": "boolean", "description": "Enable text-to-speech"},
                "quiet": {"type": "boolean", "description": "Suppress output"}
            }
        },
        "trigger": {
            "type": "string",
            "description": "Condition to trigger action (e.g., 'when appears', 'if moving')"
        },
        "duration": {
            "type": "integer",
            "description": "Duration in seconds"
        },
        "fps": {
            "type": "number",
            "description": "Frames per second"
        },
        "confidence": {
            "type": "number",
            "description": "Detection confidence threshold (0-1)"
        }
    },
    "required": ["action", "target"]
}


# =============================================================================
# LLM INTENT RESULT
# =============================================================================

@dataclass
class LLMIntent:
    """Structured intent parsed by LLM."""
    raw_text: str
    action: str = "detect"
    target: str = "motion"
    mode: str = "hybrid"
    
    # Notifications
    notify_email: Optional[str] = None
    notify_slack: Optional[str] = None
    notify_telegram: Optional[str] = None
    notify_webhook: Optional[str] = None
    notify_mode: str = "digest"
    notify_interval: int = 60
    
    # Output options
    save_screenshot: bool = False
    save_recording: bool = False
    tts_enabled: bool = False
    quiet: bool = False
    
    # Detection options
    trigger: Optional[str] = None
    duration: int = 60
    fps: float = 2.0
    confidence: float = 0.5
    
    # Source
    url: Optional[str] = None
    
    # LLM metadata
    llm_model: str = ""
    llm_raw_response: str = ""
    parse_error: Optional[str] = None
    
    def to_cli_args(self) -> List[str]:
        """Convert intent to CLI arguments."""
        args = []
        
        # Action & target
        args.extend(["--detect", self.target])
        
        # Mode
        if self.mode != "hybrid":
            args.extend(["--mode", self.mode])
        
        # Notifications
        if self.notify_email:
            args.extend(["--email", self.notify_email])
        if self.notify_slack:
            args.extend(["--slack", self.notify_slack])
        if self.notify_telegram:
            args.extend(["--telegram", self.notify_telegram])
        if self.notify_webhook:
            args.extend(["--webhook", self.notify_webhook])
        if self.notify_mode != "digest":
            args.extend(["--notify-mode", self.notify_mode])
        if self.notify_interval != 60:
            args.extend(["--notify-interval", str(self.notify_interval)])
        
        # Output
        if self.save_screenshot:
            args.append("--screenshot")
        if self.save_recording:
            args.append("--record")
        if self.tts_enabled:
            args.append("--tts")
        if self.quiet:
            args.append("--quiet")
        
        # Detection options
        if self.duration != 60:
            args.extend(["--duration", str(self.duration)])
        if self.fps != 2.0:
            args.extend(["--fps", str(self.fps)])
        if self.confidence != 0.5:
            args.extend(["--confidence", str(self.confidence)])
        
        # URL
        if self.url:
            args.extend(["--url", self.url])
        
        return args
    
    def to_cli_string(self) -> str:
        """Return full CLI command string."""
        args = self.to_cli_args()
        return "sq watch " + " ".join(args)
    
    def to_env(self) -> Dict[str, str]:
        """Convert intent to environment variables."""
        env = {
            "SQ_ACTION": self.action,
            "SQ_TARGET": self.target,
            "SQ_MODE": self.mode,
            "SQ_DURATION": str(self.duration),
            "SQ_FPS": str(self.fps),
            "SQ_CONFIDENCE": str(self.confidence),
        }
        
        if self.notify_email:
            env["SQ_NOTIFY_EMAIL"] = self.notify_email
        if self.notify_slack:
            env["SQ_NOTIFY_SLACK"] = self.notify_slack
        if self.notify_telegram:
            env["SQ_NOTIFY_TELEGRAM"] = self.notify_telegram
        if self.notify_webhook:
            env["SQ_NOTIFY_WEBHOOK"] = self.notify_webhook
        if self.notify_mode:
            env["SQ_NOTIFY_MODE"] = self.notify_mode
        
        if self.tts_enabled:
            env["SQ_TTS"] = "true"
        
        return env
    
    def describe(self) -> str:
        """Human-readable description."""
        parts = [f"{self.action.title()} {self.target}"]
        
        if self.mode != "hybrid":
            parts.append(f"mode={self.mode}")
        
        if self.trigger:
            parts.append(f"when: {self.trigger}")
        
        notifs = []
        if self.notify_email:
            notifs.append(f"📧 {self.notify_email}")
        if self.notify_slack:
            notifs.append(f"💬 {self.notify_slack}")
        if self.notify_telegram:
            notifs.append(f"📱 {self.notify_telegram}")
        if notifs:
            parts.append("→ " + ", ".join(notifs))
        
        return " | ".join(parts)


# =============================================================================
# LLM PROVIDERS
# =============================================================================

def _call_ollama(prompt: str, model: str = "llama3.2") -> str:
    """Call local Ollama API."""
    ollama_url = config.get("SQ_OLLAMA_URL", "http://localhost:11434")
    
    try:
        response = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
            },
            timeout=30
        )
        if response.ok:
            return response.json().get("response", "")
    except Exception as e:
        raise RuntimeError(f"Ollama error: {e}")
    
    return ""


def _call_openai(prompt: str, model: str = "gpt-4o-mini") -> str:
    """Call OpenAI API."""
    api_key = config.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
            },
            timeout=30
        )
        if response.ok:
            return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        raise RuntimeError(f"OpenAI error: {e}")
    
    return ""


# =============================================================================
# PROMPT TEMPLATE
# =============================================================================

PARSE_PROMPT = """Parse this natural language command for a video surveillance system.
Extract structured parameters for the CLI.

Command: "{command}"

Return a JSON object with these fields:
- action: "detect", "track", "count", "describe", "monitor", or "watch"
- target: what to look for (person, car, animal, motion, face, object, etc.)
- mode: "yolo" (fast detection only), "llm" (AI description), or "hybrid" (both)
- notification: object with:
  - email: email address if mentioned
  - slack: slack channel if mentioned  
  - telegram: telegram chat ID if mentioned
  - webhook: webhook URL if mentioned
  - mode: "instant" (each event), "digest" (batched), or "summary" (end only)
  - interval: seconds between digests (default 60)
- output: object with:
  - screenshot: true if should save images
  - recording: true if should record video
  - tts: true if should speak aloud
  - quiet: true if minimal output
- trigger: condition text if specified
- duration: seconds to run (default 60)
- fps: frames per second (default 2.0)
- confidence: detection threshold 0-1 (default 0.5)

Keywords to look for:
- "immediately", "instant", "right away" → notification.mode = "instant"
- "every X minutes/seconds" → notification.mode = "digest", interval = X
- "at the end", "summary" → notification.mode = "summary"
- "email X@Y" → notification.email = "X@Y"
- "fast", "quick" → mode = "yolo"
- "describe", "explain" → mode = "llm"
- "screenshot", "photo" → output.screenshot = true
- "record", "video" → output.recording = true
- "speak", "say", "voice" → output.tts = true

Return ONLY valid JSON, no explanation.
"""


# =============================================================================
# MAIN PARSER
# =============================================================================

def parse_command(
    command: str,
    provider: str = "auto",
    model: Optional[str] = None,
    fallback_to_heuristics: bool = True
) -> LLMIntent:
    """
    Parse natural language command using LLM.
    
    Args:
        command: Natural language command
        provider: "ollama", "openai", or "auto" (try ollama first)
        model: Specific model to use
        fallback_to_heuristics: Use regex fallback if LLM fails
    
    Returns:
        LLMIntent with structured parameters
    """
    intent = LLMIntent(raw_text=command)
    
    # Try LLM parsing
    prompt = PARSE_PROMPT.format(command=command)
    llm_response = ""
    
    try:
        if provider == "auto":
            # Try Ollama first, fall back to OpenAI
            try:
                llm_response = _call_ollama(prompt, model or "llama3.2")
                intent.llm_model = model or "llama3.2"
            except Exception:
                if config.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY"):
                    llm_response = _call_openai(prompt, model or "gpt-4o-mini")
                    intent.llm_model = model or "gpt-4o-mini"
        elif provider == "ollama":
            llm_response = _call_ollama(prompt, model or "llama3.2")
            intent.llm_model = model or "llama3.2"
        elif provider == "openai":
            llm_response = _call_openai(prompt, model or "gpt-4o-mini")
            intent.llm_model = model or "gpt-4o-mini"
        
        intent.llm_raw_response = llm_response
        
        # Parse JSON response
        if llm_response:
            data = json.loads(llm_response)
            intent = _apply_parsed_data(intent, data)
            return intent
            
    except json.JSONDecodeError as e:
        intent.parse_error = f"JSON parse error: {e}"
    except Exception as e:
        intent.parse_error = f"LLM error: {e}"
    
    # Fallback to heuristics
    if fallback_to_heuristics:
        intent = _parse_with_heuristics(intent)
    
    return intent


def _apply_parsed_data(intent: LLMIntent, data: Dict[str, Any]) -> LLMIntent:
    """Apply parsed JSON data to intent."""
    intent.action = data.get("action", "detect")
    intent.target = data.get("target", "motion")
    intent.mode = data.get("mode", "hybrid")
    
    # Notifications
    notif = data.get("notification", {})
    intent.notify_email = notif.get("email")
    intent.notify_slack = notif.get("slack")
    intent.notify_telegram = notif.get("telegram")
    intent.notify_webhook = notif.get("webhook")
    intent.notify_mode = notif.get("mode", "digest")
    intent.notify_interval = notif.get("interval", 60)
    
    # Output
    output = data.get("output", {})
    intent.save_screenshot = output.get("screenshot", False)
    intent.save_recording = output.get("recording", False)
    intent.tts_enabled = output.get("tts", False)
    intent.quiet = output.get("quiet", False)
    
    # Detection
    intent.trigger = data.get("trigger")
    intent.duration = data.get("duration", 60)
    intent.fps = data.get("fps", 2.0)
    intent.confidence = data.get("confidence", 0.5)
    
    return intent


def _parse_with_heuristics(intent: LLMIntent) -> LLMIntent:
    """Fallback regex-based parsing."""
    text = intent.raw_text.lower()
    
    # Action
    if "track" in text:
        intent.action = "track"
    elif "count" in text:
        intent.action = "count"
    elif "describe" in text:
        intent.action = "describe"
    elif "monitor" in text:
        intent.action = "monitor"
    else:
        intent.action = "detect"
    
    # Target
    targets = ["person", "people", "car", "vehicle", "animal", "dog", "cat", "face", "motion"]
    for t in targets:
        if t in text:
            intent.target = t if t != "people" else "person"
            break
    
    # Mode
    if "yolo" in text or "fast" in text:
        intent.mode = "yolo"
    elif "llm" in text or "describe" in text:
        intent.mode = "llm"
    
    # Email
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    if email_match:
        intent.notify_email = email_match.group()
    
    # Notification mode
    if any(kw in text for kw in ["immediately", "instant", "right away", "now"]):
        intent.notify_mode = "instant"
    elif "summary" in text or "at the end" in text:
        intent.notify_mode = "summary"
    
    # Screenshot/Recording
    if "screenshot" in text or "photo" in text:
        intent.save_screenshot = True
    if "record" in text or "video" in text:
        intent.save_recording = True
    if "speak" in text or "voice" in text or "tts" in text:
        intent.tts_enabled = True
    
    return intent


# =============================================================================
# CLI HELPER
# =============================================================================

def generate_cli(command: str, url: Optional[str] = None) -> str:
    """
    Generate complete CLI command from natural language.
    
    Args:
        command: Natural language command
        url: Optional video source URL
    
    Returns:
        Full CLI command string
    """
    intent = parse_command(command)
    
    if url:
        intent.url = url
    elif not intent.url:
        intent.url = config.get("SQ_DEFAULT_URL")
    
    return intent.to_cli_string()


# =============================================================================
# QUICK ACCESS
# =============================================================================

def parse(text: str) -> LLMIntent:
    """Quick alias for parse_command."""
    return parse_command(text)


if __name__ == "__main__":
    # Test
    import sys
    
    if len(sys.argv) > 1:
        cmd = " ".join(sys.argv[1:])
    else:
        cmd = "detect person and email tom@sapletta.com immediately"
    
    print(f"Command: {cmd}")
    print()
    
    intent = parse_command(cmd)
    
    print(f"Parsed: {intent.describe()}")
    print(f"CLI: {intent.to_cli_string()}")
    print(f"Args: {intent.to_cli_args()}")
    print()
    print(f"Model: {intent.llm_model or 'heuristics'}")
    if intent.parse_error:
        print(f"Error: {intent.parse_error}")
