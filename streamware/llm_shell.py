#!/usr/bin/env python3
"""
Interactive LLM Shell for Streamware

Live conversation mode with LLM to invoke system functions.
LLM understands all available functions and generates shell commands.

Usage:
    # Start interactive shell
    sq shell
    
    # Or directly
    python -m streamware.llm_shell
    
    # In the shell:
    > detect person and email me when found
    > track cars for 10 minutes  
    > stop
    > help
"""

import json
import os
import re
import readline
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests

from .config import config
from .function_registry import registry, get_llm_context


# =============================================================================
# LLM SHELL
# =============================================================================

@dataclass
class ShellResult:
    """Result of shell command parsing."""
    understood: bool
    function_name: Optional[str] = None
    parameters: Dict[str, Any] = None
    shell_command: Optional[str] = None
    env_vars: Dict[str, str] = None
    explanation: str = ""
    error: Optional[str] = None
    # For clarification dialogs
    options: List[tuple] = None  # [(key, description, command), ...]
    input_type: Optional[str] = None  # "email", "url", etc.
    pending_command: Optional[str] = None  # Command with {placeholder}
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}
        if self.env_vars is None:
            self.env_vars = {}
        if self.options is None:
            self.options = []


class LLMShell:
    """Interactive shell with LLM understanding."""
    
    SYSTEM_PROMPT = """You are Streamware assistant. Convert user requests to shell commands.

RESPOND ONLY WITH JSON in this exact format:
{{"understood": true, "function": "name", "shell_command": "command", "explanation": "what it does"}}

COMMANDS:
- detect: sq live narrator --mode track --focus TARGET --duration 60 --skip-checks --adaptive
- track+speak: sq live narrator --mode track --focus TARGET --duration 60 --tts --tts-diff --model llava:7b --skip-checks  
- email alert: SQ_NOTIFY_EMAIL=EMAIL sq live narrator --mode track --focus TARGET --duration 60 --skip-checks --adaptive
- stop: pkill -f 'sq watch'; pkill -f 'sq live'

EXAMPLES:
User: detect person
{{"understood": true, "function": "detect", "shell_command": "sq live narrator --mode track --focus person --duration 60 --skip-checks --adaptive", "explanation": "Detect person"}}

User: track person and speak
{{"understood": true, "function": "narrate", "shell_command": "sq live narrator --mode track --focus person --duration 60 --tts --tts-diff --model llava:7b --skip-checks", "explanation": "Track and narrate person"}}

User: email tom@x.com when person detected
{{"understood": true, "function": "notify", "shell_command": "SQ_NOTIFY_EMAIL=tom@x.com sq live narrator --mode track --focus person --duration 60 --skip-checks --adaptive", "explanation": "Detect person, email tom@x.com"}}

User: stop
{{"understood": true, "function": "stop", "shell_command": "pkill -f 'sq watch'; pkill -f 'sq live'", "explanation": "Stop all"}}

User: unknown request
{{"understood": false, "function": null, "shell_command": null, "explanation": "Unknown command"}}

{functions}
"""

    def __init__(
        self,
        model: str = "llama3.2",
        provider: str = "ollama",
        auto_execute: bool = False,
        verbose: bool = False,
        language: str = "en",
    ):
        self.model = model
        self.provider = provider
        self.auto_execute = auto_execute
        self.verbose = verbose
        self.language = language
        
        # Translator for multi-language support
        from .i18n.translations import Translator
        self.t = Translator(language)
        
        self.history: List[Tuple[str, ShellResult]] = []
        self.running_process: Optional[subprocess.Popen] = None
        
        # Context for interactive session
        self.context: Dict[str, Any] = {
            "url": config.get("SQ_DEFAULT_URL"),  # Default from .env
            "email": config.get("SQ_NOTIFY_EMAIL"),
            "duration": 60,
        }
        
        # Build system prompt with function context
        self.system_prompt = self.SYSTEM_PROMPT.format(
            functions=get_llm_context()
        )
    
    def parse(self, user_input: str) -> ShellResult:
        """Parse user input using LLM."""
        # Handle built-in commands
        lower = user_input.lower().strip()
        
        # Check if input looks like a URL (set as default source)
        if user_input.startswith(("rtsp://", "http://", "https://", "/dev/video", "/")):
            self.context["url"] = user_input
            return ShellResult(
                understood=True,
                function_name="set_url",
                explanation=f"📹 Default video source set to: {user_input}",
            )
        
        # Check if input looks like an email (set as default notification)
        if "@" in user_input and "." in user_input.split("@")[-1] and " " not in user_input:
            self.context["email"] = user_input
            return ShellResult(
                understood=True,
                function_name="set_email", 
                explanation=f"📧 Default notification email set to: {user_input}",
            )
        
        if lower in ("exit", "quit", "q"):
            return ShellResult(
                understood=True,
                function_name="exit",
                shell_command="exit",
                explanation="Exit the shell",
            )
        
        # Quick pattern matching for common commands (fallback if LLM fails)
        if "track" in lower and "speak" in lower:
            target = "person"
            if "car" in lower:
                target = "car"
            elif "animal" in lower:
                target = "animal"
            # Include language for TTS
            lang_param = f"--lang {self.language}" if hasattr(self, 'language') and self.language != 'en' else ""
            return ShellResult(
                understood=True,
                function_name="narrate",
                shell_command=f"sq live narrator --mode track --focus {target} --duration 60 --tts --tts-diff --model llava:7b --skip-checks {lang_param}".strip(),
                explanation=f"Track {target} and speak results",
            )
        
        # Track without speak - offer options
        if "track" in lower and "speak" not in lower:
            target = "person"
            if "car" in lower:
                target = "car"
            # Include language for TTS options
            lang_param = f"--lang {self.language}" if hasattr(self, 'language') and self.language != 'en' else ""
            
            # Translated target and option texts
            target_tr = self.t.translate_target(target)
            opt_tts = self.t.conv("option_tts")
            opt_silent = self.t.conv("option_silent")
            opt_email = self.t.conv("option_email")
            question = self.t.conv("how_would_you_like", action=f"{self.t.cmd('tracking')} {target_tr}")
            
            return ShellResult(
                understood=True,
                function_name="clarify",
                options=[
                    ("1", f"{self.t.cmd('tracking')} {target_tr} {opt_tts}", f"sq live narrator --mode track --focus {target} --duration 60 --tts --tts-diff --model llava:7b --skip-checks {lang_param}".strip()),
                    ("2", f"{self.t.cmd('tracking')} {target_tr} {opt_silent}", f"sq live narrator --mode track --focus {target} --duration 60 --model llava:7b --skip-checks"),
                    ("3", f"{self.t.cmd('tracking')} {target_tr} {opt_email}", "need_email"),
                ],
                explanation=question,
            )
        
        if "detect" in lower and "email" in lower:
            # Extract email
            import re
            email_match = re.search(r'[\w.+-]+@[\w.-]+\.\w+', user_input)
            email = email_match.group(0) if email_match else None
            target = "person"
            if not email:
                return ShellResult(
                    understood=True,
                    function_name="need_input",
                    input_type="email",
                    explanation="Please provide email address (you can spell it)",
                    pending_command=f"SQ_NOTIFY_EMAIL={{email}} sq live narrator --mode track --focus {target} --duration 60 --skip-checks --adaptive",
                )
            return ShellResult(
                understood=True,
                function_name="notify_email",
                shell_command=f"SQ_NOTIFY_EMAIL={email} sq live narrator --mode track --focus {target} --duration 60 --skip-checks --adaptive",
                explanation=f"Detect {target} and email {email}",
            )
        
        if lower.startswith("detect ") or lower.startswith("find "):
            target = lower.replace("detect ", "").replace("find ", "").split()[0] or "person"
            return ShellResult(
                understood=True,
                function_name="detect",
                shell_command=f"sq live narrator --mode track --focus {target} --duration 60 --skip-checks --adaptive",
                explanation=f"Detect {target}",
            )
        
        # Greeting or unclear - show options
        if lower in ("hello", "hi", "hey", "help me", "what can you do"):
            return ShellResult(
                understood=True,
                function_name="clarify",
                options=[
                    ("1", "Track person and speak", "sq live narrator --mode track --focus person --duration 60 --tts --tts-diff --model llava:7b --skip-checks"),
                    ("2", "Detect person silently", "sq live narrator --mode track --focus person --duration 60 --skip-checks --adaptive"),
                    ("3", "Detect and email me", "need_email"),
                    ("4", "Show all functions", "functions"),
                ],
                explanation="What would you like to do? Say a number:",
            )
        
        if lower == "help":
            return ShellResult(
                understood=True,
                function_name="help",
                explanation=self._get_help(),
            )
        
        if lower == "functions" or lower == "list":
            return ShellResult(
                understood=True,
                function_name="list",
                explanation=self._list_functions(),
            )
        
        if lower == "history":
            return ShellResult(
                understood=True,
                function_name="history",
                explanation=self._format_history(),
            )
        
        if lower in ("context", "status", "settings"):
            return ShellResult(
                understood=True,
                function_name="context",
                explanation=self._format_context(),
            )
        
        if lower == "stop":
            return ShellResult(
                understood=True,
                function_name="stop",
                shell_command="pkill -f 'sq watch' 2>/dev/null || echo 'Nothing running'",
                explanation="Stop all detection processes",
            )
        
        # Use LLM to parse
        return self._parse_with_llm(user_input)
    
    def _parse_with_llm(self, user_input: str) -> ShellResult:
        """Use LLM to parse user input."""
        prompt = f"""User request: "{user_input}"

Remember to respond with only valid JSON."""
        
        try:
            if self.provider == "ollama":
                response = self._call_ollama(prompt)
            else:
                response = self._call_openai(prompt)
            
            if self.verbose:
                print(f"[LLM Response]: {response}")
            
            # Parse JSON response
            data = json.loads(response)
            
            # Handle nested response from some models
            if "response" in data and isinstance(data["response"], str):
                try:
                    data = json.loads(data["response"])
                except:
                    pass
            
            return ShellResult(
                understood=data.get("understood", False),
                function_name=data.get("function"),
                parameters=data.get("parameters", {}),
                shell_command=data.get("shell_command"),
                env_vars=data.get("env_vars", {}),
                explanation=data.get("explanation", ""),
            )
            
        except json.JSONDecodeError as e:
            # Try to extract command from raw response
            if "sq " in response:
                import re
                match = re.search(r'(sq\s+\w+[^"\'}\]]*)', response)
                if match:
                    cmd = match.group(1).strip()
                    return ShellResult(
                        understood=True,
                        shell_command=cmd,
                        explanation="Extracted command from response",
                    )
            return ShellResult(
                understood=False,
                error=f"Failed to parse LLM response: {e}",
                explanation="LLM returned invalid JSON",
            )
        except Exception as e:
            return ShellResult(
                understood=False,
                error=str(e),
                explanation=f"LLM error: {e}",
            )
    
    def _call_ollama(self, prompt: str) -> str:
        """Call Ollama API."""
        url = config.get("SQ_OLLAMA_URL", "http://localhost:11434")
        
        response = requests.post(
            f"{url}/api/chat",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "format": "json",
            },
            timeout=60,
        )
        
        if response.ok:
            return response.json().get("message", {}).get("content", "")
        else:
            raise RuntimeError(f"Ollama error: {response.status_code}")
    
    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API."""
        api_key = config.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt},
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=60,
        )
        
        if response.ok:
            return response.json()["choices"][0]["message"]["content"]
        else:
            raise RuntimeError(f"OpenAI error: {response.status_code}")
    
    def _check_missing_params(self, cmd: str) -> Tuple[List[str], str]:
        """Check for missing required parameters in command.
        
        Returns:
            Tuple of (missing params list, updated command with context values)
        """
        missing = []
        
        # Check if command needs URL
        needs_url = "sq watch" in cmd or "sq live" in cmd
        
        if needs_url:
            has_url = "--url" in cmd or "-u " in cmd
            has_intent = cmd.count('"') >= 2 or cmd.count("'") >= 2  # Has quoted intent
            
            if not has_url and not has_intent:
                if self.context.get("url"):
                    # Auto-inject URL from context
                    if "sq watch " in cmd:
                        cmd = cmd.replace("sq watch ", f"sq watch --url {self.context['url']} ", 1)
                    elif "sq live narrator" in cmd:
                        cmd = cmd.replace("sq live narrator ", f"sq live narrator --url {self.context['url']} ", 1)
                    elif "sq live " in cmd:
                        cmd = cmd.replace("sq live ", f"sq live --url {self.context['url']} ", 1)
                else:
                    missing.append("url")
        
        return missing, cmd
    
    def _prompt_for_missing(self, missing: List[str]) -> Dict[str, str]:
        """Prompt user for missing parameters."""
        values = {}
        
        for param in missing:
            if param == "url":
                print(f"   📹 Video source URL is required.")
                print(f"   Examples: rtsp://admin:pass@192.168.1.100:554/stream")
                print(f"             /dev/video0")
                print(f"             /path/to/video.mp4")
                value = input(f"   Enter URL: ").strip()
                if value:
                    values["url"] = value
                    self.context["url"] = value  # Save for future commands
            elif param == "email":
                value = input(f"   Enter email for notifications: ").strip()
                if value:
                    values["email"] = value
                    self.context["email"] = value
            elif param == "duration":
                value = input(f"   Enter duration in seconds [60]: ").strip()
                values["duration"] = value if value else "60"
        
        return values
    
    def _inject_params(self, cmd: str, params: Dict[str, str]) -> str:
        """Inject missing parameters into command."""
        for key, value in params.items():
            if key == "url" and "--url" not in cmd:
                # Insert after "sq watch"
                cmd = cmd.replace("sq watch ", f"sq watch --url {value} ", 1)
            elif key == "email" and "--email" not in cmd:
                cmd += f" --email {value}"
            elif key == "duration" and "--duration" not in cmd:
                cmd += f" --duration {value}"
        return cmd
    
    def execute(self, result: ShellResult) -> bool:
        """Execute shell command from result."""
        if not result.shell_command:
            return False
        
        cmd = result.shell_command
        
        # Check for missing required parameters (and auto-inject from context)
        missing, cmd = self._check_missing_params(cmd)
        
        if missing:
            print(f"   ⚠️  Missing required parameters: {', '.join(missing)}")
            params = self._prompt_for_missing(missing)
            if not all(p in params for p in missing):
                print("   ❌ Missing required parameters, command cancelled.")
                return False
            cmd = self._inject_params(cmd, params)
            print(f"   Updated command: {cmd}")
        elif cmd != result.shell_command:
            # URL was auto-injected from context
            print(f"   (Using saved URL: {self.context.get('url')})")
        
        # Set environment variables
        env = os.environ.copy()
        env.update(result.env_vars)
        
        # Get path to sq command (use current Python's sq)
        import shutil
        sq_path = shutil.which("sq")
        if not sq_path:
            # Fallback: try to find sq in current Python environment
            python_path = sys.executable
            sq_path = os.path.join(os.path.dirname(python_path), "sq")
        
        # Replace 'sq ' with full path
        if sq_path and os.path.exists(sq_path):
            cmd = cmd.replace("sq ", f"{sq_path} ", 1)
        
        print(f"$ {cmd}")
        
        try:
            # Run command
            process = subprocess.Popen(
                cmd,
                shell=True,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            
            # For long-running commands, run in background
            if "watch" in cmd and "&" not in cmd:
                self.running_process = process
                print(f"[Started in background, PID: {process.pid}]")
                print("[Use 'stop' to terminate]")
                
                # Show initial output
                for _ in range(5):
                    line = process.stdout.readline()
                    if line:
                        print(line, end="")
                    else:
                        break
                return True
            
            # For quick commands, wait for completion
            stdout, _ = process.communicate(timeout=30)
            if stdout:
                print(stdout)
            
            return process.returncode == 0
            
        except subprocess.TimeoutExpired:
            print("[Command timed out]")
            return False
        except Exception as e:
            print(f"[Error: {e}]")
            return False
    
    def _get_help(self) -> str:
        """Get help text."""
        return """
Streamware Interactive Shell
============================

Commands you can use:
- Natural language requests (e.g., "detect person and email me")
- "help" - Show this help
- "functions" or "list" - List available functions
- "history" - Show command history
- "stop" - Stop running detection
- "exit" or "quit" - Exit shell

Examples:
  > detect person for 5 minutes
  > track cars and save screenshots
  > email admin@example.com when you see someone
  > count people every minute
  > show config
  > stop

Tips:
- The shell understands natural language
- It will show the generated command before executing
- Press Enter to confirm, or type 'n' to cancel
"""
    
    def _list_functions(self) -> str:
        """List all functions."""
        lines = ["Available Functions:", ""]
        
        for cat in registry.categories():
            lines.append(f"## {cat.title()}")
            for fn in registry.get_by_category(cat):
                params = ", ".join(p.name for p in fn.params if p.required)
                lines.append(f"  - {fn.name}({params}): {fn.description}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_history(self) -> str:
        """Format command history."""
        if not self.history:
            return "No history"
        
        lines = ["Command History:", ""]
        for i, (cmd, result) in enumerate(self.history[-10:], 1):
            status = "✅" if result.understood else "❌"
            lines.append(f"{i}. {status} {cmd}")
            if result.shell_command:
                lines.append(f"   → {result.shell_command}")
        
        return "\n".join(lines)
    
    def _format_context(self) -> str:
        """Format current session context."""
        lines = [
            "Current Session Context:",
            "",
            f"📹 Video URL: {self.context.get('url') or '(not set)'}",
            f"📧 Email: {self.context.get('email') or '(not set)'}",
            f"⏱️  Duration: {self.context.get('duration', 60)}s",
            "",
            "Set values by typing:",
            "  rtsp://... or /dev/video0  → sets video URL",
            "  email@example.com          → sets notification email",
        ]
        return "\n".join(lines)
    
    def run(self):
        """Run interactive shell loop."""
        print("=" * 60)
        print("Streamware Interactive Shell")
        print("=" * 60)
        print("Type natural language commands or 'help' for assistance")
        print("Type 'context' to see/set current settings")
        print("Type 'exit' to quit")
        
        # Show current context if URL is set
        if self.context.get("url"):
            print(f"\n📹 Default URL: {self.context['url']}")
        if self.context.get("email"):
            print(f"📧 Default email: {self.context['email']}")
        print()
        
        while True:
            try:
                user_input = input("sq> ").strip()
                
                if not user_input:
                    continue
                
                # Parse input
                result = self.parse(user_input)
                self.history.append((user_input, result))
                
                # Handle exit
                if result.function_name == "exit":
                    print("Goodbye!")
                    break
                
                # Show help/info commands
                if result.function_name in ("help", "list", "history", "context", "set_url", "set_email"):
                    print(result.explanation)
                    continue
                
                # Handle clarification with options
                if result.function_name == "clarify" and result.options:
                    print(f"❓ {result.explanation}")
                    for key, desc, _ in result.options:
                        print(f"   {key}. {desc}")
                    
                    choice = input("   Choice [1-4]: ").strip().lower()
                    option_map = {"one": "1", "two": "2", "three": "3", "four": "4"}
                    choice = option_map.get(choice, choice)
                    
                    for key, desc, cmd in result.options:
                        if choice == key:
                            if cmd == "need_email":
                                email = input("   Enter email: ").strip()
                                cmd = f"SQ_NOTIFY_EMAIL={email} sq live narrator --mode track --focus person --duration 60 --skip-checks --adaptive"
                            elif cmd == "functions":
                                print(self._list_functions())
                                continue
                            
                            new_result = ShellResult(understood=True, shell_command=cmd, explanation=desc)
                            print(f"✅ {desc}")
                            print(f"   Command: {cmd}")
                            confirm = input("   Execute? [Y/n]: ").strip().lower()
                            if confirm in ("", "y", "yes"):
                                self.execute(new_result)
                            break
                    continue
                
                # Handle need_input for email
                if result.function_name == "need_input":
                    print(f"📝 {result.explanation}")
                    value = input(f"   Enter {result.input_type}: ").strip()
                    cmd = result.pending_command.replace(f"{{{result.input_type}}}", value)
                    new_result = ShellResult(understood=True, shell_command=cmd, explanation=f"Using {result.input_type}: {value}")
                    print(f"   Command: {cmd}")
                    confirm = input("   Execute? [Y/n]: ").strip().lower()
                    if confirm in ("", "y", "yes"):
                        self.execute(new_result)
                    continue
                
                # Show result
                if not result.understood:
                    print(f"❌ Not understood: {result.explanation}")
                    if result.error:
                        print(f"   Error: {result.error}")
                    print("   Tip: Say 'hello' for options")
                    continue
                
                print(f"✅ {result.explanation}")
                
                if result.shell_command:
                    print(f"   Command: {result.shell_command}")
                    
                    # Ask for confirmation unless auto_execute
                    if self.auto_execute:
                        self.execute(result)
                    else:
                        confirm = input("   Execute? [Y/n]: ").strip().lower()
                        if confirm in ("", "y", "yes"):
                            self.execute(result)
                        else:
                            print("   Cancelled")
                
                print()
                
            except KeyboardInterrupt:
                print("\n[Interrupted]")
                continue
            except EOFError:
                print("\nGoodbye!")
                break


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Streamware Interactive LLM Shell",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    sq shell                    # Start interactive shell
    sq shell --auto             # Auto-execute without confirmation
    sq shell --model gpt-4o     # Use specific model
    sq shell -v                 # Verbose mode (show LLM responses)
        """
    )
    
    parser.add_argument(
        "--model", "-m",
        default="llama3.2",
        help="LLM model to use (default: llama3.2)"
    )
    parser.add_argument(
        "--provider", "-p",
        choices=["ollama", "openai"],
        default="ollama",
        help="LLM provider (default: ollama)"
    )
    parser.add_argument(
        "--auto", "-a",
        action="store_true",
        help="Auto-execute commands without confirmation"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show LLM responses"
    )
    
    args = parser.parse_args()
    
    shell = LLMShell(
        model=args.model,
        provider=args.provider,
        auto_execute=args.auto,
        verbose=args.verbose,
    )
    
    shell.run()


if __name__ == "__main__":
    main()
