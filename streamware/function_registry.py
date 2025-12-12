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
    
    def generate_shell(self, lang: str = "en", **kwargs) -> str:
        """Generate shell command with parameters and language support.
        
        Args:
            lang: Language code for TTS (en, pl, de)
            **kwargs: Command parameters
        """
        if self.shell_template:
            cmd = self.shell_template
            
            # Handle boolean params that add flags
            if kwargs.get("speak"):
                cmd += " --tts --tts-diff"
            
            for key, value in kwargs.items():
                if value is not None and not isinstance(value, bool):
                    cmd = cmd.replace(f"{{{key}}}", str(value))
            
            # Add language parameter for TTS commands
            if "--tts" in cmd and lang and lang != "en":
                cmd += f" --lang {lang}"
            
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
            FunctionParam("speak", "boolean", "Speak results using TTS", False, False),
            FunctionParam("model", "string", "Vision LLM model", False, "llava:7b"),
        ],
        returns="Tracking data with object IDs and trajectories",
        examples=[
            "track person entering",
            "track all vehicles for 10 minutes",
            "track person and speak",
        ],
        shell_template="sq live narrator --mode track --focus {target} --duration {duration} --model {model} --skip-checks",
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
    
    registry.add(RegisteredFunction(
        name="narrate",
        description="Track and narrate objects with voice (TTS)",
        category="detection",
        params=[
            FunctionParam("target", "string", "Object to track and narrate", True, "person"),
            FunctionParam("url", "string", "Video source URL", False, None, env_var="SQ_DEFAULT_URL"),
            FunctionParam("duration", "integer", "Duration in seconds", False, 60),
            FunctionParam("model", "string", "Vision LLM model", False, "llava:7b"),
        ],
        returns="Voice narration of scene",
        examples=[
            "track person and speak",
            "narrate what you see",
            "tell me when someone enters",
            "talk about the scene",
        ],
        shell_template="sq live narrator --mode track --focus {target} --duration {duration} --tts --tts-diff --model {model} --skip-checks",
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
        description="Speak detection results using TTS (voice narration)",
        category="output",
        params=[
            FunctionParam("target", "string", "Object to track and speak about", False, "person"),
            FunctionParam("mode", "string", "TTS mode", False, "diff", choices=["diff", "all"]),
            FunctionParam("duration", "integer", "Duration in seconds", False, 60),
        ],
        returns="None",
        examples=[
            "speak detections",
            "announce when person enters",
            "track and speak",
            "voice alerts for person",
        ],
        shell_template="sq live narrator --tts --tts-{mode} --focus {target} --duration {duration}",
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
    
    # =========================================================================
    # COMMUNICATION FUNCTIONS
    # =========================================================================
    
    registry.add(RegisteredFunction(
        name="send_slack",
        description="Send message to Slack channel",
        category="communication",
        params=[
            FunctionParam("channel", "string", "Slack channel name", True),
            FunctionParam("message", "string", "Message to send", True),
            FunctionParam("token", "string", "Slack bot token", False, None, env_var="SLACK_BOT_TOKEN"),
        ],
        returns="Message ID",
        examples=[
            "send hello to slack channel ops",
            "slack message to #alerts: server down",
        ],
        shell_template="sq slack {channel} --message \"{message}\"",
    ))
    
    registry.add(RegisteredFunction(
        name="send_telegram",
        description="Send message via Telegram",
        category="communication",
        params=[
            FunctionParam("chat_id", "string", "Telegram chat ID", True),
            FunctionParam("message", "string", "Message to send", True),
            FunctionParam("bot_token", "string", "Telegram bot token", False, None, env_var="TELEGRAM_BOT_TOKEN"),
        ],
        returns="Message ID",
        examples=[
            "send telegram: motion detected",
            "telegram alert to admin",
        ],
        shell_template="sq telegram {chat_id} --message \"{message}\"",
    ))
    
    registry.add(RegisteredFunction(
        name="send_discord",
        description="Send message to Discord channel",
        category="communication",
        params=[
            FunctionParam("webhook", "string", "Discord webhook URL", True, env_var="DISCORD_WEBHOOK"),
            FunctionParam("message", "string", "Message to send", True),
        ],
        returns="None",
        examples=[
            "discord alert: person detected",
        ],
        shell_template="sq discord --webhook {webhook} --message \"{message}\"",
    ))
    
    registry.add(RegisteredFunction(
        name="send_teams",
        description="Send message to Microsoft Teams",
        category="communication",
        params=[
            FunctionParam("webhook", "string", "Teams webhook URL", True, env_var="TEAMS_WEBHOOK"),
            FunctionParam("message", "string", "Message to send", True),
        ],
        returns="None",
        examples=[
            "teams message: deployment complete",
        ],
        shell_template="sq teams --webhook {webhook} --message \"{message}\"",
    ))
    
    registry.add(RegisteredFunction(
        name="send_sms",
        description="Send SMS message via Twilio",
        category="communication",
        params=[
            FunctionParam("to", "string", "Phone number", True),
            FunctionParam("message", "string", "Message to send", True),
        ],
        returns="Message SID",
        examples=[
            "sms +1234567890: alert triggered",
        ],
        shell_template="sq sms {to} --message \"{message}\"",
    ))
    
    # =========================================================================
    # HTTP/API FUNCTIONS
    # =========================================================================
    
    registry.add(RegisteredFunction(
        name="http_get",
        description="Make HTTP GET request",
        category="http",
        params=[
            FunctionParam("url", "string", "URL to fetch", True),
            FunctionParam("headers", "string", "HTTP headers as JSON", False, None),
            FunctionParam("save", "string", "Save response to file", False, None),
        ],
        returns="Response data",
        examples=[
            "get https://api.example.com/data",
            "fetch weather from api.weather.com",
        ],
        shell_template="sq get {url}",
    ))
    
    registry.add(RegisteredFunction(
        name="http_post",
        description="Make HTTP POST request",
        category="http",
        params=[
            FunctionParam("url", "string", "URL to post to", True),
            FunctionParam("data", "string", "Data to send (JSON)", True),
            FunctionParam("headers", "string", "HTTP headers as JSON", False, None),
        ],
        returns="Response data",
        examples=[
            "post to https://api.example.com/webhook",
            "send data to API",
        ],
        shell_template="sq post {url} --data '{data}'",
    ))
    
    # =========================================================================
    # FILE FUNCTIONS
    # =========================================================================
    
    registry.add(RegisteredFunction(
        name="read_file",
        description="Read file contents",
        category="file",
        params=[
            FunctionParam("path", "string", "File path", True),
            FunctionParam("format", "string", "Output format", False, "text", choices=["text", "json", "csv", "base64"]),
        ],
        returns="File contents",
        examples=[
            "read config.json",
            "load data from data.csv",
        ],
        shell_template="sq file {path} --{format}",
    ))
    
    registry.add(RegisteredFunction(
        name="write_file",
        description="Write data to file",
        category="file",
        params=[
            FunctionParam("path", "string", "File path", True),
            FunctionParam("data", "string", "Data to write", True),
        ],
        returns="Success status",
        examples=[
            "save to output.json",
            "write report to report.html",
        ],
        shell_template="echo '{data}' > {path}",
    ))
    
    # =========================================================================
    # DATABASE FUNCTIONS
    # =========================================================================
    
    registry.add(RegisteredFunction(
        name="postgres_query",
        description="Execute PostgreSQL query",
        category="database",
        params=[
            FunctionParam("sql", "string", "SQL query", True),
            FunctionParam("format", "string", "Output format", False, "json", choices=["json", "csv", "table"]),
        ],
        returns="Query results",
        examples=[
            "query SELECT * FROM users",
            "get all orders from database",
        ],
        shell_template="sq postgres \"{sql}\" --{format}",
    ))
    
    registry.add(RegisteredFunction(
        name="kafka_consume",
        description="Consume messages from Kafka topic",
        category="database",
        params=[
            FunctionParam("topic", "string", "Kafka topic", True),
            FunctionParam("group", "string", "Consumer group", False, "default"),
        ],
        returns="Messages",
        examples=[
            "consume from events topic",
            "read kafka messages from logs",
        ],
        shell_template="sq kafka {topic} --consume --group {group}",
    ))
    
    registry.add(RegisteredFunction(
        name="kafka_produce",
        description="Produce message to Kafka topic",
        category="database",
        params=[
            FunctionParam("topic", "string", "Kafka topic", True),
            FunctionParam("message", "string", "Message to send", True),
        ],
        returns="None",
        examples=[
            "send event to kafka",
            "publish to orders topic",
        ],
        shell_template="sq kafka {topic} --produce --data '{message}'",
    ))
    
    # =========================================================================
    # SSH/DEPLOY FUNCTIONS
    # =========================================================================
    
    registry.add(RegisteredFunction(
        name="ssh_exec",
        description="Execute command on remote server via SSH",
        category="deploy",
        params=[
            FunctionParam("host", "string", "Remote host", True),
            FunctionParam("command", "string", "Command to execute", True),
            FunctionParam("user", "string", "SSH user", False, "root"),
        ],
        returns="Command output",
        examples=[
            "run uptime on server.com",
            "execute df -h on production",
        ],
        shell_template="sq ssh {host} --user {user} --exec \"{command}\"",
    ))
    
    registry.add(RegisteredFunction(
        name="ssh_upload",
        description="Upload file to remote server",
        category="deploy",
        params=[
            FunctionParam("host", "string", "Remote host", True),
            FunctionParam("local", "string", "Local file path", True),
            FunctionParam("remote", "string", "Remote file path", True),
            FunctionParam("user", "string", "SSH user", False, "root"),
        ],
        returns="Success status",
        examples=[
            "upload app.tar.gz to server",
            "copy config to production",
        ],
        shell_template="sq ssh {host} --user {user} --upload {local} --remote {remote}",
    ))
    
    registry.add(RegisteredFunction(
        name="deploy",
        description="Deploy application to server",
        category="deploy",
        params=[
            FunctionParam("host", "string", "Remote host", True),
            FunctionParam("file", "string", "File to deploy", True),
            FunctionParam("restart", "string", "Service to restart after deploy", False, None),
        ],
        returns="Deploy result",
        examples=[
            "deploy app.tar.gz to production",
            "deploy and restart nginx",
        ],
        shell_template="sq ssh {host} --deploy {file} --restart {restart}",
    ))
    
    # =========================================================================
    # VOICE FUNCTIONS
    # =========================================================================
    
    registry.add(RegisteredFunction(
        name="voice_listen",
        description="Listen for voice input (STT)",
        category="voice",
        params=[
            FunctionParam("language", "string", "Language code", False, "en-US"),
            FunctionParam("timeout", "integer", "Timeout in seconds", False, 10),
        ],
        returns="Transcribed text",
        examples=[
            "listen for voice",
            "what did I say",
            "voice input",
        ],
        shell_template="sq voice listen --lang {language} --timeout {timeout}",
    ))
    
    registry.add(RegisteredFunction(
        name="voice_speak",
        description="Speak text using TTS",
        category="voice",
        params=[
            FunctionParam("text", "string", "Text to speak", True),
            FunctionParam("engine", "string", "TTS engine", False, "pico", choices=["pico", "espeak", "gtts"]),
        ],
        returns="None",
        examples=[
            "say hello world",
            "speak the results",
            "announce: person detected",
        ],
        shell_template="sq voice speak \"{text}\" --engine {engine}",
    ))
    
    # =========================================================================
    # AUTOMATION FUNCTIONS
    # =========================================================================
    
    registry.add(RegisteredFunction(
        name="mouse_click",
        description="Click at screen coordinates or AI-detected element",
        category="automation",
        params=[
            FunctionParam("target", "string", "Click target (coordinates 'x,y' or element description)", True),
        ],
        returns="Click result",
        examples=[
            "click on submit button",
            "click at 100,200",
            "click the OK button",
        ],
        shell_template="sq voice-click \"{target}\"",
    ))
    
    registry.add(RegisteredFunction(
        name="keyboard_type",
        description="Type text using keyboard",
        category="automation",
        params=[
            FunctionParam("text", "string", "Text to type", True),
        ],
        returns="None",
        examples=[
            "type hello world",
            "wpisz: test message",
        ],
        shell_template="sq voice-keyboard type \"{text}\"",
    ))
    
    registry.add(RegisteredFunction(
        name="keyboard_press",
        description="Press keyboard key",
        category="automation",
        params=[
            FunctionParam("key", "string", "Key to press", True),
        ],
        returns="None",
        examples=[
            "press enter",
            "naciśnij tab",
            "hit escape",
        ],
        shell_template="sq voice-keyboard press {key}",
    ))
    
    registry.add(RegisteredFunction(
        name="take_screenshot",
        description="Take screenshot of screen",
        category="automation",
        params=[
            FunctionParam("output", "string", "Output file path", False, "screenshot.png"),
        ],
        returns="Screenshot path",
        examples=[
            "take screenshot",
            "capture screen",
        ],
        shell_template="sq desktop screenshot --output {output}",
    ))
    
    # =========================================================================
    # MEDIA FUNCTIONS
    # =========================================================================
    
    registry.add(RegisteredFunction(
        name="describe_image",
        description="Describe image using AI vision",
        category="media",
        params=[
            FunctionParam("image", "string", "Image path or URL", True),
            FunctionParam("model", "string", "Vision model", False, "llava:7b"),
        ],
        returns="Image description",
        examples=[
            "describe this image",
            "what's in the photo",
            "analyze screenshot",
        ],
        shell_template="sq media describe_image --file {image} --model {model}",
    ))
    
    registry.add(RegisteredFunction(
        name="describe_video",
        description="Describe video using AI vision",
        category="media",
        params=[
            FunctionParam("video", "string", "Video path or URL", True),
            FunctionParam("mode", "string", "Analysis mode", False, "full", choices=["full", "stream", "diff"]),
        ],
        returns="Video description",
        examples=[
            "describe the video",
            "analyze video clip",
        ],
        shell_template="sq media describe_video --file {video} --mode {mode}",
    ))
    
    # =========================================================================
    # LLM FUNCTIONS
    # =========================================================================
    
    registry.add(RegisteredFunction(
        name="llm_query",
        description="Query LLM with prompt",
        category="llm",
        params=[
            FunctionParam("prompt", "string", "Prompt text", True),
            FunctionParam("model", "string", "LLM model", False, "llama3.2"),
            FunctionParam("provider", "string", "Provider", False, "ollama", choices=["ollama", "openai"]),
        ],
        returns="LLM response",
        examples=[
            "ask AI: what is the weather",
            "query llm about python",
        ],
        shell_template="sq llm \"{prompt}\" --model {model} --provider {provider}",
    ))
    
    registry.add(RegisteredFunction(
        name="text_to_sql",
        description="Convert natural language to SQL",
        category="llm",
        params=[
            FunctionParam("text", "string", "Natural language query", True),
        ],
        returns="SQL query",
        examples=[
            "convert 'get all users' to SQL",
            "sql for: find orders from last week",
        ],
        shell_template="sq llm \"{text}\" --to-sql",
    ))
    
    registry.add(RegisteredFunction(
        name="text_to_command",
        description="Convert natural language to shell command",
        category="llm",
        params=[
            FunctionParam("text", "string", "Natural language request", True),
        ],
        returns="Shell command",
        examples=[
            "how to list all files",
            "command for: find large files",
        ],
        shell_template="sq llm \"{text}\" --to-bash",
    ))
    
    # =========================================================================
    # NETWORK FUNCTIONS
    # =========================================================================
    
    registry.add(RegisteredFunction(
        name="network_scan",
        description="Scan network for devices",
        category="network",
        params=[
            FunctionParam("subnet", "string", "Subnet to scan", False, "auto"),
        ],
        returns="Device list",
        examples=[
            "scan network",
            "find devices on network",
            "list connected devices",
        ],
        shell_template="sq network scan",
    ))
    
    registry.add(RegisteredFunction(
        name="find_cameras",
        description="Find IP cameras on network",
        category="network",
        params=[],
        returns="Camera list with URLs",
        examples=[
            "find cameras",
            "scan for IP cameras",
            "list available cameras",
        ],
        shell_template="sq network find cameras --yaml",
    ))
    
    # =========================================================================
    # TRANSFORM FUNCTIONS
    # =========================================================================
    
    registry.add(RegisteredFunction(
        name="transform_json",
        description="Transform data to JSON format",
        category="transform",
        params=[
            FunctionParam("input", "string", "Input file or data", True),
        ],
        returns="JSON data",
        examples=[
            "convert to json",
            "format as json",
        ],
        shell_template="sq transform json --input {input}",
    ))
    
    registry.add(RegisteredFunction(
        name="transform_csv",
        description="Transform data to CSV format",
        category="transform",
        params=[
            FunctionParam("input", "string", "Input file or data", True),
        ],
        returns="CSV data",
        examples=[
            "convert to csv",
            "export as csv",
        ],
        shell_template="sq transform csv --input {input}",
    ))
    
    registry.add(RegisteredFunction(
        name="transform_base64",
        description="Encode/decode base64",
        category="transform",
        params=[
            FunctionParam("input", "string", "Input data", True),
            FunctionParam("decode", "boolean", "Decode instead of encode", False, False),
        ],
        returns="Encoded/decoded data",
        examples=[
            "encode to base64",
            "decode base64 string",
        ],
        shell_template="sq transform base64 --input {input}",
    ))


# =============================================================================
# LINUX SYSTEM COMMANDS
# =============================================================================

def _register_system_commands():
    """Register Linux system commands for network and system tasks."""
    
    # Network diagnostics
    registry.add(RegisteredFunction(
        name="ping",
        description="Ping a host to check connectivity",
        category="linux",
        params=[
            FunctionParam("host", "string", "Host to ping", True),
            FunctionParam("count", "integer", "Number of pings", False, 4),
        ],
        returns="Ping results",
        examples=[
            "ping google.com",
            "ping 192.168.1.1",
            "ping router 10 times",
        ],
        shell_template="ping -c {count} {host}",
    ))
    
    registry.add(RegisteredFunction(
        name="nmap",
        description="Scan ports on a host using nmap",
        category="linux",
        params=[
            FunctionParam("target", "string", "Host or IP to scan", True),
            FunctionParam("ports", "string", "Port range (e.g., 1-1000, 22,80,443)", False, "1-1000"),
            FunctionParam("scan_type", "string", "Scan type", False, "-sT", 
                         choices=["-sT", "-sS", "-sU", "-sV"]),
        ],
        returns="Open ports list",
        examples=[
            "nmap 192.168.1.1",
            "scan ports on server.com",
            "check open ports on router",
        ],
        shell_template="nmap {scan_type} -p {ports} {target}",
    ))
    
    registry.add(RegisteredFunction(
        name="traceroute",
        description="Trace network route to host",
        category="linux",
        params=[
            FunctionParam("host", "string", "Destination host", True),
        ],
        returns="Route hops",
        examples=[
            "traceroute google.com",
            "trace route to server",
        ],
        shell_template="traceroute {host}",
    ))
    
    registry.add(RegisteredFunction(
        name="dig",
        description="DNS lookup for a domain",
        category="linux",
        params=[
            FunctionParam("domain", "string", "Domain to lookup", True),
            FunctionParam("record_type", "string", "DNS record type", False, "A",
                         choices=["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA"]),
        ],
        returns="DNS records",
        examples=[
            "dig google.com",
            "lookup MX records for gmail.com",
        ],
        shell_template="dig {record_type} {domain}",
    ))
    
    registry.add(RegisteredFunction(
        name="curl",
        description="Make HTTP request with curl",
        category="linux",
        params=[
            FunctionParam("url", "string", "URL to fetch", True),
            FunctionParam("method", "string", "HTTP method", False, "GET",
                         choices=["GET", "POST", "PUT", "DELETE", "HEAD"]),
            FunctionParam("data", "string", "Request data (for POST/PUT)", False, None),
            FunctionParam("headers", "string", "Custom headers (key:value)", False, None),
        ],
        returns="HTTP response",
        examples=[
            "curl https://api.example.com",
            "post to webhook",
            "fetch json from api",
        ],
        shell_template="curl -X {method} {url}",
    ))
    
    registry.add(RegisteredFunction(
        name="wget",
        description="Download file from URL",
        category="linux",
        params=[
            FunctionParam("url", "string", "URL to download", True),
            FunctionParam("output", "string", "Output filename", False, None),
        ],
        returns="Downloaded file path",
        examples=[
            "download https://example.com/file.zip",
            "wget installer from github",
        ],
        shell_template="wget {url}",
    ))
    
    # System info
    registry.add(RegisteredFunction(
        name="df",
        description="Show disk space usage",
        category="linux",
        params=[
            FunctionParam("human", "boolean", "Human readable sizes", False, True),
        ],
        returns="Disk usage info",
        examples=[
            "show disk space",
            "how much space left",
            "df -h",
        ],
        shell_template="df -h",
    ))
    
    registry.add(RegisteredFunction(
        name="free",
        description="Show memory usage",
        category="linux",
        params=[],
        returns="Memory info",
        examples=[
            "show memory",
            "how much RAM",
            "free memory",
        ],
        shell_template="free -h",
    ))
    
    registry.add(RegisteredFunction(
        name="top",
        description="Show top processes",
        category="linux",
        params=[
            FunctionParam("count", "integer", "Number of processes to show", False, 10),
        ],
        returns="Process list",
        examples=[
            "top processes",
            "what's using CPU",
            "show running processes",
        ],
        shell_template="ps aux --sort=-%cpu | head -n {count}",
    ))
    
    registry.add(RegisteredFunction(
        name="uptime",
        description="Show system uptime",
        category="linux",
        params=[],
        returns="Uptime info",
        examples=[
            "uptime",
            "how long has system been running",
        ],
        shell_template="uptime",
    ))
    
    # File operations
    registry.add(RegisteredFunction(
        name="ls",
        description="List directory contents",
        category="linux",
        params=[
            FunctionParam("path", "string", "Directory path", False, "."),
            FunctionParam("all", "boolean", "Show hidden files", False, False),
        ],
        returns="File list",
        examples=[
            "list files",
            "ls /var/log",
            "show all files in home",
        ],
        shell_template="ls -la {path}",
    ))
    
    registry.add(RegisteredFunction(
        name="find",
        description="Find files matching pattern",
        category="linux",
        params=[
            FunctionParam("path", "string", "Search path", False, "."),
            FunctionParam("name", "string", "Filename pattern", True),
        ],
        returns="Found files",
        examples=[
            "find *.log files",
            "find all python files",
            "search for config files",
        ],
        shell_template="find {path} -name '{name}'",
    ))
    
    registry.add(RegisteredFunction(
        name="grep",
        description="Search for pattern in files",
        category="linux",
        params=[
            FunctionParam("pattern", "string", "Search pattern", True),
            FunctionParam("path", "string", "File or directory", False, "."),
            FunctionParam("recursive", "boolean", "Search recursively", False, True),
        ],
        returns="Matching lines",
        examples=[
            "grep error in logs",
            "search for TODO in code",
            "find password in files",
        ],
        shell_template="grep -r '{pattern}' {path}",
    ))
    
    # Process management
    registry.add(RegisteredFunction(
        name="kill",
        description="Kill a process by name or PID",
        category="linux",
        params=[
            FunctionParam("target", "string", "Process name or PID", True),
        ],
        returns="Kill result",
        examples=[
            "kill firefox",
            "stop process 1234",
        ],
        shell_template="pkill -f '{target}' || kill {target}",
    ))
    
    # Docker
    registry.add(RegisteredFunction(
        name="docker_ps",
        description="List running Docker containers",
        category="linux",
        params=[
            FunctionParam("all", "boolean", "Show all containers", False, False),
        ],
        returns="Container list",
        examples=[
            "docker containers",
            "running containers",
            "docker ps",
        ],
        shell_template="docker ps -a",
    ))
    
    registry.add(RegisteredFunction(
        name="docker_logs",
        description="Show Docker container logs",
        category="linux",
        params=[
            FunctionParam("container", "string", "Container name or ID", True),
            FunctionParam("tail", "integer", "Number of lines", False, 100),
        ],
        returns="Container logs",
        examples=[
            "logs for nginx container",
            "docker logs web",
        ],
        shell_template="docker logs --tail {tail} {container}",
    ))


# =============================================================================
# EXTERNAL PACKAGE REGISTRATION (PyPI packages like curllm)
# =============================================================================

def register_external_package(package_name: str, install: bool = True) -> bool:
    """
    Register functions from an external PyPI package.
    
    Args:
        package_name: Name of the package (e.g., 'curllm')
        install: Whether to install if not present
        
    Returns:
        True if registration successful
    """
    import importlib
    import subprocess
    import sys
    
    try:
        # Try to import package
        module = importlib.import_module(package_name)
    except ImportError:
        if install:
            print(f"📦 Installing {package_name}...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
                module = importlib.import_module(package_name)
            except Exception as e:
                print(f"❌ Failed to install {package_name}: {e}")
                return False
        else:
            return False
    
    # Check for streamware integration
    if hasattr(module, "streamware_functions"):
        # Package provides explicit function definitions
        for fn_def in module.streamware_functions:
            registry.add(RegisteredFunction(**fn_def))
        print(f"✅ Registered {len(module.streamware_functions)} functions from {package_name}")
        return True
    
    # Check for common patterns
    if package_name == "curllm":
        # Register curllm functions
        registry.add(RegisteredFunction(
            name="curllm",
            description="Query LLM via curl-like interface (supports multiple providers)",
            category="external",
            params=[
                FunctionParam("prompt", "string", "Prompt text", True),
                FunctionParam("model", "string", "Model name", False, "gpt-4"),
                FunctionParam("provider", "string", "API provider", False, "openai",
                             choices=["openai", "anthropic", "ollama", "groq"]),
            ],
            returns="LLM response",
            examples=[
                "curllm 'explain quantum computing'",
                "ask curllm about python",
            ],
            shell_template="curllm --model {model} --provider {provider} '{prompt}'",
        ))
        print(f"✅ Registered curllm functions")
        return True
    
    print(f"⚠️  Package {package_name} has no streamware integration")
    return False


# =============================================================================
# CONVERSATION VARIABLES
# =============================================================================

class ConversationVariables:
    """Store and retrieve variables during conversation."""
    
    def __init__(self):
        self._vars: Dict[str, Any] = {}
        self._history: List[Dict[str, Any]] = []
    
    def set(self, name: str, value: Any, persist: bool = True) -> None:
        """Set a variable."""
        self._vars[name] = value
        if persist:
            self._history.append({"action": "set", "name": name, "value": value})
    
    def get(self, name: str, default: Any = None) -> Any:
        """Get a variable."""
        return self._vars.get(name, default)
    
    def delete(self, name: str) -> bool:
        """Delete a variable."""
        if name in self._vars:
            del self._vars[name]
            self._history.append({"action": "delete", "name": name})
            return True
        return False
    
    def list(self) -> Dict[str, Any]:
        """List all variables."""
        return self._vars.copy()
    
    def clear(self) -> None:
        """Clear all variables."""
        self._vars.clear()
        self._history.append({"action": "clear"})
    
    def substitute(self, text: str) -> str:
        """Replace $var or ${var} with values."""
        import re
        
        def replace(match):
            var_name = match.group(1) or match.group(2)
            return str(self._vars.get(var_name, match.group(0)))
        
        # Match ${var} or $var patterns
        pattern = r'\$\{([^}]+)\}|\$([a-zA-Z_][a-zA-Z0-9_]*)'
        return re.sub(pattern, replace, text)
    
    def to_env(self) -> Dict[str, str]:
        """Export as environment variables."""
        return {f"SQ_VAR_{k.upper()}": str(v) for k, v in self._vars.items()}


# Global conversation variables
conversation_vars = ConversationVariables()


def _register_variable_functions():
    """Register functions for variable management."""
    
    registry.add(RegisteredFunction(
        name="set_variable",
        description="Set a conversation variable for later use",
        category="variables",
        params=[
            FunctionParam("name", "string", "Variable name", True),
            FunctionParam("value", "string", "Variable value", True),
        ],
        returns="Confirmation",
        examples=[
            "set camera to rtsp://...",
            "remember email as tom@example.com",
            "save server as 192.168.1.100",
        ],
        shell_template="echo 'Variable {name} set to {value}'",
    ))
    
    registry.add(RegisteredFunction(
        name="get_variable",
        description="Get value of a conversation variable",
        category="variables",
        params=[
            FunctionParam("name", "string", "Variable name", True),
        ],
        returns="Variable value",
        examples=[
            "what is camera",
            "show email variable",
            "get server address",
        ],
        shell_template="echo $SQ_VAR_{name}",
    ))
    
    registry.add(RegisteredFunction(
        name="list_variables",
        description="List all saved variables",
        category="variables",
        params=[],
        returns="Variable list",
        examples=[
            "list variables",
            "show all saved values",
            "what have I saved",
        ],
        shell_template="env | grep SQ_VAR_",
    ))
    
    registry.add(RegisteredFunction(
        name="clear_variables",
        description="Clear all saved variables",
        category="variables",
        params=[],
        returns="Confirmation",
        examples=[
            "clear all variables",
            "reset saved values",
        ],
        shell_template="echo 'Variables cleared'",
    ))


# Register all functions on import
_register_core_functions()
_register_system_commands()
_register_variable_functions()


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
    # New: External packages
    "register_external_package",
    # New: Conversation variables
    "conversation_vars",
    "ConversationVariables",
]
