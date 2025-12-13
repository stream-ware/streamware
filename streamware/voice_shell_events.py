"""
Voice Shell Events

Event sourcing classes for the voice shell server.
Extracted from voice_shell_server.py for modularity.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import subprocess
import threading
import uuid
import json

# EVENT SOURCING
# =============================================================================

class EventType(str, Enum):
    """Event types for the voice shell."""
    # User events
    VOICE_INPUT = "voice_input"
    TEXT_INPUT = "text_input"
    COMMAND_CONFIRM = "command_confirm"
    
    # Session events
    SESSION_CREATED = "session_created"
    SESSION_SWITCHED = "session_switched"
    SESSION_CLOSED = "session_closed"
    SESSION_OUTPUT = "session_output"
    COMMAND_CANCEL = "command_cancel"
    
    # System events
    COMMAND_PARSED = "command_parsed"
    COMMAND_EXECUTED = "command_executed"
    COMMAND_OUTPUT = "command_output"
    COMMAND_ERROR = "command_error"
    COMMAND_COMPLETED = "command_completed"
    
    # TTS events
    TTS_SPEAK = "tts_speak"
    TTS_COMPLETE = "tts_complete"
    
    # Context events
    CONTEXT_UPDATED = "context_updated"
    LANGUAGE_CHANGED = "language_changed"
    CONFIG_LOADED = "config_loaded"
    VARIABLE_CHANGED = "variable_changed"
    
    # Connection events
    CLIENT_CONNECTED = "client_connected"
    CLIENT_DISCONNECTED = "client_disconnected"


@dataclass
class Event:
    """Event for event sourcing."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: EventType = EventType.TEXT_INPUT
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "timestamp": self.timestamp,
            "data": self.data,
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class EventStore:
    """Simple in-memory event store."""
    
    def __init__(self, max_events: int = 1000):
        self.events: List[Event] = []
        self.max_events = max_events
        self.subscribers: List[callable] = []
    
    def append(self, event: Event):
        """Append event and notify subscribers."""
        self.events.append(event)
        
        # Trim old events
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]
        
        # Notify subscribers
        for subscriber in self.subscribers:
            try:
                subscriber(event)
            except Exception as e:
                print(f"Event subscriber error: {e}")
    
    def subscribe(self, callback: callable):
        """Subscribe to events."""
        self.subscribers.append(callback)
    
    def get_recent(self, count: int = 50) -> List[Event]:
        """Get recent events."""
        return self.events[-count:]


# =============================================================================
# VOICE SHELL SERVER
# =============================================================================

@dataclass
class Session:
    """A single conversation session with its own process."""
    id: str
    name: str
    command: str = ""
    status: str = "idle"  # idle, pending, running, completed, error
    process: Optional[subprocess.Popen] = None
    output: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    thread: Optional[threading.Thread] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "command": self.command,
            "status": self.status,
            "output_lines": len(self.output),
            "created_at": self.created_at.isoformat(),
            "has_process": self.process is not None or self.status in ('running', 'completed', 'error'),
        }
    
    def stop(self):
        """Stop the running process."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except:
                self.process.kill()
            self.process = None
        self.status = "stopped"

