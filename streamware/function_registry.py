"""
Function Registry for Streamware

Centralized registry of all available functions and commands.
Enables LLM to understand and invoke system capabilities.

Usage:
    from streamware.function_registry import registry, invoke, list_functions
    
    # List all functions
    for fn in registry.functions:
        print(fn.name, fn.description)
    
    # Invoke function by name
    result = invoke("detect_person", url="rtsp://...", duration=30)
    
    # Get function info for LLM
    prompt = registry.get_llm_context()
"""

import inspect
import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union
from functools import wraps

from .config import config


# =============================================================================
# FUNCTION DEFINITION
# =============================================================================

@dataclass
class FunctionParam:
    """Function parameter definition."""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None
    choices: Optional[List[str]] = None
    env_var: Optional[str] = None  # Corresponding environment variable


@dataclass  
class RegisteredFunction:
    """Registered function with metadata."""
    name: str
    description: str
    category: str
    params: List[FunctionParam] = field(default_factory=list)
    returns: str = "None"
    examples: List[str] = field(default_factory=list)
    shell_template: Optional[str] = None
    callable: Optional[Callable] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON/LLM."""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type,
                    "description": p.description,
                    "required": p.required,
                    "default": p.default,
                    "choices": p.choices,
                }
                for p in self.params
            ],
            "returns": self.returns,
            "examples": self.examples,
            "shell_template": self.shell_template,
        }
    
    def generate_shell(self, **kwargs) -> str:
        """Generate shell command with parameters."""
        if self.shell_template:
            cmd = self.shell_template
            for key, value in kwargs.items():
                if value is not None:
                    cmd = cmd.replace(f"{{{key}}}", str(value))
            # Remove unused placeholders and their preceding flags
            # Match patterns like "--flag {placeholder}" or "--flag-name {placeholder}"
            cmd = re.sub(r'--[\w-]+\s+\{[^}]+\}', '', cmd)  # Remove --flag {placeholder}
            cmd = re.sub(r'\{[^}]+\}', '', cmd)  # Remove any remaining {placeholder}
            cmd = re.sub(r'\s+', ' ', cmd)  # Normalize whitespace
            return cmd.strip()
        return f"sq {self.name} " + " ".join(f"--{k} {v}" for k, v in kwargs.items() if v)
    
    def generate_env(self, **kwargs) -> Dict[str, str]:
        """Generate environment variables from parameters."""
        env = {}
        for param in self.params:
            if param.env_var and param.name in kwargs:
                value = kwargs[param.name]
                if value is not None:
                    env[param.env_var] = str(value)
        return env


# =============================================================================
# REGISTRY
# =============================================================================

class FunctionRegistry:
    """Central registry of all functions."""
    
    def __init__(self):
        self.functions: List[RegisteredFunction] = []
        self._by_name: Dict[str, RegisteredFunction] = {}
        self._by_category: Dict[str, List[RegisteredFunction]] = {}
    
    def register(
        self,
        name: str,
        description: str,
        category: str = "general",
        params: Optional[List[FunctionParam]] = None,
        returns: str = "None",
        examples: Optional[List[str]] = None,
        shell_template: Optional[str] = None,
    ) -> Callable:
        """Decorator to register a function."""
        def decorator(func: Callable) -> Callable:
            fn = RegisteredFunction(
                name=name,
                description=description,
                category=category,
                params=params or [],
                returns=returns,
                examples=examples or [],
                shell_template=shell_template,
                callable=func,
            )
            self.functions.append(fn)
            self._by_name[name] = fn
            
            if category not in self._by_category:
                self._by_category[category] = []
            self._by_category[category].append(fn)
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def add(self, fn: RegisteredFunction):
        """Add a function definition without decorator."""
        self.functions.append(fn)
        self._by_name[fn.name] = fn
        if fn.category not in self._by_category:
            self._by_category[fn.category] = []
        self._by_category[fn.category].append(fn)
    
    def get(self, name: str) -> Optional[RegisteredFunction]:
        """Get function by name."""
        return self._by_name.get(name)
    
    def get_by_category(self, category: str) -> List[RegisteredFunction]:
        """Get all functions in category."""
        return self._by_category.get(category, [])
    
    def categories(self) -> List[str]:
        """List all categories."""
        return list(self._by_category.keys())
    
    def invoke(self, name: str, **kwargs) -> Any:
        """Invoke function by name."""
        fn = self.get(name)
        if not fn:
            raise ValueError(f"Function not found: {name}")
        if not fn.callable:
            raise ValueError(f"Function {name} has no callable")
        return fn.callable(**kwargs)
    
    def get_llm_context(self, categories: Optional[List[str]] = None) -> str:
        """Generate context for LLM with all function info."""
        lines = [
            "# Available Functions",
            "",
            "You have access to the following functions to control video surveillance system:",
            "",
        ]
        
        funcs = self.functions
        if categories:
            funcs = [f for f in funcs if f.category in categories]
        
        for cat in sorted(set(f.category for f in funcs)):
            lines.append(f"## {cat.title()}")
            lines.append("")
            
            for fn in sorted([f for f in funcs if f.category == cat], key=lambda x: x.name):
                lines.append(f"### {fn.name}")
                lines.append(f"{fn.description}")
                lines.append("")
                
                if fn.params:
                    lines.append("Parameters:")
                    for p in fn.params:
                        req = " (required)" if p.required else f" (default: {p.default})"
                        choices = f" [{', '.join(p.choices)}]" if p.choices else ""
                        lines.append(f"  - {p.name}: {p.type}{choices} - {p.description}{req}")
                    lines.append("")
                
                if fn.examples:
                    lines.append("Examples:")
                    for ex in fn.examples:
                        lines.append(f'  - "{ex}"')
                    lines.append("")
                
                if fn.shell_template:
                    lines.append(f"Shell: `{fn.shell_template}`")
                    lines.append("")
        
        return "\n".join(lines)
    
    def to_json(self) -> str:
        """Export registry to JSON."""
        return json.dumps(
            [fn.to_dict() for fn in self.functions],
            indent=2
        )
    
    def to_openai_tools(self) -> List[Dict]:
        """Convert to OpenAI function calling format."""
        tools = []
        for fn in self.functions:
            properties = {}
            required = []
            
            for p in fn.params:
                prop = {"type": p.type, "description": p.description}
                if p.choices:
                    prop["enum"] = p.choices
                properties[p.name] = prop
                if p.required:
                    required.append(p.name)
            
            tools.append({
                "type": "function",
                "function": {
                    "name": fn.name,
                    "description": fn.description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    }
                }
            })
        return tools


# =============================================================================
# GLOBAL REGISTRY
# =============================================================================

registry = FunctionRegistry()


# =============================================================================
# REGISTER CORE FUNCTIONS
# =============================================================================

def _register_core_functions():
    """Register all core Streamware functions."""
    
    # Detection functions
    registry.add(RegisteredFunction(
        name="detect",
        description="Detect objects in video stream using YOLO or LLM",
        category="detection",
        params=[
            FunctionParam("target", "string", "Object to detect (person, car, animal, motion)", True, "person",
                         choices=["person", "car", "vehicle", "animal", "dog", "cat", "face", "motion", "object"]),
            FunctionParam("url", "string", "Video source URL (RTSP, HTTP, file)", False, None, env_var="SQ_DEFAULT_URL"),
            FunctionParam("duration", "integer", "Duration in seconds", False, 60, env_var="SQ_DURATION"),
            FunctionParam("confidence", "number", "Detection confidence 0-1", False, 0.5),
            FunctionParam("mode", "string", "Detection mode", False, "yolo", choices=["yolo", "llm", "hybrid"]),
        ],
        returns="DetectionResult with has_target, confidence, detections list",
        examples=[
            "detect person",
            "detect car with high confidence",
            "detect any motion for 5 minutes",
        ],
        shell_template="sq watch --detect {target} --mode {mode} --confidence {confidence} --duration {duration}",
    ))
    
    registry.add(RegisteredFunction(
        name="track",
        description="Track objects across video frames with ID assignment",
        category="detection",
        params=[
            FunctionParam("target", "string", "Object to track", True, "person"),
            FunctionParam("url", "string", "Video source URL", False, None, env_var="SQ_DEFAULT_URL"),
            FunctionParam("duration", "integer", "Duration in seconds", False, 60),
            FunctionParam("fps", "number", "Frames per second", False, 2.0),
        ],
        returns="Tracking data with object IDs and trajectories",
        examples=[
            "track person entering",
            "track all vehicles for 10 minutes",
        ],
        shell_template="sq watch --track {target} --fps {fps} --duration {duration}",
    ))
    
    registry.add(RegisteredFunction(
        name="count",
        description="Count objects in video stream",
        category="detection",
        params=[
            FunctionParam("target", "string", "Object to count", True, "person"),
            FunctionParam("url", "string", "Video source URL", False, None),
            FunctionParam("interval", "integer", "Count interval in seconds", False, 10),
        ],
        returns="Object count per interval",
        examples=[
            "count people every minute",
            "count cars in parking lot",
        ],
        shell_template="sq watch --count {target} --interval {interval}",
    ))
    
    # Notification functions
    registry.add(RegisteredFunction(
        name="notify_email",
        description="Send email notification when event detected",
        category="notification",
        params=[
            FunctionParam("email", "string", "Recipient email address", True, env_var="SQ_NOTIFY_EMAIL"),
            FunctionParam("mode", "string", "Notification mode", False, "digest",
                         choices=["instant", "digest", "summary"], env_var="SQ_NOTIFY_MODE"),
            FunctionParam("interval", "integer", "Digest interval in seconds", False, 60, env_var="SQ_NOTIFY_INTERVAL"),
            FunctionParam("subject", "string", "Email subject prefix", False, "Streamware Alert"),
        ],
        returns="Notification status",
        examples=[
            "email admin@company.com immediately",
            "email alerts@example.com every 5 minutes",
            "send summary email to security@corp.com",
        ],
        shell_template="sq watch --email {email} --notify-mode {mode} --notify-interval {interval}",
    ))
    
    registry.add(RegisteredFunction(
        name="notify_slack",
        description="Send Slack notification",
        category="notification",
        params=[
            FunctionParam("channel", "string", "Slack channel (e.g., #alerts)", True, env_var="SQ_SLACK_CHANNEL"),
            FunctionParam("webhook", "string", "Slack webhook URL", False, None, env_var="SQ_SLACK_WEBHOOK"),
        ],
        returns="Notification status",
        examples=[
            "notify slack #security",
            "send to slack channel alerts",
        ],
        shell_template="sq watch --slack {channel}",
    ))
    
    registry.add(RegisteredFunction(
        name="notify_telegram",
        description="Send Telegram notification",
        category="notification",
        params=[
            FunctionParam("chat_id", "string", "Telegram chat ID", True, env_var="SQ_TELEGRAM_CHAT_ID"),
            FunctionParam("bot_token", "string", "Telegram bot token", False, None, env_var="SQ_TELEGRAM_TOKEN"),
        ],
        returns="Notification status",
        examples=[
            "notify telegram 123456789",
            "send to telegram",
        ],
        shell_template="sq watch --telegram {chat_id}",
    ))
    
    # Output functions
    registry.add(RegisteredFunction(
        name="screenshot",
        description="Save screenshot when event detected",
        category="output",
        params=[
            FunctionParam("path", "string", "Output directory", False, "./screenshots"),
            FunctionParam("format", "string", "Image format", False, "jpg", choices=["jpg", "png"]),
        ],
        returns="Screenshot path",
        examples=[
            "save screenshot",
            "take photo when person detected",
        ],
        shell_template="sq watch --screenshot --output {path}",
    ))
    
    registry.add(RegisteredFunction(
        name="record",
        description="Record video clip when event detected",
        category="output",
        params=[
            FunctionParam("path", "string", "Output directory", False, "./recordings"),
            FunctionParam("duration", "integer", "Clip duration in seconds", False, 10),
            FunctionParam("before", "integer", "Seconds before event", False, 3),
        ],
        returns="Recording path",
        examples=[
            "record video",
            "save 30 second clip when motion detected",
        ],
        shell_template="sq watch --record --clip-duration {duration}",
    ))
    
    registry.add(RegisteredFunction(
        name="speak",
        description="Speak detection results using TTS",
        category="output",
        params=[
            FunctionParam("engine", "string", "TTS engine", False, "pico", choices=["pico", "espeak", "festival"]),
            FunctionParam("voice", "string", "Voice name", False, None),
            FunctionParam("rate", "number", "Speech rate", False, 1.0),
        ],
        returns="None",
        examples=[
            "speak detections",
            "announce when person enters",
            "voice alerts",
        ],
        shell_template="sq watch --tts --tts-engine {engine}",
    ))
    
    # Configuration functions
    registry.add(RegisteredFunction(
        name="set_source",
        description="Set video source URL",
        category="config",
        params=[
            FunctionParam("url", "string", "Video source URL (RTSP, HTTP, file, or camera index)", True),
        ],
        returns="None",
        examples=[
            "use rtsp://admin:pass@192.168.1.100:554/stream",
            "set source to /dev/video0",
            "use camera 0",
        ],
        shell_template="export SQ_DEFAULT_URL={url}",
    ))
    
    registry.add(RegisteredFunction(
        name="set_model",
        description="Set LLM model for analysis",
        category="config",
        params=[
            FunctionParam("model", "string", "Model name", True),
            FunctionParam("provider", "string", "Provider", False, "ollama", choices=["ollama", "openai"]),
        ],
        returns="None",
        examples=[
            "use llama3.2 model",
            "set model to gpt-4o",
        ],
        shell_template="export SQ_LLM_MODEL={model}",
    ))
    
    registry.add(RegisteredFunction(
        name="show_config",
        description="Show current configuration",
        category="config",
        params=[],
        returns="Current config values",
        examples=[
            "show config",
            "what are my settings",
        ],
        shell_template="sq config --show",
    ))
    
    # System functions
    registry.add(RegisteredFunction(
        name="status",
        description="Show system status and running processes",
        category="system",
        params=[],
        returns="System status info",
        examples=[
            "show status",
            "what's running",
        ],
        shell_template="sq status",
    ))
    
    registry.add(RegisteredFunction(
        name="stop",
        description="Stop running detection/monitoring",
        category="system",
        params=[],
        returns="None",
        examples=[
            "stop",
            "stop watching",
            "cancel",
        ],
        shell_template="pkill -f 'sq watch' || echo 'Nothing running'",
    ))
    
    registry.add(RegisteredFunction(
        name="help",
        description="Show help for functions",
        category="system",
        params=[
            FunctionParam("topic", "string", "Help topic", False, None),
        ],
        returns="Help text",
        examples=[
            "help",
            "help detection",
            "how do I detect person",
        ],
        shell_template="sq --help",
    ))


# Register core functions on import
_register_core_functions()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def invoke(name: str, **kwargs) -> Any:
    """Invoke a registered function."""
    return registry.invoke(name, **kwargs)


def list_functions(category: Optional[str] = None) -> List[str]:
    """List available function names."""
    funcs = registry.functions
    if category:
        funcs = registry.get_by_category(category)
    return [f.name for f in funcs]


def get_function(name: str) -> Optional[RegisteredFunction]:
    """Get function definition."""
    return registry.get(name)


def generate_shell(name: str, **kwargs) -> str:
    """Generate shell command for function."""
    fn = registry.get(name)
    if fn:
        return fn.generate_shell(**kwargs)
    return ""


def get_llm_context() -> str:
    """Get function context for LLM."""
    return registry.get_llm_context()


# =============================================================================
# EXPORT
# =============================================================================

__all__ = [
    "registry",
    "FunctionRegistry",
    "RegisteredFunction",
    "FunctionParam",
    "invoke",
    "list_functions",
    "get_function",
    "generate_shell",
    "get_llm_context",
]
