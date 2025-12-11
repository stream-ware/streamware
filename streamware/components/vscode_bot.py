"""
VSCode Bot Component for Streamware

Automate VSCode work: click buttons, generate prompts, recognize UI, commit changes.
Your AI pair programmer that never sleeps!

# Menu:
- [Quick Start](#quick-start)
- [Features](#features)
- [Examples](#examples)
"""

from __future__ import annotations
import os
import time
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from ..core import Component, register
from ..uri import StreamwareURI
from ..exceptions import ComponentError
from ..diagnostics import get_logger

logger = get_logger(__name__)


@register("vscode")
@register("bot")
@register("ai_assistant")
class VSCodeBotComponent(Component):
    """
    VSCode automation bot with AI
    
    Operations:
    - click_button: Click VSCode UI buttons (Accept, Reject, Run, etc.)
    - find_button: Find button coordinates using AI vision
    - generate_prompt: Generate next prompt for AI assistant
    - commit_changes: Git commit and push changes
    - accept_changes: Accept all pending changes
    - reject_changes: Reject all pending changes
    - continue_work: Continue autonomous work
    - watch: Watch for changes and respond
    
    URI Examples:
        vscode://click_button?button=accept_all
        vscode://find_button?name=Run&screenshot=vscode.png
        vscode://generate_prompt?context=fix_tests
        vscode://commit_changes?message=Auto commit
        vscode://continue_work?iterations=5
    """
    
    input_mime = "*/*"
    output_mime = "application/json"
    
    # Known button patterns and typical locations
    BUTTON_PATTERNS = {
        "accept_all": {
            "text": ["Accept all", "Accept All"],
            "typical_location": (870, 130),
            "search_area": (800, 100, 900, 150)
        },
        "reject_all": {
            "text": ["Reject all", "Reject All"],
            "typical_location": (800, 130),
            "search_area": (750, 100, 850, 150)
        },
        "run": {
            "text": ["Run", "Run Alt"],
            "typical_location": (760, 65),
            "search_area": (700, 50, 800, 80)
        },
        "skip": {
            "text": ["Skip"],
            "typical_location": (820, 65),
            "search_area": (800, 50, 850, 80)
        },
        "continue": {
            "text": ["Continue", "Code"],
            "typical_location": (845, 208),
            "search_area": (800, 190, 900, 220)
        }
    }
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.operation = uri.operation or "continue_work"
        
        # Button operation
        self.button = uri.get_param("button", "accept_all")
        self.screenshot = uri.get_param("screenshot")
        
        # Prompt generation
        self.context = uri.get_param("context", "")
        self.task = uri.get_param("task", "continue development")
        
        # Git operations
        self.commit_message = uri.get_param("message", "Auto commit by VSCode bot")
        self.branch = uri.get_param("branch")
        self.push = uri.get_param("push", True)
        
        # Work parameters
        self.iterations = int(uri.get_param("iterations", 1))
        self.delay = float(uri.get_param("delay", 2.0))
        self.auto_commit = uri.get_param("auto_commit", True)
        
        # Workspace
        self.workspace = uri.get_param("workspace", os.getcwd())
    
    def process(self, data: Any) -> Dict:
        """Process bot operation"""
        operations = {
            "click_button": self._click_button,
            "find_button": self._find_button,
            "generate_prompt": self._generate_prompt,
            "commit_changes": self._commit_changes,
            "accept_changes": self._accept_changes,
            "reject_changes": self._reject_changes,
            "continue_work": self._continue_work,
            "watch": self._watch_and_respond,
        }
        
        operation_func = operations.get(self.operation)
        if not operation_func:
            raise ComponentError(f"Unknown operation: {self.operation}")
        
        return operation_func(data)
    
    def _click_button(self, data: Any) -> Dict:
        """Click a specific button in VSCode"""
        from ..core import flow
        
        logger.info(f"Clicking button: {self.button}")
        
        # Get button info
        if self.button not in self.BUTTON_PATTERNS:
            return self._find_and_click_custom_button(self.button)
        
        button_info = self.BUTTON_PATTERNS[self.button]
        x, y = button_info["typical_location"]
        
        # Take screenshot and verify location
        if self.screenshot or True:  # Always verify
            screenshot_path = self.screenshot or "/tmp/vscode_screen.png"
            
            # Screenshot
            screenshot_result = flow(f"automation://screenshot?text={screenshot_path}").run()
            
            if screenshot_result.get("success"):
                # Find exact button location with AI
                found = self._find_button_in_screenshot(screenshot_path, self.button)
                if found.get("success"):
                    x = found.get("x", x)
                    y = found.get("y", y)
        
        # Click
        time.sleep(0.5)
        click_result = flow(f"automation://click?x={x}&y={y}").run()
        
        return {
            "success": click_result.get("success", False),
            "button": self.button,
            "x": x,
            "y": y
        }
    
    def _find_button(self, data: Any) -> Dict:
        """Find button coordinates using AI vision"""
        from ..core import flow
        
        if not self.screenshot:
            # Take screenshot first
            self.screenshot = "/tmp/vscode_find.png"
            flow(f"automation://screenshot?text={self.screenshot}").run()
        
        # Use AI to find button
        prompt = f"Find the '{self.button}' button in this VSCode interface. Give exact x,y pixel coordinates of the center of the button."
        
        result = flow(f"media://describe_image?file={self.screenshot}&prompt={prompt}&model=llava").run()
        
        if result.get("success"):
            description = result.get("description", "")
            
            # Try to extract coordinates from description
            coords = self._extract_coordinates(description)
            
            return {
                "success": coords is not None,
                "button": self.button,
                "x": coords[0] if coords else None,
                "y": coords[1] if coords else None,
                "description": description
            }
        
        return {"success": False, "error": "Could not analyze screenshot"}
    
    def _generate_prompt(self, data: Any) -> Dict:
        """Generate next prompt for AI assistant"""
        from ..core import flow
        
        # Analyze current state
        git_status = self._get_git_status()
        recent_changes = self._get_recent_changes()
        test_results = self._get_test_results()
        
        # Build context
        context_text = f"""
Current Task: {self.task}
Context: {self.context}

Git Status:
{git_status}

Recent Changes:
{recent_changes}

Test Results:
{test_results}

Generate the next development task prompt.
"""
        
        # Use LLM to generate prompt
        result = flow(f"llm://generate?prompt={context_text}&provider=ollama&model=qwen2.5:14b").run()
        
        return {
            "success": True,
            "prompt": str(result),
            "context": {
                "git_status": git_status,
                "test_results": test_results
            }
        }
    
    def _commit_changes(self, data: Any) -> Dict:
        """Commit changes to git"""
        os.chdir(self.workspace)
        
        try:
            # Check if there are changes
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True
            )
            
            if not status.stdout.strip():
                return {
                    "success": True,
                    "message": "No changes to commit",
                    "committed": False
                }
            
            # Add all changes
            subprocess.run(["git", "add", "."], check=True)
            
            # Commit
            commit_result = subprocess.run(
                ["git", "commit", "-m", self.commit_message],
                capture_output=True,
                text=True,
                check=True
            )
            
            committed = True
            
            # Push if requested
            if self.push:
                if self.branch:
                    subprocess.run(["git", "push", "origin", self.branch], check=True)
                else:
                    subprocess.run(["git", "push"], check=True)
            
            return {
                "success": True,
                "message": self.commit_message,
                "committed": True,
                "pushed": self.push,
                "output": commit_result.stdout
            }
            
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": str(e),
                "output": e.stderr if hasattr(e, 'stderr') else str(e)
            }
    
    def _accept_changes(self, data: Any) -> Dict:
        """Accept all pending changes in VSCode"""
        return self._click_button({"button": "accept_all"})
    
    def _reject_changes(self, data: Any) -> Dict:
        """Reject all pending changes"""
        return self._click_button({"button": "reject_all"})
    
    def _continue_work(self, data: Any) -> Dict:
        """Continue autonomous work for N iterations"""
        from ..core import flow
        
        results = []
        
        for i in range(self.iterations):
            logger.info(f"Iteration {i+1}/{self.iterations}")
            
            iteration_result = {
                "iteration": i + 1,
                "steps": []
            }
            
            # Step 1: Take screenshot
            screenshot_path = f"/tmp/vscode_iter_{i}.png"
            screen_result = flow(f"automation://screenshot?text={screenshot_path}").run()
            iteration_result["steps"].append({"screenshot": screen_result})
            
            # Step 2: Analyze what to do
            analysis = flow(
                f"media://describe_image?file={screenshot_path}"
                f"&prompt=What actions should I take in this VSCode interface? "
                f"Are there buttons to click like Accept/Reject/Run/Skip?"
                "&model=llava"
            ).run()
            
            iteration_result["steps"].append({"analysis": analysis})
            
            # Step 3: Decide action based on analysis
            description = analysis.get("description", "").lower()
            
            action_taken = None
            
            if "accept" in description and "all" in description:
                # Click Accept All
                click_result = self._click_button({"button": "accept_all"})
                action_taken = "accept_all"
                iteration_result["steps"].append({"action": "accept_all", "result": click_result})
                time.sleep(self.delay)
            
            elif "run" in description or "execute" in description:
                # Click Run
                click_result = self._click_button({"button": "run"})
                action_taken = "run"
                iteration_result["steps"].append({"action": "run", "result": click_result})
                time.sleep(self.delay)
            
            elif "continue" in description or "code" in description:
                # Click Continue
                click_result = self._click_button({"button": "continue"})
                action_taken = "continue"
                iteration_result["steps"].append({"action": "continue", "result": click_result})
                time.sleep(self.delay)
            
            # Step 4: Generate next prompt if needed
            if not action_taken or "task" in description.lower():
                prompt_result = self._generate_prompt(data)
                iteration_result["steps"].append({"generate_prompt": prompt_result})
                
                # Type the prompt (if there's an input field)
                if prompt_result.get("success"):
                    # This would need to find the input field and type
                    pass
            
            # Step 5: Check for changes and commit
            if self.auto_commit and (i + 1) % 3 == 0:  # Every 3 iterations
                commit_result = self._commit_changes(data)
                iteration_result["steps"].append({"commit": commit_result})
            
            results.append(iteration_result)
            
            # Wait between iterations
            time.sleep(self.delay)
        
        return {
            "success": True,
            "iterations_completed": len(results),
            "results": results
        }
    
    def _watch_and_respond(self, data: Any) -> Dict:
        """Watch for changes and respond automatically"""
        from ..core import flow
        
        logger.info("Starting watch mode...")
        
        events = []
        iteration = 0
        
        while iteration < self.iterations:
            iteration += 1
            
            # Screenshot
            screenshot_path = f"/tmp/vscode_watch_{iteration}.png"
            flow(f"automation://screenshot?text={screenshot_path}").run()
            
            # Analyze
            analysis = flow(
                f"media://describe_image?file={screenshot_path}"
                f"&prompt=Describe the current state. Are there any buttons or prompts waiting for action?"
                "&model=llava"
            ).run()
            
            description = analysis.get("description", "").lower()
            
            # Respond to common patterns
            event = {"iteration": iteration, "action": None}
            
            if "accept" in description:
                self._click_button({"button": "accept_all"})
                event["action"] = "accepted_changes"
            
            elif "reject" in description:
                self._click_button({"button": "reject_all"})
                event["action"] = "rejected_changes"
            
            elif "run" in description or "execute" in description:
                self._click_button({"button": "run"})
                event["action"] = "executed_command"
            
            elif "waiting" in description or "prompt" in description:
                prompt_result = self._generate_prompt(data)
                event["action"] = "generated_prompt"
                event["prompt"] = prompt_result.get("prompt")
            
            events.append(event)
            
            time.sleep(self.delay)
        
        return {
            "success": True,
            "events_handled": len(events),
            "events": events
        }
    
    # Helper methods
    def _find_button_in_screenshot(self, screenshot_path: str, button_name: str) -> Dict:
        """Use AI to find button in screenshot"""
        from ..core import flow
        
        button_info = self.BUTTON_PATTERNS.get(button_name, {})
        text_options = button_info.get("text", [button_name])
        
        prompt = f"Find the button with text '{text_options[0]}' in this VSCode interface. Give the x,y pixel coordinates of its center."
        
        result = flow(f"media://describe_image?file={screenshot_path}&prompt={prompt}&model=llava").run()
        
        if result.get("success"):
            coords = self._extract_coordinates(result.get("description", ""))
            if coords:
                return {"success": True, "x": coords[0], "y": coords[1]}
        
        # Fallback to typical location
        if "typical_location" in button_info:
            x, y = button_info["typical_location"]
            return {"success": True, "x": x, "y": y}
        
        return {"success": False}
    
    def _find_and_click_custom_button(self, button_text: str) -> Dict:
        """Find and click a custom button by text"""
        from ..core import flow
        
        screenshot_path = "/tmp/vscode_custom.png"
        flow(f"automation://screenshot?text={screenshot_path}").run()
        
        result = self._find_button_in_screenshot(screenshot_path, button_text)
        
        if result.get("success"):
            x, y = result["x"], result["y"]
            click_result = flow(f"automation://click?x={x}&y={y}").run()
            return {
                "success": click_result.get("success"),
                "button": button_text,
                "x": x,
                "y": y
            }
        
        return {"success": False, "error": f"Could not find button: {button_text}"}
    
    def _extract_coordinates(self, text: str) -> Optional[tuple]:
        """Extract x,y coordinates from text"""
        import re
        
        # Try various patterns
        patterns = [
            r'(\d+)\s*,\s*(\d+)',
            r'x:\s*(\d+).*?y:\s*(\d+)',
            r'\((\d+),\s*(\d+)\)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return (int(match.group(1)), int(match.group(2)))
        
        return None
    
    def _get_git_status(self) -> str:
        """Get git status"""
        try:
            os.chdir(self.workspace)
            result = subprocess.run(
                ["git", "status", "--short"],
                capture_output=True,
                text=True
            )
            return result.stdout or "No changes"
        except Exception:
            return "Git not available"
    
    def _get_recent_changes(self) -> str:
        """Get recent file changes"""
        try:
            os.chdir(self.workspace)
            result = subprocess.run(
                ["git", "diff", "--stat"],
                capture_output=True,
                text=True
            )
            return result.stdout[:500] or "No recent changes"
        except Exception:
            return "No changes"
    
    def _get_test_results(self) -> str:
        """Get test results if available"""
        # Look for common test output files
        test_files = [
            ".pytest_cache/v/cache/lastfailed",
            "test-results.xml",
            ".test-results"
        ]
        
        for test_file in test_files:
            path = Path(self.workspace) / test_file
            if path.exists():
                try:
                    return path.read_text()[:300]
                except Exception:
                    pass
        
        return "No test results available"


# Quick helpers
def click_accept():
    """Quick accept all changes"""
    from ..core import flow
    return flow("vscode://click_button?button=accept_all").run()


def click_reject():
    """Quick reject all changes"""
    from ..core import flow
    return flow("vscode://click_button?button=reject_all").run()


def continue_bot(iterations: int = 5):
    """Quick continue autonomous work"""
    from ..core import flow
    return flow(f"vscode://continue_work?iterations={iterations}").run()
