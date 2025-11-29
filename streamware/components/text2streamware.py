"""
Text to Streamware Component

Converts natural language to Streamware Quick (sq) commands using LLM.
Specialized for Qwen2.5 14B model with optimized prompts.
"""

from __future__ import annotations
import os
import json
import re
from typing import Any, Dict, List
from ..core import Component, register
from ..uri import StreamwareURI
from ..exceptions import ComponentError
from ..diagnostics import get_logger
from ..config import config

logger = get_logger(__name__)

# Ollama support
import requests


@register("text2sq")
@register("text2streamware")
class Text2StreamwareComponent(Component):
    """
    Convert natural language to Streamware Quick commands
    
    Optimized for Qwen2.5 14B model with specialized prompts.
    
    Operations:
    - convert: Convert text to sq command
    - explain: Explain what a command does
    - optimize: Optimize existing command
    - validate: Validate command syntax
    
    URI Examples:
        text2sq://convert?prompt=upload file to server
        text2sq://explain?command=sq ssh prod.com --upload file.txt
        text2sq://optimize?command=streamware "http://api.com" --pipe "transform://json"
    """
    
    input_mime = "text/plain"
    output_mime = "text/plain"
    
    # System prompt optimized for Qwen2.5
    SYSTEM_PROMPT = """You are an expert in Streamware Quick (sq) commands. 
Your task is to convert natural language requests into precise sq commands.

Streamware Quick (sq) is a CLI tool with these main commands:

1. HTTP Operations:
   sq get URL [--json] [--save FILE]
   sq post URL --data DATA [--json]

2. File Operations:
   sq file PATH [--json] [--csv] [--base64] [--save FILE]

3. SSH Operations:
   sq ssh HOST --upload FILE --remote PATH [--user USER] [--key KEY]
   sq ssh HOST --download REMOTE --local LOCAL
   sq ssh HOST --exec COMMAND
   sq ssh HOST --deploy FILE --remote PATH --restart SERVICE

4. Database:
   sq postgres "SQL_QUERY" [--json] [--csv] [--save FILE]

5. Messaging:
   sq kafka TOPIC --produce --data DATA
   sq kafka TOPIC --consume [--json] [--stream]

6. Communication:
   sq email TO --subject SUBJECT --body TEXT [--attach FILE]
   sq slack CHANNEL --message TEXT [--token TOKEN]

7. LLM Operations:
   sq llm "prompt" --to-sql
   sq llm "prompt" --to-sq
   sq llm "text" --analyze

RULES:
1. Output ONLY the command, no explanations
2. Use proper flags and syntax
3. Be concise and accurate
4. Use environment variables when appropriate (e.g., $TOKEN)
5. Escape special characters properly

Examples:
User: "upload app.tar.gz to production server"
Assistant: sq ssh prod.company.com --upload app.tar.gz --remote /app/ --user deploy

User: "get users from database and save as CSV"
Assistant: sq postgres "SELECT * FROM users" --csv --save users.csv

User: "send notification to slack"
Assistant: sq slack general --message "Notification" --token $SLACK_TOKEN

Now convert the user's request:"""
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.operation = uri.operation or "convert"
        
        # LLM configuration (use config with env fallback)
        self.model = uri.get_param("model", config.get("SQ_MODEL", "qwen2.5:14b"))
        self.ollama_url = uri.get_param("ollama_url", config.get("SQ_OLLAMA_URL", "http://localhost:11434"))
        self.temperature = float(uri.get_param("temperature", 0.1))  # Low for precise commands
        self.max_tokens = int(uri.get_param("max_tokens", 500))
        
        # Input
        self.prompt = uri.get_param("prompt")
        self.command = uri.get_param("command")
    
    def process(self, data: Any) -> str:
        """Process text to streamware conversion"""
        operations = {
            "convert": self._convert,
            "explain": self._explain,
            "optimize": self._optimize,
            "validate": self._validate,
        }
        
        operation_func = operations.get(self.operation)
        if not operation_func:
            raise ComponentError(f"Unknown operation: {self.operation}")
        
        return operation_func(data)
    
    def _convert(self, data: Any) -> str:
        """Convert natural language to sq command"""
        text = self.prompt or str(data)
        
        if not text:
            raise ComponentError("No input text provided")
        
        logger.info(f"Converting to sq command: {text}")
        
        # Call LLM
        response = self._call_qwen(
            prompt=f"User request: {text}\n\nStreamware sq command:",
            system=self.SYSTEM_PROMPT
        )
        
        # Clean output
        command = self._clean_command(response)
        
        logger.info(f"Generated command: {command}")
        
        return command
    
    def _explain(self, data: Any) -> str:
        """Explain what a command does"""
        command = self.command or str(data)
        
        prompt = f"""Explain what this Streamware command does in simple terms:

Command: {command}

Provide a brief, clear explanation."""
        
        return self._call_qwen(prompt)
    
    def _optimize(self, data: Any) -> str:
        """Optimize an existing command"""
        command = self.command or str(data)
        
        prompt = f"""Optimize this Streamware command to be more efficient:

Original: {command}

Provide ONLY the optimized command, no explanation."""
        
        response = self._call_qwen(prompt, system=self.SYSTEM_PROMPT)
        return self._clean_command(response)
    
    def _validate(self, data: Any) -> Dict:
        """Validate command syntax"""
        command = self.command or str(data)
        
        # Basic validation
        errors = []
        warnings = []
        
        if not command.startswith("sq "):
            errors.append("Command must start with 'sq'")
        
        # Check for common mistakes
        if "--pipe" in command and "sq " in command:
            warnings.append("Use 'streamware' for --pipe, not 'sq'")
        
        if "--" in command and " -" in command:
            warnings.append("Mix of long and short flags")
        
        valid = len(errors) == 0
        
        return {
            "valid": valid,
            "command": command,
            "errors": errors,
            "warnings": warnings
        }
    
    def _call_qwen(self, prompt: str, system: str = None) -> str:
        """Call Qwen2.5 via Ollama"""
        url = f"{self.ollama_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
                "top_p": 0.9,
                "top_k": 40,
            }
        }
        
        if system:
            payload["system"] = system
        
        try:
            logger.debug(f"Calling Qwen2.5: {self.model}")
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "").strip()
            
        except requests.exceptions.RequestException as e:
            raise ComponentError(f"Qwen API error: {e}")
    
    def _clean_command(self, text: str) -> str:
        """Clean and extract sq command from response"""
        # Remove markdown code blocks
        text = re.sub(r'```[\w]*\n', '', text)
        text = re.sub(r'```\n?', '', text)
        
        # Remove common prefixes
        text = re.sub(r'^(Command:|Output:|Result:)\s*', '', text, flags=re.IGNORECASE)
        
        # Extract first line that starts with sq
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('sq '):
                return line
        
        # If no sq command found, return cleaned text
        return text.strip()


# Quick helper functions
def text_to_sq(text: str, model: str = "qwen2.5:14b") -> str:
    """Quick conversion of text to sq command"""
    from ..core import flow
    
    uri = f"text2sq://convert?prompt={text}&model={model}"
    return flow(uri).run()


def explain_command(command: str, model: str = "qwen2.5:14b") -> str:
    """Explain what a command does"""
    from ..core import flow
    
    uri = f"text2sq://explain?command={command}&model={model}"
    return flow(uri).run()


def optimize_command(command: str, model: str = "qwen2.5:14b") -> str:
    """Optimize a command"""
    from ..core import flow
    
    uri = f"text2sq://optimize?command={command}&model={model}"
    return flow(uri).run()
