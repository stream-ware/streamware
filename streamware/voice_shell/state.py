"""
Conversation state management for Voice Shell.

Separates state from server logic for cleaner code and easier testing.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class InputMode(Enum):
    """Current input mode for the conversation."""
    NORMAL = "normal"           # Regular command input
    CONFIRMING = "confirming"   # Waiting for yes/no
    OPTIONS = "options"         # Waiting for option selection (1/2/3)
    EMAIL = "email"             # Entering email (spelling mode)
    SPELLING = "spelling"       # Generic spelling mode


@dataclass
class ConversationState:
    """Holds the current state of a voice conversation."""
    
    # Current input mode
    mode: InputMode = InputMode.NORMAL
    
    # Pending command waiting for confirmation
    pending_command: Optional[Any] = None  # ShellResult
    
    # Options for clarification
    pending_options: Optional[List[tuple]] = None  # [(key, desc, cmd), ...]
    
    # Email input state
    pending_input_type: Optional[str] = None  # "email", "url", etc.
    pending_command_template: Optional[str] = None  # "sq watch --email {email}"
    spelling_buffer: str = ""
    
    # Language
    language: str = "en"
    
    def reset(self):
        """Reset conversation state to normal mode."""
        self.mode = InputMode.NORMAL
        self.pending_command = None
        self.pending_options = None
        self.pending_input_type = None
        self.pending_command_template = None
        self.spelling_buffer = ""
    
    def start_confirmation(self, command: Any):
        """Enter confirmation mode for a command."""
        self.mode = InputMode.CONFIRMING
        self.pending_command = command
    
    def start_options(self, options: List[tuple]):
        """Enter options selection mode."""
        self.mode = InputMode.OPTIONS
        self.pending_options = options
    
    def start_email_input(self, command_template: str):
        """Enter email input mode."""
        self.mode = InputMode.EMAIL
        self.pending_input_type = "email"
        self.pending_command_template = command_template
        self.spelling_buffer = ""
    
    def add_to_buffer(self, text: str):
        """Add text to spelling buffer."""
        self.spelling_buffer += text
    
    def clear_buffer(self):
        """Clear spelling buffer."""
        self.spelling_buffer = ""
    
    def delete_last_char(self):
        """Delete last character from buffer."""
        if self.spelling_buffer:
            self.spelling_buffer = self.spelling_buffer[:-1]
    
    def get_email_from_buffer(self) -> str:
        """Get cleaned email from buffer."""
        return self.spelling_buffer.replace(" ", "").lower()
    
    def build_command_with_email(self, email: str) -> str:
        """Build command with email substituted."""
        if self.pending_command_template:
            return self.pending_command_template.replace("{email}", email)
        return ""
    
    def is_confirming(self) -> bool:
        return self.mode == InputMode.CONFIRMING and self.pending_command is not None
    
    def is_selecting_option(self) -> bool:
        return self.mode == InputMode.OPTIONS and self.pending_options is not None
    
    def is_entering_email(self) -> bool:
        return self.mode == InputMode.EMAIL
    
    def to_dict(self) -> Dict:
        """Serialize state for debugging/logging."""
        return {
            "mode": self.mode.value,
            "has_pending_command": self.pending_command is not None,
            "has_options": self.pending_options is not None,
            "buffer": self.spelling_buffer,
            "language": self.language,
        }
