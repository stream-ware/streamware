"""
Streamware Configuration Module

Handles loading configuration from:
1. .env file
2. Environment variables
3. Default values

Usage:
    from streamware.config import config
    
    model = config.get("SQ_MODEL", "llava")
    config.set("SQ_MODEL", "llava:13b")
    config.save()
"""

__all__ = ["config", "Config", "DEFAULTS"]

import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# Default configuration values
DEFAULTS = {
    # AI / LLM - balanced for accuracy
    "SQ_MODEL": "llava:7b",            # Good vision model (accurate person detection)
    "SQ_OLLAMA_URL": "http://localhost:11434",
    "SQ_OPENAI_API_KEY": "",
    "SQ_ANTHROPIC_API_KEY": "",
    "SQ_LLM_PROVIDER": "ollama",
    "SQ_LLM_TIMEOUT": "30",
    "SQ_GUARDER_MODEL": "gemma:2b",   # Small model for response validation (fast)
    "SQ_USE_GUARDER": "true",          # LLM-based response filtering (default: on)
    "SQ_FAST_CAPTURE": "true",         # Persistent RTSP connection (10x faster)
    
    # Audio / Voice
    "SQ_STT_PROVIDER": "google",
    "SQ_WHISPER_MODEL": "base",
    "SQ_TTS_ENGINE": "auto",      # auto, pyttsx3, espeak, say, powershell
    "SQ_TTS_VOICE": "",          # Preferred TTS voice name (engine-specific)
    "SQ_TTS_RATE": "150",        # TTS speech rate (approx. words per minute)
    
    # Stream Analysis
    "SQ_STREAM_MODE": "track",         # track mode for intelligent movement detection
    "SQ_STREAM_INTERVAL": "2",         # 2 seconds between frames (faster for tracking)
    "SQ_STREAM_DURATION": "30",        # 1 minute default
    "SQ_STREAM_FOCUS": "person",       # default focus on person tracking
    "SQ_STREAM_FRAMES_DIR": "",
    "SQ_RAMDISK_PATH": "/dev/shm/streamware",
    "SQ_RAMDISK_ENABLED": "true",
    "SQ_RAMDISK_SIZE_MB": "512",
    "SQ_CAPTURE_FPS": "0.5",
    "SQ_IMAGE_MAX_SIZE": "512",
    "SQ_IMAGE_QUALITY": "75",
    "SQ_USE_CACHE": "true",
    
    # Detection Settings (descriptive)
    "SQ_SENSITIVITY": "medium",      # ultra, high, medium, low, minimal
    "SQ_DETECT": "any",              # person, vehicle, motion, package, animal, bird, any
    "SQ_SPEED": "normal",            # realtime, fast, normal, slow, thorough
    
    # Animal Detection
    "SQ_ANIMAL_FOCUS": "all",        # all, bird, cat, dog, pet, wildlife
    "SQ_MOTION_THRESHOLD": "15",     # 0-100 (lower = more sensitive, 15 is good for indoor)
    "SQ_MIN_REGION": "500",          # minimum region size in pixels
    "SQ_MIN_CHANGE": "0.0",          # minimum change percent (0.0 = always check, 0.1 = very sensitive)
    "SQ_FRAME_SCALE": "0.3",         # downscale factor for motion detection (0.1-1.0)
    
    # YOLO Detection (auto-installed on first use)
    "SQ_USE_YOLO": "true",           # Use YOLO for detection (faster, more accurate)
    "SQ_YOLO_MODEL": "yolov8n",      # YOLO model: yolov8n (fast), yolov8s, yolov8m, yolov8l, yolov8x (accurate)
    "SQ_YOLO_CONFIDENCE": "0.25",    # Minimum confidence for YOLO detection
    
    # Network
    "SQ_NETWORK_SUBNET": "",
    "SQ_NETWORK_TIMEOUT": "10",
    "SQ_NETWORK_DEEP": "false",
    
    # RTSP
    "SQ_RTSP_USER": "admin",
    "SQ_RTSP_PASS": "admin",
    "SQ_RTSP_PORT": "554",
    
    # Image Optimization (for LLM vision processing)
    "SQ_IMAGE_PRESET": "balanced",  # fast, balanced, quality, minimal
    "SQ_IMAGE_MAX_SIZE": "512",     # max dimension in pixels
    "SQ_IMAGE_QUALITY": "65",       # JPEG quality 1-100
    "SQ_IMAGE_POSTERIZE": "0",      # 0=off, 8-256=color count
    "SQ_IMAGE_GRAYSCALE": "false",  # convert to grayscale
    
    # Output
    "SQ_OUTPUT_FORMAT": "yaml",
    "SQ_REPORTS_DIR": "./reports",
    "SQ_REPORT_INCLUDE_IMAGES": "true",
    
    # Email
    "SQ_SMTP_HOST": "smtp.gmail.com",
    "SQ_SMTP_PORT": "587",
    "SQ_SMTP_USER": "",
    "SQ_SMTP_PASS": "",
    "SQ_EMAIL_FROM": "",
    "SQ_EMAIL_TO": "",
    
    # Slack
    "SQ_SLACK_WEBHOOK": "",
    "SQ_SLACK_CHANNEL": "alerts",
    
    # Telegram
    "SQ_TELEGRAM_BOT_TOKEN": "",
    "SQ_TELEGRAM_CHAT_ID": "",
    
    # Database
    "SQ_POSTGRES_HOST": "localhost",
    "SQ_POSTGRES_PORT": "5432",
    "SQ_POSTGRES_USER": "postgres",
    "SQ_POSTGRES_PASS": "",
    "SQ_POSTGRES_DB": "streamware",
    
    # Kafka
    "SQ_KAFKA_BROKERS": "localhost:9092",
    "SQ_KAFKA_GROUP_ID": "streamware",
    
    # SSH
    "SQ_SSH_USER": "",
    "SQ_SSH_KEY": "~/.ssh/id_rsa",
    "SQ_SSH_PORT": "22",
    
    # Web UI
    "SQ_WEB_HOST": "0.0.0.0",
    "SQ_WEB_PORT": "8080",
    "SQ_WEB_DEBUG": "false",
    
    # Logging
    "SQ_LOG_LEVEL": "INFO",
    "SQ_LOG_FILE": "",
}

# Configuration categories for web UI
CONFIG_CATEGORIES = {
    "AI / LLM": [
        ("SQ_MODEL", "Vision Model", "AI model for image analysis (llava:13b recommended)"),
        ("SQ_OLLAMA_URL", "Ollama URL", "Ollama server URL"),
        ("SQ_OPENAI_API_KEY", "OpenAI API Key", "API key for OpenAI GPT models"),
        ("SQ_ANTHROPIC_API_KEY", "Anthropic API Key", "API key for Claude models"),
        ("SQ_LLM_PROVIDER", "LLM Provider", "Default provider: ollama, openai, anthropic"),
    ],
    "Voice / Audio": [
        ("SQ_STT_PROVIDER", "STT Provider", "Speech-to-text provider (google, whisper_local, whisper_api)"),
        ("SQ_WHISPER_MODEL", "Whisper Model", "Model size for local Whisper (tiny, base, small, medium, large)"),
        ("SQ_TTS_ENGINE", "TTS Engine", "Text-to-speech engine: auto, pyttsx3, espeak, say, powershell"),
        ("SQ_TTS_VOICE", "TTS Voice", "Preferred TTS voice name (depends on engine)"),
        ("SQ_TTS_RATE", "TTS Rate", "Speech rate (words per minute, e.g. 150)"),
    ],
    "Stream Analysis": [
        ("SQ_STREAM_MODE", "Default Mode", "Analysis mode: full, stream, diff"),
        ("SQ_STREAM_INTERVAL", "Interval (seconds)", "Seconds between frame captures"),
        ("SQ_STREAM_DURATION", "Duration (seconds)", "Total analysis duration (0=infinite)"),
        ("SQ_STREAM_FOCUS", "Focus Target", "Detection focus: person, animal, vehicle, etc."),
        ("SQ_STREAM_SENSITIVITY", "Sensitivity", "Detection sensitivity: low, medium, high"),
        ("SQ_STREAM_FRAMES_DIR", "Frames Directory", "Save captured frames to this directory"),
        ("SQ_RAMDISK_PATH", "RAM Disk Path", "Path for RAM disk frame storage (default: /dev/shm/streamware)"),
        ("SQ_RAMDISK_ENABLED", "RAM Disk Enabled", "Use RAM disk for faster frame I/O (true/false)"),
        ("SQ_RAMDISK_SIZE_MB", "RAM Disk Size (MB)", "Maximum RAM disk size in megabytes"),
        ("SQ_CAPTURE_FPS", "Capture FPS", "Frames per second to capture from stream"),
    ],
    "Network Scanning": [
        ("SQ_NETWORK_SUBNET", "Default Subnet", "Subnet to scan (empty = auto-detect)"),
        ("SQ_NETWORK_TIMEOUT", "Timeout (seconds)", "Scan timeout"),
        ("SQ_NETWORK_DEEP", "Deep Scan", "Enable deep scan by default (true/false)"),
    ],
    "Camera / RTSP": [
        ("SQ_RTSP_USER", "Default Username", "Default RTSP username"),
        ("SQ_RTSP_PASS", "Default Password", "Default RTSP password"),
        ("SQ_RTSP_PORT", "Default Port", "Default RTSP port"),
    ],
    "Output Settings": [
        ("SQ_OUTPUT_FORMAT", "Default Format", "Output format: yaml, json, table, html"),
        ("SQ_REPORTS_DIR", "Reports Directory", "Directory for HTML reports"),
        ("SQ_REPORT_INCLUDE_IMAGES", "Include Images", "Include base64 images in reports (true/false)"),
    ],
    "Email Alerts": [
        ("SQ_SMTP_HOST", "SMTP Host", "SMTP server hostname"),
        ("SQ_SMTP_PORT", "SMTP Port", "SMTP server port"),
        ("SQ_SMTP_USER", "SMTP Username", "SMTP authentication username"),
        ("SQ_SMTP_PASS", "SMTP Password", "SMTP authentication password"),
        ("SQ_EMAIL_FROM", "From Address", "Sender email address"),
        ("SQ_EMAIL_TO", "To Address", "Recipient email address"),
    ],
    "Slack Alerts": [
        ("SQ_SLACK_WEBHOOK", "Webhook URL", "Slack webhook URL"),
        ("SQ_SLACK_CHANNEL", "Channel", "Default Slack channel"),
    ],
    "Telegram Alerts": [
        ("SQ_TELEGRAM_BOT_TOKEN", "Bot Token", "Telegram bot token"),
        ("SQ_TELEGRAM_CHAT_ID", "Chat ID", "Telegram chat ID"),
    ],
    "Database": [
        ("SQ_POSTGRES_HOST", "Host", "PostgreSQL hostname"),
        ("SQ_POSTGRES_PORT", "Port", "PostgreSQL port"),
        ("SQ_POSTGRES_USER", "Username", "PostgreSQL username"),
        ("SQ_POSTGRES_PASS", "Password", "PostgreSQL password"),
        ("SQ_POSTGRES_DB", "Database", "PostgreSQL database name"),
    ],
    "Kafka": [
        ("SQ_KAFKA_BROKERS", "Brokers", "Kafka broker addresses"),
        ("SQ_KAFKA_GROUP_ID", "Group ID", "Kafka consumer group ID"),
    ],
    "SSH": [
        ("SQ_SSH_USER", "Default User", "Default SSH username"),
        ("SQ_SSH_KEY", "Key Path", "Path to SSH private key"),
        ("SQ_SSH_PORT", "Default Port", "Default SSH port"),
    ],
    "Web UI": [
        ("SQ_WEB_HOST", "Host", "Web server host"),
        ("SQ_WEB_PORT", "Port", "Web server port"),
        ("SQ_WEB_DEBUG", "Debug Mode", "Enable debug mode (true/false)"),
    ],
    "Logging": [
        ("SQ_LOG_LEVEL", "Log Level", "Logging level: DEBUG, INFO, WARNING, ERROR"),
        ("SQ_LOG_FILE", "Log File", "Path to log file (empty = console only)"),
    ],
}


class Config:
    """Configuration manager for Streamware"""
    
    def __init__(self):
        self._config: Dict[str, str] = {}
        self._env_file: Optional[Path] = None
        self._load()
    
    def _find_env_file(self) -> Optional[Path]:
        """Find .env file in current directory or parent directories"""
        current = Path.cwd()
        
        # Check current and parent directories
        for _ in range(5):
            env_path = current / ".env"
            if env_path.exists():
                return env_path
            current = current.parent
        
        return None
    
    def _load(self):
        """Load configuration from .env file and environment"""
        # Start with defaults
        self._config = DEFAULTS.copy()
        
        # Load .env file if exists
        self._env_file = self._find_env_file()
        if self._env_file:
            self._load_env_file(self._env_file)
        
        # Override with environment variables
        for key in DEFAULTS.keys():
            env_val = os.environ.get(key)
            if env_val is not None:
                self._config[key] = env_val
    
    def _load_env_file(self, path: Path):
        """Load configuration from .env file"""
        try:
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, _, value = line.partition("=")
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key in DEFAULTS:
                            self._config[key] = value
        except Exception:
            pass
    
    def get(self, key: str, default: Any = None) -> str:
        """Get configuration value"""
        return self._config.get(key, default or DEFAULTS.get(key, ""))
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get configuration value as boolean"""
        val = self.get(key, str(default))
        return val.lower() in ("true", "1", "yes", "on")
    
    def get_int(self, key: str, default: int = 0) -> int:
        """Get configuration value as integer"""
        try:
            return int(self.get(key, str(default)))
        except ValueError:
            return default
    
    def set(self, key: str, value: str):
        """Set configuration value"""
        self._config[key] = str(value)
    
    def save(self, path: Optional[Path] = None, full: bool = False, keys_only: List[str] = None):
        """Save configuration to .env file.
        
        Args:
            path: Path to save to (default: current .env file)
            full: If True, write all values. If False, only update existing keys.
            keys_only: If provided, only update these specific keys (safest option)
        """
        if path is None:
            path = self._env_file or Path.cwd() / ".env"
        
        # If keys_only specified, do minimal update
        if keys_only and path.exists():
            existing_lines = []
            try:
                with open(path, "r") as f:
                    existing_lines = f.readlines()
            except Exception:
                pass
            
            if existing_lines:
                updated_lines = []
                for line in existing_lines:
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#") and "=" in stripped:
                        key = stripped.split("=", 1)[0].strip()
                        if key in keys_only and key in self._config:
                            updated_lines.append(f"{key}={self._config[key]}\n")
                        else:
                            updated_lines.append(line)
                    else:
                        updated_lines.append(line)
                
                with open(path, "w") as f:
                    f.writelines(updated_lines)
                
                self._env_file = path
                return
        
        # Incremental save - update only keys in _config, preserve everything else
        if path.exists() and not full:
            existing_lines = []
            try:
                with open(path, "r") as f:
                    existing_lines = f.readlines()
            except Exception:
                pass
            
            if existing_lines:
                updated_lines = []
                for line in existing_lines:
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#") and "=" in stripped:
                        key = stripped.split("=", 1)[0].strip()
                        if key in self._config:
                            updated_lines.append(f"{key}={self._config[key]}\n")
                        else:
                            # Preserve unknown keys (user's custom variables)
                            updated_lines.append(line)
                    else:
                        updated_lines.append(line)
                
                with open(path, "w") as f:
                    f.writelines(updated_lines)
                
                self._env_file = path
                return
        
        # Full save - only when explicitly requested or file doesn't exist
        if full or not path.exists():
            lines = []
            for category, items in CONFIG_CATEGORIES.items():
                lines.append(f"\n# {category}")
                for key, label, desc in items:
                    value = self._config.get(key, DEFAULTS.get(key, ""))
                    lines.append(f"{key}={value}")
            
            with open(path, "w") as f:
                f.write("# Streamware Configuration\n")
                f.write("# Generated by: sq config --save\n")
                f.write("\n".join(lines))
        
        self._env_file = path
    
    def to_dict(self) -> Dict[str, str]:
        """Get all configuration as dictionary"""
        return self._config.copy()
    
    def reload(self):
        """Reload configuration from files"""
        self._load()


# Global config instance
config = Config()


def get_config_web_html() -> str:
    """Generate HTML for web configuration panel"""
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Streamware Configuration</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
</head>
<body class="bg-gray-900 text-white min-h-screen">
    <div class="container mx-auto px-4 py-8 max-w-4xl">
        <header class="mb-8">
            <h1 class="text-3xl font-bold flex items-center gap-3">
                <i class="fas fa-cog text-blue-400"></i>
                Streamware Configuration
            </h1>
            <p class="text-gray-400 mt-2">Configure your Streamware settings</p>
        </header>
        
        <div id="status" class="hidden mb-4 p-4 rounded-lg"></div>
        
        <form id="configForm" class="space-y-8">
"""
    
    for category, items in CONFIG_CATEGORIES.items():
        icon_map = {
            "AI / LLM": "fa-robot",
            "Stream Analysis": "fa-video",
            "Network Scanning": "fa-network-wired",
            "Camera / RTSP": "fa-camera",
            "Output Settings": "fa-file-export",
            "Email Alerts": "fa-envelope",
            "Slack Alerts": "fa-slack",
            "Telegram Alerts": "fa-telegram",
            "Database": "fa-database",
            "Kafka": "fa-stream",
            "SSH": "fa-terminal",
            "Web UI": "fa-globe",
            "Logging": "fa-list",
        }
        icon = icon_map.get(category, "fa-cog")
        
        html += f"""
            <div class="bg-gray-800 rounded-lg p-6">
                <h2 class="text-xl font-semibold mb-4 flex items-center gap-2">
                    <i class="fas {icon} text-blue-400"></i>
                    {category}
                </h2>
                <div class="grid gap-4">
"""
        
        for key, label, desc in items:
            value = config.get(key, "")
            input_type = "password" if "PASS" in key or "KEY" in key or "TOKEN" in key else "text"
            
            html += f"""
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-2 items-center">
                        <label class="text-gray-300 font-medium" for="{key}">{label}</label>
                        <input type="{input_type}" 
                               id="{key}" 
                               name="{key}" 
                               value="{value}"
                               class="col-span-2 bg-gray-700 border border-gray-600 rounded px-3 py-2 
                                      focus:outline-none focus:border-blue-500"
                               placeholder="{desc}">
                    </div>
"""
        
        html += """
                </div>
            </div>
"""
    
    html += """
            <div class="flex gap-4 justify-end">
                <button type="button" onclick="resetForm()" 
                        class="px-6 py-2 bg-gray-600 hover:bg-gray-500 rounded-lg transition">
                    <i class="fas fa-undo mr-2"></i>Reset
                </button>
                <button type="submit" 
                        class="px-6 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg transition">
                    <i class="fas fa-save mr-2"></i>Save Configuration
                </button>
            </div>
        </form>
        
        <footer class="mt-8 pt-4 border-t border-gray-700 text-gray-500 text-sm">
            <p>Configuration file: <code class="bg-gray-800 px-2 py-1 rounded">.env</code></p>
            <p class="mt-1">CLI: <code class="bg-gray-800 px-2 py-1 rounded">sq config --show</code></p>
        </footer>
    </div>
    
    <script>
        document.getElementById('configForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData.entries());
            
            try {
                const response = await fetch('/api/config', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                showStatus(result.success ? 'success' : 'error', result.message);
            } catch (error) {
                showStatus('error', 'Failed to save: ' + error.message);
            }
        });
        
        function showStatus(type, message) {
            const status = document.getElementById('status');
            status.className = type === 'success' 
                ? 'mb-4 p-4 rounded-lg bg-green-900 text-green-200'
                : 'mb-4 p-4 rounded-lg bg-red-900 text-red-200';
            status.textContent = message;
            status.classList.remove('hidden');
            setTimeout(() => status.classList.add('hidden'), 3000);
        }
        
        function resetForm() {
            location.reload();
        }
    </script>
</body>
</html>
"""
    return html


def run_config_web(host: str = "0.0.0.0", port: int = 8080):
    """Run web configuration panel"""
    try:
        from flask import Flask, request, jsonify, send_from_directory
    except ImportError:
        print("Flask required. Install: pip install flask")
        return
    
    app = Flask(__name__)
    
    @app.route("/")
    def index():
        return get_config_web_html()
    
    @app.route("/api/config", methods=["GET"])
    def get_config():
        return jsonify(config.to_dict())
    
    @app.route("/api/config", methods=["POST"])
    def save_config():
        try:
            data = request.json
            for key, value in data.items():
                if key in DEFAULTS:
                    config.set(key, value)
            config.save(keys_only=list(data.keys()))
            return jsonify({"success": True, "message": "Configuration saved to .env"})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)})
    
    print(f"\n🔧 Streamware Configuration Panel")
    print(f"   Open: http://localhost:{port}")
    print(f"   Press Ctrl+C to stop\n")
    
    app.run(host=host, port=port, debug=False)
