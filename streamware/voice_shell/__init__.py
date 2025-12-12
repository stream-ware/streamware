"""
Voice Shell - Modular voice interaction for Streamware.

This package provides:
- handlers.py: Input handling (confirmation, options, email, commands)
- state.py: Session and conversation state management
- database.py: SQLite persistence for sessions, commands, config
"""

from .handlers import InputHandlers
from .state import ConversationState
from .database import VoiceShellDB, get_db

__all__ = [
    "InputHandlers", "ConversationState",
    "VoiceShellDB", "get_db"
]
