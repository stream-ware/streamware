"""
Cross-platform Setup Utilities for Streamware

Handles:
- Dependency checking and installation
- TTS engine setup
- Configuration validation
- First-run setup prompts

Works on: Linux, macOS, Windows
"""

import logging
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class Platform(str, Enum):
    LINUX = "linux"
    MACOS = "darwin"
    WINDOWS = "windows"
    UNKNOWN = "unknown"


@dataclass
class Dependency:
    """Represents an installable dependency."""
    name: str
    check_cmd: List[str]  # Command to check if installed
    install_linux: Optional[str] = None  # apt install command
    install_macos: Optional[str] = None  # brew install command
    install_windows: Optional[str] = None  # choco/winget command
    install_pip: Optional[str] = None  # pip install command
    description: str = ""


# TTS Dependencies
TTS_DEPENDENCIES = {
    "pyttsx3": Dependency(
        name="pyttsx3",
        check_cmd=["python3", "-c", "import pyttsx3"],
        install_pip="pyttsx3",
        description="Cross-platform Python TTS (recommended)",
    ),
    "espeak": Dependency(
        name="espeak",
        check_cmd=["espeak", "--version"],
        install_linux="espeak",
        install_macos="espeak",
        description="Lightweight CLI TTS for Linux/macOS",
    ),
    "pico": Dependency(
        name="pico",
        check_cmd=["pico2wave", "--help"],
        install_linux="libttspico-utils",
        description="Better quality TTS for Linux",
    ),
    "festival": Dependency(
        name="festival",
        check_cmd=["festival", "--version"],
        install_linux="festival",
        description="Full-featured TTS for Linux",
    ),
}

# Core Dependencies
CORE_DEPENDENCIES = {
    "ffmpeg": Dependency(
        name="ffmpeg",
        check_cmd=["ffmpeg", "-version"],
        install_linux="ffmpeg",
        install_macos="ffmpeg",
        install_windows="ffmpeg",
        description="Video/audio processing (required for RTSP)",
    ),
    "requests": Dependency(
        name="requests",
        check_cmd=["python3", "-c", "import requests"],
        install_pip="requests",
        description="HTTP library",
    ),
    "pillow": Dependency(
        name="Pillow",
        check_cmd=["python3", "-c", "from PIL import Image"],
        install_pip="Pillow",
        description="Image processing",
    ),
}


def get_platform() -> Platform:
    """Detect current platform."""
    system = platform.system().lower()
    if system == "linux":
        return Platform.LINUX
    elif system == "darwin":
        return Platform.MACOS
    elif system == "windows":
        return Platform.WINDOWS
    return Platform.UNKNOWN


def check_dependency(dep: Dependency) -> bool:
    """Check if a dependency is installed."""
    try:
        if dep.check_cmd[0] == "python3":
            # Python import check
            result = subprocess.run(
                dep.check_cmd,
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        else:
            # System command check
            return shutil.which(dep.check_cmd[0]) is not None
    except Exception:
        return False


def get_install_command(dep: Dependency, plat: Platform) -> Optional[str]:
    """Get installation command for platform."""
    if dep.install_pip:
        return f"pip install {dep.install_pip}"
    
    if plat == Platform.LINUX and dep.install_linux:
        return f"sudo apt-get install -y {dep.install_linux}"
    elif plat == Platform.MACOS and dep.install_macos:
        return f"brew install {dep.install_macos}"
    elif plat == Platform.WINDOWS and dep.install_windows:
        return f"winget install {dep.install_windows}"
    
    return None


def install_dependency(dep: Dependency, interactive: bool = True) -> bool:
    """Install a dependency.
    
    Args:
        dep: Dependency to install
        interactive: If True, ask user before installing
        
    Returns:
        True if installed successfully
    """
    plat = get_platform()
    cmd = get_install_command(dep, plat)
    
    if not cmd:
        logger.warning(f"No install method for {dep.name} on {plat.value}")
        return False
    
    if interactive:
        print(f"\n   {dep.name} not found.")
        print(f"   Install with: {cmd}")
        try:
            response = input("   Install now? [Y/n]: ").strip().lower()
            if response and response not in ("y", "yes"):
                return False
        except (EOFError, KeyboardInterrupt):
            return False
    
    print(f"   Installing {dep.name}...")
    
    try:
        if cmd.startswith("pip"):
            result = subprocess.run(
                cmd.split(),
                capture_output=False,
                timeout=120
            )
        elif cmd.startswith("sudo"):
            result = subprocess.run(
                cmd.split(),
                capture_output=False,
                timeout=120
            )
        else:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=False,
                timeout=120
            )
        
        if result.returncode == 0:
            print(f"   ✅ {dep.name} installed successfully")
            return True
        else:
            print(f"   ❌ Failed to install {dep.name}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"   ❌ Installation timed out")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def check_tts_available() -> Tuple[bool, Optional[str]]:
    """Check if any TTS engine is available.
    
    Returns:
        (available, engine_name) tuple
    """
    plat = get_platform()
    
    # Platform-specific priority
    if plat == Platform.MACOS:
        priority = ["say", "pyttsx3"]
    elif plat == Platform.WINDOWS:
        priority = ["pyttsx3", "powershell"]
    else:  # Linux
        priority = ["pyttsx3", "espeak", "pico", "festival"]
    
    for engine in priority:
        if engine == "say":
            if shutil.which("say"):
                return True, "say"
        elif engine == "powershell":
            if shutil.which("powershell"):
                return True, "powershell"
        elif engine in TTS_DEPENDENCIES:
            if check_dependency(TTS_DEPENDENCIES[engine]):
                return True, engine
    
    return False, None


def ensure_tts_available(interactive: bool = True) -> bool:
    """Ensure at least one TTS engine is available.
    
    If none available and interactive, offer to install one.
    
    Returns:
        True if TTS is available after check
    """
    available, engine = check_tts_available()
    
    if available:
        return True
    
    if not interactive:
        return False
    
    plat = get_platform()
    print("\n⚠️  No TTS engine found.")
    
    # Offer installation options
    options = []
    
    if plat == Platform.LINUX:
        options = [
            ("pyttsx3", TTS_DEPENDENCIES["pyttsx3"]),
            ("espeak", TTS_DEPENDENCIES["espeak"]),
            ("pico", TTS_DEPENDENCIES["pico"]),
        ]
    elif plat == Platform.MACOS:
        print("   macOS 'say' command should be available by default.")
        options = [("pyttsx3", TTS_DEPENDENCIES["pyttsx3"])]
    elif plat == Platform.WINDOWS:
        options = [("pyttsx3", TTS_DEPENDENCIES["pyttsx3"])]
    
    if not options:
        return False
    
    print("\n   Available TTS options:")
    for i, (name, dep) in enumerate(options):
        cmd = get_install_command(dep, plat)
        print(f"   {i+1}. {name} - {dep.description}")
        if cmd:
            print(f"      Install: {cmd}")
    print(f"   {len(options)+1}. Skip (no TTS)")
    
    try:
        choice = input(f"\n   Choose [1-{len(options)+1}, default=1]: ").strip()
        if not choice:
            choice = "1"
        
        idx = int(choice) - 1
        if 0 <= idx < len(options):
            name, dep = options[idx]
            return install_dependency(dep, interactive=False)
        else:
            print("   Skipping TTS installation.")
            return False
            
    except (ValueError, EOFError, KeyboardInterrupt):
        return False


def check_core_dependencies() -> Dict[str, bool]:
    """Check all core dependencies.
    
    Returns:
        Dict mapping dependency name to availability
    """
    results = {}
    for name, dep in CORE_DEPENDENCIES.items():
        results[name] = check_dependency(dep)
    return results


def ensure_core_dependencies(interactive: bool = True) -> bool:
    """Ensure core dependencies are installed.
    
    Returns:
        True if all core deps are available
    """
    results = check_core_dependencies()
    missing = [name for name, available in results.items() if not available]
    
    if not missing:
        return True
    
    print(f"\n⚠️  Missing dependencies: {', '.join(missing)}")
    
    if not interactive:
        return False
    
    plat = get_platform()
    
    for name in missing:
        dep = CORE_DEPENDENCIES[name]
        install_dependency(dep, interactive=True)
    
    # Recheck
    results = check_core_dependencies()
    return all(results.values())


def update_env_file(key: str, value: str, env_path: Path = None) -> bool:
    """Update or add a key in .env file.
    
    Args:
        key: Environment variable name
        value: Value to set
        env_path: Path to .env file (default: current dir)
        
    Returns:
        True if successful
    """
    if env_path is None:
        env_path = Path(".env")
    
    lines = []
    key_found = False
    
    if env_path.exists():
        lines = env_path.read_text().splitlines()
        for i, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[i] = f"{key}={value}"
                key_found = True
                break
    
    if not key_found:
        lines.append(f"{key}={value}")
    
    try:
        env_path.write_text("\n".join(lines) + "\n")
        return True
    except Exception as e:
        logger.error(f"Failed to update .env: {e}")
        return False


def get_system_info() -> Dict[str, str]:
    """Get system information for diagnostics."""
    return {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "python_version": platform.python_version(),
        "architecture": platform.machine(),
    }


def run_first_time_setup(interactive: bool = True) -> bool:
    """Run first-time setup if needed.
    
    Checks for .streamware_configured flag file.
    
    Returns:
        True if setup completed or already done
    """
    config_flag = Path.home() / ".streamware_configured"
    
    if config_flag.exists():
        return True
    
    if not interactive:
        return False
    
    print("\n🚀 First-time Streamware Setup")
    print("=" * 40)
    
    # Check core dependencies
    ensure_core_dependencies(interactive=True)
    
    # Check TTS
    ensure_tts_available(interactive=True)
    
    # Mark as configured
    try:
        config_flag.touch()
    except Exception:
        pass
    
    print("\n✅ Setup complete!")
    return True
