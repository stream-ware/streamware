"""
Voice Mouse Component for Streamware

Control mouse with voice commands + AI vision
"Kliknij w button zatwierdź" -> AI finds button -> Click!
"""

import os
import re
import time
import subprocess
from typing import Any, Dict, Optional, Tuple
from ..core import Component, register
from ..uri import StreamwareURI
from ..exceptions import ComponentError
from ..diagnostics import get_logger

logger = get_logger(__name__)


@register("voice_mouse")
@register("voice_click")
class VoiceMouseComponent(Component):
    """
    Voice-controlled mouse with AI vision
    
    Operations:
    - click: Voice command -> AI finds element -> Click
    - move: Voice command -> AI finds element -> Move
    - listen_and_click: Continuous listening and clicking
    
    URI Examples:
        voice_mouse://click?command=kliknij w button zatwierdź
        voice_mouse://click?command=click approve button
        voice_mouse://listen_and_click?iterations=10
    """
    
    input_mime = "*/*"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.operation = uri.operation or "click"
        
        # Voice command
        self.command = uri.get_param("command", "")
        self.language = uri.get_param("language", "pl")  # pl or en
        
        # Behavior
        self.iterations = int(uri.get_param("iterations", 1))
        self.delay = float(uri.get_param("delay", 2.0))
        self.confirm = uri.get_param("confirm", True)  # Speak before clicking
        
        # Screenshot for AI
        self.screenshot_path = uri.get_param("screenshot", "/tmp/voice_mouse_screen.png")
    
    def process(self, data: Any) -> Dict:
        """Process voice mouse operation"""
        operations = {
            "click": self._voice_click,
            "move": self._voice_move,
            "listen_and_click": self._listen_and_click,
        }
        
        operation_func = operations.get(self.operation)
        if not operation_func:
            raise ComponentError(f"Unknown operation: {self.operation}")
        
        return operation_func(data)
    
    def _voice_click(self, data: Any) -> Dict:
        """Voice command -> AI find -> Click"""
        from ..core import flow
        
        # 1. Get voice command if not provided
        if not self.command:
            logger.info("Listening for voice command...")
            try:
                listen_result = flow(f"voice://listen?language={self.language}").run()
                self.command = listen_result.get("text", "")
                logger.info(f"Heard: {self.command}")
            except Exception as e:
                raise ComponentError(f"Voice recognition failed: {e}")
        
        if not self.command:
            raise ComponentError("No voice command received")
        
        # 2. Extract what to click from command
        target = self._extract_target(self.command)
        logger.info(f"Target to click: {target}")
        
        # 3. Take screenshot
        logger.info("Taking screenshot...")
        screenshot_result = flow(f"automation://screenshot?text={self.screenshot_path}").run()
        
        if not screenshot_result.get("success"):
            raise ComponentError("Screenshot failed")
        
        # 4. Use AI to find the target
        logger.info(f"Finding '{target}' with AI...")
        coords = self._find_element_with_ai(target, self.screenshot_path)
        
        if not coords:
            return {
                "success": False,
                "error": f"Could not find '{target}' on screen",
                "command": self.command
            }
        
        x, y = coords
        logger.info(f"Found '{target}' at ({x}, {y})")
        
        # 5. Confirm with voice (optional)
        if self.confirm:
            try:
                flow(f"voice://speak?text=Klikam w {target}").run()
            except Exception:
                pass  # Voice confirmation optional
        
        # 6. Click!
        time.sleep(0.5)  # Small delay
        
        # Use xdotool for clicking (more reliable than pyautogui)
        try:
            subprocess.run(['xdotool', 'mousemove', str(x), str(y)], timeout=5)
            subprocess.run(['xdotool', 'click', '1'], timeout=5)
            
            return {
                "success": True,
                "command": self.command,
                "target": target,
                "x": x,
                "y": y,
                "method": "xdotool"
            }
        except FileNotFoundError:
            # Fallback to pyautogui
            try:
                import pyautogui
                pyautogui.click(x, y)
                
                return {
                    "success": True,
                    "command": self.command,
                    "target": target,
                    "x": x,
                    "y": y,
                    "method": "pyautogui"
                }
            except Exception as e:
                raise ComponentError(f"Click failed: {e}. Install xdotool: sudo apt-get install xdotool")
    
    def _voice_move(self, data: Any) -> Dict:
        """Voice command -> AI find -> Move mouse"""
        from ..core import flow
        
        # Similar to click but only move
        if not self.command:
            listen_result = flow(f"voice://listen?language={self.language}").run()
            self.command = listen_result.get("text", "")
        
        target = self._extract_target(self.command)
        screenshot_result = flow(f"automation://screenshot?text={self.screenshot_path}").run()
        
        if not screenshot_result.get("success"):
            raise ComponentError("Screenshot failed")
        
        coords = self._find_element_with_ai(target, self.screenshot_path)
        
        if not coords:
            return {
                "success": False,
                "error": f"Could not find '{target}'",
                "command": self.command
            }
        
        x, y = coords
        
        # Move mouse
        try:
            subprocess.run(['xdotool', 'mousemove', str(x), str(y)], timeout=5)
            return {
                "success": True,
                "command": self.command,
                "target": target,
                "x": x,
                "y": y,
                "action": "move"
            }
        except FileNotFoundError:
            try:
                import pyautogui
                pyautogui.moveTo(x, y)
                return {
                    "success": True,
                    "command": self.command,
                    "target": target,
                    "x": x,
                    "y": y,
                    "action": "move"
                }
            except Exception as e:
                raise ComponentError(f"Move failed: {e}")
    
    def _listen_and_click(self, data: Any) -> Dict:
        """Continuous listening and clicking"""
        from ..core import flow
        
        results = []
        
        for i in range(self.iterations):
            logger.info(f"Iteration {i+1}/{self.iterations}")
            
            try:
                # Listen
                flow("voice://speak?text=Słucham").run()
                listen_result = flow(f"voice://listen?language={self.language}").run()
                command = listen_result.get("text", "")
                
                logger.info(f"Command: {command}")
                
                # Check for exit
                if any(word in command.lower() for word in ["stop", "koniec", "exit", "zakończ"]):
                    flow("voice://speak?text=Kończę pracę").run()
                    break
                
                # Check if it's a click command
                if any(word in command.lower() for word in ["kliknij", "click", "naciśnij", "press"]):
                    # Execute click
                    self.command = command
                    result = self._voice_click(data)
                    results.append(result)
                    
                    if result.get("success"):
                        flow("voice://speak?text=Zrobione").run()
                    else:
                        flow("voice://speak?text=Nie znalazłem tego elementu").run()
                else:
                    flow("voice://speak?text=Nie rozumiem. Powiedz kliknij w...").run()
                
            except Exception as e:
                logger.error(f"Error in iteration {i+1}: {e}")
                results.append({"success": False, "error": str(e)})
            
            time.sleep(self.delay)
        
        return {
            "success": True,
            "iterations_completed": len(results),
            "results": results
        }
    
    def _extract_target(self, command: str) -> str:
        """Extract what to click from voice command"""
        # Polish patterns
        patterns_pl = [
            r"kliknij w (.+)",
            r"kliknij na (.+)",
            r"naciśnij (.+)",
            r"wciśnij (.+)",
            r"wybierz (.+)",
        ]
        
        # English patterns
        patterns_en = [
            r"click (?:on |the )?(.+)",
            r"press (?:the )?(.+)",
            r"select (?:the )?(.+)",
            r"tap (?:on )?(.+)",
        ]
        
        command_lower = command.lower()
        
        # Try Polish patterns
        for pattern in patterns_pl:
            match = re.search(pattern, command_lower)
            if match:
                return match.group(1).strip()
        
        # Try English patterns
        for pattern in patterns_en:
            match = re.search(pattern, command_lower)
            if match:
                return match.group(1).strip()
        
        # If no pattern matched, return the whole command
        return command.strip()
    
    def _find_element_with_ai(self, target: str, screenshot_path: str) -> Optional[Tuple[int, int]]:
        """Use AI vision to find element coordinates"""
        from ..core import flow
        
        # Use LLaVA to find the element
        prompt = f"""Analyze this screenshot and find the '{target}' button or element.
        
Give me the EXACT pixel coordinates (x, y) of the CENTER of this element.

The screenshot resolution is typically 1920x1080 or similar.
Respond ONLY with coordinates in format: x,y
For example: 850,130

If you can't find the element, respond with: NOT_FOUND

Target to find: {target}
"""
        
        try:
            result = flow(
                f"media://describe_image?"
                f"file={screenshot_path}&"
                f"prompt={prompt}&"
                f"model=llava"
            ).run()
            
            if not result.get("success"):
                logger.warning("AI analysis failed")
                return None
            
            description = result.get("description", "")
            logger.info(f"AI response: {description}")
            
            # Extract coordinates
            coords = self._extract_coordinates(description)
            return coords
            
        except Exception as e:
            logger.error(f"AI vision error: {e}")
            return None
    
    def _extract_coordinates(self, text: str) -> Optional[Tuple[int, int]]:
        """Extract x,y coordinates from AI response"""
        # Check if NOT_FOUND
        if "NOT_FOUND" in text.upper() or "NOT FOUND" in text.upper():
            return None
        
        # Try various coordinate patterns
        patterns = [
            r'(\d+)\s*,\s*(\d+)',  # 850, 130
            r'x:\s*(\d+).*?y:\s*(\d+)',  # x: 850, y: 130
            r'\((\d+),\s*(\d+)\)',  # (850, 130)
            r'coordinates?:\s*(\d+)\s*,\s*(\d+)',  # coordinates: 850, 130
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                x, y = int(match.group(1)), int(match.group(2))
                # Sanity check (typical screen resolutions)
                if 0 < x < 4000 and 0 < y < 3000:
                    return (x, y)
        
        return None


# Quick helper functions
def voice_click(command: str, language: str = "pl") -> Dict:
    """Quick voice click"""
    from ..core import flow
    return flow(f"voice_mouse://click?command={command}&language={language}").run()


def listen_and_click(iterations: int = 10) -> Dict:
    """Quick continuous voice clicking"""
    from ..core import flow
    return flow(f"voice_mouse://listen_and_click?iterations={iterations}").run()
