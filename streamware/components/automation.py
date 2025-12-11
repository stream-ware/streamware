"""
Automation Component for Streamware

Control mouse and keyboard programmatically.
Automate desktop interactions with natural language!

# Menu:
- [Quick Start](#quick-start)
- [Mouse Control](#mouse-control)
- [Keyboard Control](#keyboard-control)
- [AI Automation](#ai-automation)
"""

from __future__ import annotations
import time
import subprocess
from typing import Any, Dict, List, Tuple
from ..core import Component, register
from ..uri import StreamwareURI
from ..exceptions import ComponentError
from ..diagnostics import get_logger

logger = get_logger(__name__)


@register("automation")
@register("auto")
@register("control")
class AutomationComponent(Component):
    """
    Desktop automation component
    
    Operations:
    - click: Click mouse at position
    - move: Move mouse to position
    - type: Type text
    - press: Press key
    - hotkey: Press key combination
    - automate: AI-powered automation from text
    
    URI Examples:
        automation://click?x=100&y=200
        automation://move?x=500&y=300
        automation://type?text=Hello World
        automation://press?key=enter
        automation://hotkey?keys=ctrl+c
        automation://automate?task=click the submit button
    """
    
    input_mime = "*/*"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.operation = uri.operation or "click"
        
        # Mouse parameters
        self.x = uri.get_param("x")
        self.y = uri.get_param("y")
        self.button = uri.get_param("button", "left")
        self.clicks = int(uri.get_param("clicks", 1))
        
        # Keyboard parameters
        self.text = uri.get_param("text")
        self.key = uri.get_param("key")
        self.keys = uri.get_param("keys")
        
        # Automation task
        self.task = uri.get_param("task")
        
        # Options
        self.duration = float(uri.get_param("duration", 0.25))
        self.interval = float(uri.get_param("interval", 0.1))
        self.auto_install = uri.get_param("auto_install", True)
    
    def process(self, data: Any) -> Dict:
        """Process automation operation"""
        if self.auto_install:
            self._ensure_dependencies()
        
        operations = {
            "click": self._click,
            "move": self._move,
            "type": self._type_text,
            "press": self._press_key,
            "hotkey": self._hotkey,
            "automate": self._automate_task,
            "screenshot": self._screenshot,
        }
        
        operation_func = operations.get(self.operation)
        if not operation_func:
            raise ComponentError(f"Unknown operation: {self.operation}")
        
        return operation_func(data)
    
    def _ensure_dependencies(self):
        """Ensure dependencies are available (pyautogui or scrot)"""
        # Check if scrot is available (preferred for screenshots)
        try:
            result = subprocess.run(['which', 'scrot'], capture_output=True, timeout=2)
            if result.returncode == 0:
                logger.info("scrot available for screenshots")
                return  # scrot works, no need for pyautogui
        except Exception:
            pass
        
        # Try to import pyautogui if scrot not available
        try:
            import pyautogui
            # Set failsafe to False to avoid issues
            pyautogui.FAILSAFE = False
            logger.info("pyautogui available")
        except ImportError:
            # Neither scrot nor pyautogui available
            logger.warning(
                "No automation tools found. For best results, install:\n"
                "  sudo apt-get install scrot  (recommended)\n"
                "  OR pip install pyautogui Pillow"
            )
            # Don't fail here - let specific operations fail if needed
        except Exception as e:
            # Catch display connection errors but don't fail
            if "display" in str(e).lower() or "authorization" in str(e).lower():
                logger.warning(f"Display connection issue: {e}")
            else:
                logger.warning(f"pyautogui import issue: {e}")
    
    def _click(self, data: Any) -> Dict:
        """Click mouse at position using xdotool (preferred) or pyautogui"""
        if self.x is None or self.y is None:
            raise ComponentError("x and y coordinates required")
        
        x, y = int(self.x), int(self.y)
        logger.info(f"Clicking at ({x}, {y})")
        
        # Try xdotool first (more reliable, no display auth issues)
        try:
            import subprocess
            # Move mouse and click
            subprocess.run(['xdotool', 'mousemove', str(x), str(y)], timeout=5, check=True)
            click_cmd = ['xdotool', 'click', '1' if self.button == 'left' else '3']
            for _ in range(self.clicks):
                subprocess.run(click_cmd, timeout=5, check=True)
            return {"success": True, "action": "click", "x": x, "y": y, "button": self.button, "clicks": self.clicks, "method": "xdotool"}
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass
        
        # Fallback to pyautogui
        try:
            import pyautogui
            pyautogui.click(x, y, clicks=self.clicks, button=self.button, duration=self.duration)
            return {"success": True, "action": "click", "x": x, "y": y, "button": self.button, "clicks": self.clicks, "method": "pyautogui"}
        except ImportError:
            raise ComponentError("No click tool available. Install: sudo apt-get install xdotool OR pip install pyautogui")
        except Exception as e:
            raise ComponentError(f"Click failed: {e}. Try: sudo apt-get install xdotool")
    
    def _move(self, data: Any) -> Dict:
        """Move mouse to position using xdotool (preferred) or pyautogui"""
        if self.x is None or self.y is None:
            raise ComponentError("x and y coordinates required")
        
        x, y = int(self.x), int(self.y)
        logger.info(f"Moving to ({x}, {y})")
        
        # Try xdotool first
        try:
            import subprocess
            subprocess.run(['xdotool', 'mousemove', str(x), str(y)], timeout=5, check=True)
            return {"success": True, "action": "move", "x": x, "y": y, "method": "xdotool"}
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass
        
        # Fallback to pyautogui
        try:
            import pyautogui
            pyautogui.moveTo(x, y, duration=self.duration)
            return {"success": True, "action": "move", "x": x, "y": y, "method": "pyautogui"}
        except ImportError:
            raise ComponentError("No mouse tool available. Install: sudo apt-get install xdotool OR pip install pyautogui")
        except Exception as e:
            raise ComponentError(f"Move failed: {e}")
    
    def _type_text(self, data: Any) -> Dict:
        """Type text using xdotool (preferred) or pyautogui"""
        text = self.text or str(data)
        if not text:
            raise ComponentError("Text required")
        
        logger.info(f"Typing: {text}")
        
        # Try xdotool first (more reliable, no display issues)
        try:
            import subprocess
            subprocess.run(['xdotool', 'type', '--', text], timeout=10, check=True)
            return {"success": True, "action": "type", "text": text, "method": "xdotool"}
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass
        
        # Fallback to pyautogui
        try:
            import pyautogui
            pyautogui.typewrite(text, interval=self.interval)
            return {"success": True, "action": "type", "text": text, "method": "pyautogui"}
        except ImportError:
            raise ComponentError("No typing tool available. Install: sudo apt-get install xdotool OR pip install pyautogui")
        except Exception as e:
            raise ComponentError(f"Typing failed: {e}. Try: sudo apt-get install xdotool")
    
    def _press_key(self, data: Any) -> Dict:
        """Press a key using xdotool (preferred) or pyautogui"""
        if not self.key:
            raise ComponentError("Key required")
        
        logger.info(f"Pressing key: {self.key}")
        
        # Try xdotool first
        try:
            import subprocess
            subprocess.run(['xdotool', 'key', self.key], timeout=5, check=True)
            return {"success": True, "action": "press", "key": self.key, "method": "xdotool"}
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass
        
        # Fallback to pyautogui
        try:
            import pyautogui
            pyautogui.press(self.key)
            return {"success": True, "action": "press", "key": self.key, "method": "pyautogui"}
        except ImportError:
            raise ComponentError("No key press tool available. Install: sudo apt-get install xdotool OR pip install pyautogui")
        except Exception as e:
            raise ComponentError(f"Key press failed: {e}")
    
    def _hotkey(self, data: Any) -> Dict:
        """Press key combination using xdotool (preferred) or pyautogui"""
        if not self.keys:
            raise ComponentError("Keys required")
        
        # URLs often decode "+" as space, so support both separators
        raw = self.keys.replace(" ", "+")
        keys_list = [k for k in raw.split("+") if k]
        
        logger.info(f"Pressing hotkey: {self.keys}")
        
        # Try xdotool first
        try:
            import subprocess
            xdotool_keys = "+".join(keys_list)
            subprocess.run(['xdotool', 'key', xdotool_keys], timeout=5, check=True)
            return {"success": True, "action": "hotkey", "keys": keys_list, "method": "xdotool"}
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass
        
        # Fallback to pyautogui
        try:
            import pyautogui
            pyautogui.hotkey(*keys_list)
            return {"success": True, "action": "hotkey", "keys": keys_list, "method": "pyautogui"}
        except ImportError:
            raise ComponentError("No hotkey tool available. Install: sudo apt-get install xdotool OR pip install pyautogui")
        except Exception as e:
            raise ComponentError(f"Hotkey failed: {e}")
    
    def _screenshot(self, data: Any) -> Dict:
        """Take screenshot using scrot or pyautogui"""
        output = self.text or "screenshot.png"
        
        # Method 1: Try scrot (most reliable)
        try:
            logger.info(f"Taking screenshot with scrot: {output}")
            result = subprocess.run(['scrot', output], capture_output=True, timeout=10)
            if result.returncode == 0:
                from pathlib import Path
                if Path(output).exists():
                    return {
                        "success": True,
                        "action": "screenshot",
                        "file": output,
                        "method": "scrot"
                    }
        except FileNotFoundError:
            logger.debug("scrot not found")
        except Exception as e:
            logger.debug(f"scrot failed: {e}")
        
        # Method 2: Fallback to pyautogui
        try:
            import pyautogui
            logger.info(f"Taking screenshot with pyautogui: {output}")
            screenshot = pyautogui.screenshot()
            screenshot.save(output)
            return {
                "success": True,
                "action": "screenshot",
                "file": output,
                "method": "pyautogui"
            }
        except ImportError:
            raise ComponentError(
                "No screenshot tool available. Install:\n"
                "  sudo apt-get install scrot  (recommended)\n"
                "  OR pip install pyautogui Pillow"
            )
        except Exception as e:
            raise ComponentError(f"Screenshot failed: {e}")
    
    def _automate_task(self, data: Any) -> Dict:
        """AI-powered automation from natural language"""
        if not self.task:
            raise ComponentError("Task description required")
        
        logger.info(f"Automating task: {self.task}")
        
        # Use LLM to convert task to actions
        try:
            from ..core import flow
            
            prompt = f"""Convert this task to automation actions:
Task: {self.task}

Available actions:
- move(x, y) - Move mouse
- click(x, y) - Click at position
- type(text) - Type text
- press(key) - Press key (enter, tab, etc)
- hotkey(key1+key2) - Press key combination

Respond with Python code using these functions.
Example: click(100, 200); type('hello'); press('enter')
"""
            
            result = flow(f"llm://generate?prompt={prompt}").run()
            
            # Extract and execute actions
            actions = self._parse_actions(result)
            executed = []
            
            for action in actions:
                action_result = self._execute_action(action)
                executed.append(action_result)
                time.sleep(0.5)  # Small delay between actions
            
            return {
                "success": True,
                "task": self.task,
                "actions": executed,
                "count": len(executed)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _parse_actions(self, text: str) -> List[Dict]:
        """Parse actions from text"""
        import re
        
        actions = []
        
        # Extract function calls
        patterns = [
            r'move\((\d+),\s*(\d+)\)',
            r'click\((\d+),\s*(\d+)\)',
            r'type\([\'"](.+?)[\'"]\)',
            r'press\([\'"](.+?)[\'"]\)',
            r'hotkey\([\'"](.+?)[\'"]\)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if 'move' in pattern:
                    actions.append({"type": "move", "x": int(match[0]), "y": int(match[1])})
                elif 'click' in pattern:
                    actions.append({"type": "click", "x": int(match[0]), "y": int(match[1])})
                elif 'type' in pattern:
                    actions.append({"type": "type", "text": match})
                elif 'press' in pattern:
                    actions.append({"type": "press", "key": match})
                elif 'hotkey' in pattern:
                    actions.append({"type": "hotkey", "keys": match})
        
        return actions
    
    def _execute_action(self, action: Dict) -> Dict:
        """Execute a single action"""
        import pyautogui
        
        action_type = action.get("type")
        
        if action_type == "move":
            pyautogui.moveTo(action["x"], action["y"], duration=self.duration)
            return {"action": "move", "x": action["x"], "y": action["y"]}
        
        elif action_type == "click":
            pyautogui.click(action["x"], action["y"], duration=self.duration)
            return {"action": "click", "x": action["x"], "y": action["y"]}
        
        elif action_type == "type":
            pyautogui.typewrite(action["text"], interval=self.interval)
            return {"action": "type", "text": action["text"]}
        
        elif action_type == "press":
            pyautogui.press(action["key"])
            return {"action": "press", "key": action["key"]}
        
        elif action_type == "hotkey":
            keys = action["keys"].split("+")
            pyautogui.hotkey(*keys)
            return {"action": "hotkey", "keys": keys}
        
        return {"action": "unknown"}


# Quick helpers
def click(x: int, y: int) -> Dict:
    """Quick mouse click"""
    from ..core import flow
    return flow(f"automation://click?x={x}&y={y}").run()


def type_text(text: str) -> Dict:
    """Quick type text"""
    from ..core import flow
    return flow(f"automation://type?text={text}").run()


def automate(task: str) -> Dict:
    """Quick AI automation"""
    from ..core import flow
    return flow(f"automation://automate?task={task}").run()
