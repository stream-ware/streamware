"""
Voice Keyboard Component for Streamware

Control keyboard with voice commands
"Wpisz hello world" -> Types "hello world"
"Naciśnij enter" -> Presses enter key
"""

import re
import time
import subprocess
from typing import Any, Dict, Optional
from ..core import Component, register
from ..uri import StreamwareURI
from ..exceptions import ComponentError
from ..diagnostics import get_logger

logger = get_logger(__name__)


@register("voice_keyboard")
@register("voice_type")
class VoiceKeyboardComponent(Component):
    """
    Voice-controlled keyboard
    
    Operations:
    - type: Voice "wpisz tekst" -> types text
    - press: Voice "naciśnij enter" -> presses key
    - listen_and_type: Continuous dictation
    
    URI Examples:
        voice_keyboard://type?command=wpisz hello world
        voice_keyboard://press?command=naciśnij enter
        voice_keyboard://listen_and_type?iterations=10
    """
    
    input_mime = "*/*"
    output_mime = "application/json"
    
    # Key mappings
    KEY_MAP = {
        # Polish
        "enter": "Return",
        "spacja": "space",
        "backspace": "BackSpace",
        "delete": "Delete",
        "tab": "Tab",
        "escape": "Escape",
        "strzałka w górę": "Up",
        "strzałka w dół": "Down",
        "strzałka w lewo": "Left",
        "strzałka w prawo": "Right",
        "góra": "Up",
        "dół": "Down",
        "lewo": "Left",
        "prawo": "Right",
        
        # English
        "space": "space",
        "up": "Up",
        "down": "Down",
        "left": "Left",
        "right": "Right",
        "shift": "shift",
        "control": "ctrl",
        "ctrl": "ctrl",
        "alt": "alt",
    }
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        # Extract operation from path (remove leading slashes and scheme)
        operation = uri.operation or uri.path or "type"
        # Clean up operation name
        self.operation = operation.strip('/').replace('voice_keyboard://', '').replace('voice_type://', '')
        
        # Voice command
        self.command = uri.get_param("command", "")
        self.language = uri.get_param("language", "pl")
        
        # Behavior
        self.iterations = int(uri.get_param("iterations", 1))
        self.delay = float(uri.get_param("delay", 1.0))
        self.confirm = uri.get_param("confirm", True)
    
    def process(self, data: Any) -> Dict:
        """Process voice keyboard operation"""
        operations = {
            "type": self._voice_type,
            "press": self._voice_press,
            "listen_and_type": self._listen_and_type,
        }
        
        operation_func = operations.get(self.operation)
        if not operation_func:
            raise ComponentError(f"Unknown operation: {self.operation}")
        
        return operation_func(data)
    
    def _voice_type(self, data: Any) -> Dict:
        """Voice -> extract text -> type it"""
        from ..core import flow
        
        # 1. Get voice command if not provided
        if not self.command:
            logger.info("Listening for typing command...")
            try:
                listen_result = flow(f"voice://listen?language={self.language}").run()
                self.command = listen_result.get("text", "")
                logger.info(f"Heard: {self.command}")
            except Exception as e:
                raise ComponentError(f"Voice recognition failed: {e}")
        
        if not self.command:
            raise ComponentError("No voice command received")
        
        # 2. Extract text to type
        text_to_type = self._extract_text_to_type(self.command)
        
        if not text_to_type:
            return {
                "success": False,
                "error": "Could not extract text to type",
                "command": self.command
            }
        
        logger.info(f"Text to type: '{text_to_type}'")
        
        # 3. Confirm (optional)
        if self.confirm:
            try:
                flow(f"voice://speak?text=Wpisuję {text_to_type}").run()
            except Exception:
                pass
        
        # 4. Type it!
        time.sleep(0.5)
        success = self._type_text(text_to_type)
        
        return {
            "success": success,
            "command": self.command,
            "typed": text_to_type
        }
    
    def _voice_press(self, data: Any) -> Dict:
        """Voice -> extract key -> press it"""
        from ..core import flow
        
        # 1. Get voice command
        if not self.command:
            listen_result = flow(f"voice://listen?language={self.language}").run()
            self.command = listen_result.get("text", "")
        
        # 2. Extract key to press
        key = self._extract_key_to_press(self.command)
        
        if not key:
            return {
                "success": False,
                "error": "Could not extract key to press",
                "command": self.command
            }
        
        logger.info(f"Key to press: {key}")
        
        # 3. Confirm
        if self.confirm:
            try:
                flow(f"voice://speak?text=Naciskam {key}").run()
            except Exception:
                pass
        
        # 4. Press it!
        time.sleep(0.5)
        success = self._press_key(key)
        
        return {
            "success": success,
            "command": self.command,
            "key": key
        }
    
    def _listen_and_type(self, data: Any) -> Dict:
        """Continuous dictation"""
        from ..core import flow
        
        results = []
        
        logger.info("Starting continuous dictation...")
        
        if self.confirm:
            try:
                flow("voice://speak?text=Dyktuj. Powiedz stop aby zakończyć.").run()
            except Exception:
                pass
        
        for i in range(self.iterations):
            logger.info(f"Dictation {i+1}/{self.iterations}")
            
            try:
                # Listen
                listen_result = flow(f"voice://listen?language={self.language}").run()
                text = listen_result.get("text", "")
                
                logger.info(f"Heard: {text}")
                
                # Check for stop
                if any(word in text.lower() for word in ["stop", "koniec", "zakończ", "exit"]):
                    if self.confirm:
                        flow("voice://speak?text=Kończę dyktowanie").run()
                    break
                
                # Check for special commands
                if "naciśnij" in text.lower() or "press" in text.lower():
                    # It's a key press command
                    self.command = text
                    result = self._voice_press(data)
                    results.append(result)
                elif "wpisz" in text.lower() or "type" in text.lower():
                    # It's a type command
                    self.command = text
                    result = self._voice_type(data)
                    results.append(result)
                else:
                    # Just type what was said
                    success = self._type_text(text)
                    results.append({
                        "success": success,
                        "typed": text
                    })
                
            except Exception as e:
                logger.error(f"Error in iteration {i+1}: {e}")
                results.append({"success": False, "error": str(e)})
            
            time.sleep(self.delay)
        
        return {
            "success": True,
            "iterations_completed": len(results),
            "results": results
        }
    
    def _extract_text_to_type(self, command: str) -> Optional[str]:
        """Extract text to type from voice command"""
        # Polish patterns
        patterns_pl = [
            r"wpisz\s+(.+)",
            r"napisz\s+(.+)",
            r"wprowadź\s+(.+)",
        ]
        
        # English patterns
        patterns_en = [
            r"type\s+(.+)",
            r"write\s+(.+)",
            r"enter\s+(.+)",
        ]
        
        command_lower = command.lower()
        
        # Try Polish
        for pattern in patterns_pl:
            match = re.search(pattern, command_lower)
            if match:
                return match.group(1).strip()
        
        # Try English
        for pattern in patterns_en:
            match = re.search(pattern, command_lower)
            if match:
                return match.group(1).strip()
        
        # If no pattern, maybe it's just text to type
        # But be careful - don't type commands themselves
        if not any(word in command_lower for word in ["naciśnij", "press", "kliknij", "click"]):
            return command.strip()
        
        return None
    
    def _extract_key_to_press(self, command: str) -> Optional[str]:
        """Extract key to press from voice command"""
        # Polish patterns
        patterns_pl = [
            r"naciśnij\s+(.+)",
            r"wciśnij\s+(.+)",
            r"przyciśnij\s+(.+)",
        ]
        
        # English patterns
        patterns_en = [
            r"press\s+(.+)",
            r"hit\s+(.+)",
            r"push\s+(.+)",
        ]
        
        command_lower = command.lower()
        
        # Try patterns
        for pattern in patterns_pl + patterns_en:
            match = re.search(pattern, command_lower)
            if match:
                key_name = match.group(1).strip()
                # Map to actual key
                return self.KEY_MAP.get(key_name, key_name)
        
        return None
    
    def _type_text(self, text: str) -> bool:
        """Type text using xdotool"""
        try:
            # Try xdotool first (most reliable)
            subprocess.run(
                ['xdotool', 'type', '--', text],
                timeout=10,
                check=True
            )
            logger.info(f"Typed with xdotool: {text}")
            return True
        except FileNotFoundError:
            # Fallback to pyautogui
            try:
                import pyautogui
                pyautogui.write(text)
                logger.info(f"Typed with pyautogui: {text}")
                return True
            except Exception as e:
                logger.error(f"Typing failed: {e}")
                raise ComponentError(
                    "No typing tool available. Install:\n"
                    "  sudo apt-get install xdotool\n"
                    "  OR pip install pyautogui"
                )
        except Exception as e:
            logger.error(f"Typing error: {e}")
            return False
    
    def _press_key(self, key: str) -> bool:
        """Press a key using xdotool"""
        try:
            # Try xdotool
            subprocess.run(
                ['xdotool', 'key', key],
                timeout=5,
                check=True
            )
            logger.info(f"Pressed key with xdotool: {key}")
            return True
        except FileNotFoundError:
            # Fallback to pyautogui
            try:
                import pyautogui
                pyautogui.press(key.lower())
                logger.info(f"Pressed key with pyautogui: {key}")
                return True
            except Exception as e:
                logger.error(f"Key press failed: {e}")
                raise ComponentError(f"Could not press key '{key}'. Install xdotool.")
        except Exception as e:
            logger.error(f"Key press error: {e}")
            return False


# Quick helper functions
def voice_type(command: str, language: str = "pl") -> Dict:
    """Quick voice typing"""
    from ..core import flow
    return flow(f"voice_keyboard://type?command={command}&language={language}").run()


def voice_press(command: str) -> Dict:
    """Quick voice key press"""
    from ..core import flow
    return flow(f"voice_keyboard://press?command={command}").run()


def dictate(iterations: int = 10) -> Dict:
    """Quick dictation mode"""
    from ..core import flow
    return flow(f"voice_keyboard://listen_and_type?iterations={iterations}").run()
