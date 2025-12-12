"""
Input handlers for Voice Shell.

Each handler processes a specific type of input and returns True if handled.
This allows for a clean chain-of-responsibility pattern.
"""

from typing import Any, Callable, Optional, Tuple
from dataclasses import dataclass

from .state import ConversationState, InputMode
from ..i18n import get_messages, is_confirm, is_cancel, is_done, is_clear


@dataclass
class HandlerResult:
    """Result from an input handler."""
    handled: bool = False
    speak: Optional[str] = None  # Text to speak via TTS
    command: Optional[Any] = None  # Command to execute
    error: Optional[str] = None


class InputHandlers:
    """
    Collection of input handlers for Voice Shell.
    
    Each handler checks if it should handle the input and processes it.
    Returns HandlerResult with speak text or command to execute.
    """
    
    def __init__(self, state: ConversationState, lang: str = "en"):
        self.state = state
        self.lang = lang
        self._msg = get_messages(lang)
    
    def set_language(self, lang: str):
        """Update language for messages."""
        self.lang = lang
        self._msg = get_messages(lang)
        self.state.language = lang
    
    def handle_confirmation(self, text: str) -> HandlerResult:
        """Handle yes/no confirmation for pending command."""
        if not self.state.is_confirming():
            return HandlerResult(handled=False)
        
        lower = text.lower().strip()
        
        # Check for confirmation
        if is_confirm(lower, self.lang):
            cmd = self.state.pending_command
            self.state.reset()
            return HandlerResult(
                handled=True,
                command=cmd,
                speak=self._msg.executing,
            )
        
        # Check for cancellation
        if is_cancel(lower, self.lang):
            self.state.reset()
            return HandlerResult(
                handled=True,
                speak=self._msg.cancelled,
            )
        
        return HandlerResult(handled=False)
    
    def handle_option_selection(self, text: str) -> HandlerResult:
        """Handle option selection (1/2/3 or one/two/three)."""
        if not self.state.is_selecting_option():
            return HandlerResult(handled=False)
        
        lower = text.lower().strip()
        
        # Map words to numbers
        option_map = {
            "one": "1", "1": "1", "first": "1",
            "two": "2", "2": "2", "second": "2",
            "three": "3", "3": "3", "third": "3",
            "four": "4", "4": "4", "fourth": "4",
            # Polish
            "jeden": "1", "dwa": "2", "trzy": "3", "cztery": "4",
            "pierwszy": "1", "drugi": "2", "trzeci": "3", "czwarty": "4",
        }
        
        choice = option_map.get(lower, lower)
        
        # Find matching option
        for key, desc, cmd in self.state.pending_options:
            if choice == key:
                self.state.pending_options = None
                
                # Special commands
                if cmd == "need_email":
                    self.state.start_email_input(
                        "SQ_NOTIFY_EMAIL={email} sq live narrator --mode track --focus person --duration 60 --skip-checks --adaptive"
                    )
                    return HandlerResult(
                        handled=True,
                        speak=self._msg.email_prompt,
                    )
                
                if cmd == "functions":
                    self.state.mode = InputMode.NORMAL
                    return HandlerResult(
                        handled=True,
                        speak="Functions list...",  # TODO: get from shell
                    )
                
                # Regular command - needs confirmation
                self.state.mode = InputMode.NORMAL
                return HandlerResult(
                    handled=True,
                    speak=f"{desc}. {self._msg.say_yes_confirm}",
                    command=("confirm_needed", cmd, desc),  # Signal to set pending
                )
        
        # No match - repeat options
        options_text = self._msg.please_say_number
        return HandlerResult(handled=True, speak=options_text)
    
    def handle_email_input(self, text: str) -> HandlerResult:
        """Handle email spelling/input mode."""
        if not self.state.is_entering_email():
            return HandlerResult(handled=False)
        
        lower = text.lower().strip()
        
        # Check for done
        if is_done(lower, self.lang):
            if self.state.spelling_buffer:
                email = self.state.get_email_from_buffer()
                cmd = self.state.build_command_with_email(email)
                self.state.reset()
                return HandlerResult(
                    handled=True,
                    speak=self._msg.email_set.format(email=email),
                    command=("confirm_needed", cmd, f"Detect and email {email}"),
                )
            return HandlerResult(handled=True)
        
        # Check for clear
        if is_clear(lower, self.lang):
            self.state.clear_buffer()
            return HandlerResult(
                handled=True,
                speak=self._msg.email_cleared,
            )
        
        # Check for cancel
        if is_cancel(lower, self.lang):
            self.state.reset()
            return HandlerResult(
                handled=True,
                speak=self._msg.cancelled,
            )
        
        # Check for delete
        delete_words = {"delete", "backspace", "usuń", "cofnij"}
        if any(w in lower for w in delete_words):
            self.state.delete_last_char()
            buffer = self.state.spelling_buffer or "empty"
            return HandlerResult(
                handled=True,
                speak=self._msg.email_deleted.format(buffer=buffer),
            )
        
        # Clean and process input
        clean_text = self._clean_email_input(text)
        
        # If looks like full email, use it directly
        if "@" in clean_text and "." in clean_text:
            self.state.spelling_buffer = clean_text.replace(" ", "")
            return HandlerResult(
                handled=True,
                speak=self._msg.email_got_full.format(email=self.state.spelling_buffer),
            )
        
        # Add to buffer
        self.state.add_to_buffer(clean_text)
        return HandlerResult(
            handled=True,
            speak=self._msg.email_got.format(
                text=clean_text,
                buffer=self.state.spelling_buffer,
            ),
        )
    
    def _clean_email_input(self, text: str) -> str:
        """Clean email input, replacing spoken symbols."""
        replacements = {
            " at ": "@",
            " dot ": ".",
            "at sign": "@",
            "małpa": "@",
            "kropka": ".",
            "punkt": ".",
        }
        result = text
        for old, new in replacements.items():
            result = result.replace(old, new)
        return result


def create_handlers(state: ConversationState, lang: str = "en") -> InputHandlers:
    """Factory function to create handlers."""
    return InputHandlers(state, lang)
