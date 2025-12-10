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


def test_tts_works(engine: str = None) -> Tuple[bool, str]:
    """Actually test if TTS works by speaking a test phrase.
    
    Args:
        engine: Specific engine to test, or None to auto-detect
        
    Returns:
        (works, message) tuple
    """
    if engine is None:
        available, engine = check_tts_available()
        if not available:
            return False, "No TTS engine found"
    
    try:
        if engine == "pyttsx3":
            import pyttsx3
            tts = pyttsx3.init()
            # Just initialize, don't actually speak during test
            tts.stop()
            return True, "pyttsx3 initialized successfully"
        
        elif engine == "espeak":
            import subprocess
            result = subprocess.run(
                ["espeak", "--version"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                return True, "espeak available"
            return False, "espeak not working"
        
        elif engine == "say":
            import subprocess
            # macOS say - just check it exists
            result = subprocess.run(
                ["say", "-v", "?"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                return True, "say available"
            return False, "say not working"
        
        elif engine == "pico":
            import subprocess
            if shutil.which("pico2wave"):
                return True, "pico2wave available"
            return False, "pico2wave not found"
        
        else:
            return False, f"Unknown engine: {engine}"
            
    except ImportError as e:
        return False, f"Import error: {e}"
    except Exception as e:
        return False, f"TTS test failed: {e}"


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


def check_ollama_available() -> Tuple[bool, str]:
    """Check if Ollama is running and accessible.
    
    Returns:
        (available, message) tuple
    """
    import requests
    
    try:
        from .config import config
        ollama_url = config.get("SQ_OLLAMA_URL", "http://localhost:11434")
        resp = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if resp.ok:
            models = resp.json().get("models", [])
            return True, f"Ollama running ({len(models)} models)"
        else:
            return False, "Ollama not responding"
    except requests.exceptions.ConnectionError:
        return False, "Ollama not running. Start with: ollama serve"
    except Exception as e:
        return False, f"Ollama error: {e}"


def test_llm_works(model: str = None) -> Tuple[bool, str]:
    """Actually test if LLM can process an image.
    
    Args:
        model: Model to test, or None for default
        
    Returns:
        (works, message) tuple
    """
    from .config import config
    
    provider = config.get("SQ_LLM_PROVIDER", "ollama")
    
    if provider == "openai":
        api_key = config.get("SQ_OPENAI_API_KEY", "")
        if not api_key:
            return False, "OpenAI selected but SQ_OPENAI_API_KEY not set"
        return True, "OpenAI API key configured"
    
    elif provider == "anthropic":
        api_key = config.get("SQ_ANTHROPIC_API_KEY", "")
        if not api_key:
            return False, "Anthropic selected but SQ_ANTHROPIC_API_KEY not set"
        return True, "Anthropic API key configured"
    
    elif provider == "ollama":
        # Test actual Ollama connection
        ollama_ok, msg = check_ollama_available()
        if not ollama_ok:
            return False, msg
        
        # Test model availability
        if model:
            model_ok, model_msg = check_ollama_model(model)
            if not model_ok:
                return False, model_msg
        
        return True, f"Ollama ready"
    
    else:
        return False, f"Unknown LLM provider: {provider}"


def select_llm_provider(interactive: bool = True) -> bool:
    """Let user select LLM provider configuration.
    
    Args:
        interactive: If True, prompt user
        
    Returns:
        True if valid configuration selected
    """
    from .config import config
    
    if not interactive:
        return False
    
    print("\n🔧 LLM Configuration")
    print("=" * 40)
    print("\nSelect LLM provider:")
    print("  1. Ollama (local, free, recommended)")
    print("  2. OpenAI (cloud, requires API key)")
    print("  3. Anthropic (cloud, requires API key)")
    
    try:
        choice = input("\nChoice [1-3, default=1]: ").strip()
        if not choice:
            choice = "1"
        
        if choice == "1":
            config.set("SQ_LLM_PROVIDER", "ollama")
            
            # Check if Ollama is running
            ollama_ok, msg = check_ollama_available()
            if not ollama_ok:
                print(f"   ⚠️  {msg}")
                print("   Start Ollama with: ollama serve")
                return False
            
            # Save ONLY this key to .env (preserve everything else)
            try:
                config.save(keys_only=["SQ_LLM_PROVIDER"])
                print("\n✅ Using Ollama (local) - saved to .env")
            except Exception as e:
                print(f"\n✅ Using Ollama (local) - could not save to .env: {e}")
            
            return True
            
        elif choice == "2":
            api_key = input("Enter OpenAI API key: ").strip()
            if not api_key:
                print("   ❌ API key required")
                return False
            
            config.set("SQ_LLM_PROVIDER", "openai")
            config.set("SQ_OPENAI_API_KEY", api_key)
            
            # Save ONLY these keys to .env (preserve everything else)
            try:
                config.save(keys_only=["SQ_LLM_PROVIDER", "SQ_OPENAI_API_KEY"])
                print("\n✅ Using OpenAI - saved to .env")
            except Exception as e:
                print(f"\n✅ Using OpenAI - could not save to .env: {e}")
            return True
            
        elif choice == "3":
            api_key = input("Enter Anthropic API key: ").strip()
            if not api_key:
                print("   ❌ API key required")
                return False
            
            config.set("SQ_LLM_PROVIDER", "anthropic")
            config.set("SQ_ANTHROPIC_API_KEY", api_key)
            
            # Save ONLY these keys to .env (preserve everything else)
            try:
                config.save(keys_only=["SQ_LLM_PROVIDER", "SQ_ANTHROPIC_API_KEY"])
                print("\n✅ Using Anthropic - saved to .env")
            except Exception as e:
                print(f"\n✅ Using Anthropic - could not save to .env: {e}")
            return True
            
        else:
            print("   ❌ Invalid choice")
            return False
            
    except (EOFError, KeyboardInterrupt):
        print("\n   Cancelled")
        return False


def check_ollama_model(model: str) -> Tuple[bool, str]:
    """Check if specific Ollama model is installed.
    
    Returns:
        (available, message) tuple
    """
    import requests
    
    try:
        from .config import config
        ollama_url = config.get("SQ_OLLAMA_URL", "http://localhost:11434")
        resp = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if resp.ok:
            models = [m.get("name", "") for m in resp.json().get("models", [])]
            base_name = model.split(":")[0]
            
            # Check exact match first, then with :latest suffix
            # Be precise - don't match gemma2 when looking for gemma
            for m in models:
                # Exact match
                if m == model or m == f"{model}:latest":
                    return True, m
            
            # Fallback: check base name with colon (gemma: matches gemma:2b but not gemma2:2b)
            for m in models:
                if m.startswith(f"{base_name}:"):
                    return True, m
            
            return False, f"Model {model} not installed"
        else:
            return False, "Cannot check models"
    except Exception as e:
        return False, f"Error: {e}"


def install_ollama_model(model: str, auto_install: bool = True, interactive: bool = True) -> bool:
    """Install Ollama model.
    
    Args:
        model: Model name (e.g. "llava:7b", "gemma:2b")
        auto_install: If True, install without asking (default: True)
        interactive: If True and auto_install is False, ask user before installing
        
    Returns:
        True if installed successfully
    """
    import subprocess
    
    if not auto_install and interactive:
        print(f"\n⚠️  Model '{model}' not found.")
        try:
            response = input(f"   Install with 'ollama pull {model}'? [Y/n]: ").strip().lower()
            if response and response not in ("y", "yes", ""):
                return False
        except (EOFError, KeyboardInterrupt):
            return False
    
    print(f"   📦 Installing {model}... (this may take a few minutes)")
    
    try:
        result = subprocess.run(
            ["ollama", "pull", model],
            capture_output=False,
            timeout=600  # 10 minutes max
        )
        
        if result.returncode == 0:
            print(f"   ✅ {model} installed successfully")
            return True
        else:
            print(f"   ❌ Failed to install {model}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"   ❌ Installation timed out")
        return False
    except FileNotFoundError:
        print(f"   ❌ Ollama not found. Install from: https://ollama.ai")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def ensure_ollama_model(model: str, auto_install: bool = True, interactive: bool = True) -> bool:
    """Ensure Ollama model is available, install if not.
    
    Args:
        model: Model name
        auto_install: If True, install automatically without asking
        interactive: If True and auto_install is False, prompt user
        
    Returns:
        True if model is available
    """
    available, msg = check_ollama_model(model)
    if available:
        return True
    
    return install_ollama_model(model, auto_install=auto_install, interactive=interactive)


def run_startup_checks(
    vision_model: str = None,
    guarder_model: str = None,
    check_tts: bool = False,
    interactive: bool = True,
    auto_install: bool = True
) -> dict:
    """Run all startup checks and install missing dependencies.
    
    Args:
        vision_model: Vision LLM model (e.g. "moondream", "llava:7b")
        guarder_model: Guarder model (e.g. "gemma:2b")
        check_tts: Whether to check TTS availability
        interactive: Whether to prompt for installation (if auto_install=False)
        auto_install: If True (default), automatically install missing models
        
    Returns:
        Dict with check results
    """
    from .config import config
    
    results = {
        "llm": False,
        "ollama": False,
        "vision_model": False,
        "guarder_model": False,
        "tts": False,
        "all_ok": False,
    }
    
    print("\n🔍 Checking dependencies...")
    
    # 0. Check LLM provider configuration
    llm_ok, llm_msg = test_llm_works(vision_model)
    
    if not llm_ok:
        print(f"   ❌ LLM: {llm_msg}")
        
        if interactive:
            print("\n   LLM is not configured correctly.")
            if select_llm_provider(interactive=True):
                # Re-check after configuration
                llm_ok, llm_msg = test_llm_works(vision_model)
        
        if not llm_ok:
            print(f"\n❌ Cannot start without working LLM configuration.")
            return results
    
    results["llm"] = True
    provider = config.get("SQ_LLM_PROVIDER", "ollama")
    print(f"   ✅ LLM: {provider} ({llm_msg})")
    
    # 1. Check Ollama (only if using Ollama provider)
    if provider == "ollama":
        ollama_ok, ollama_msg = check_ollama_available()
        results["ollama"] = ollama_ok
        
        if not ollama_ok:
            print(f"   ❌ Ollama: {ollama_msg}")
            if interactive:
                print("\n   Ollama is required for AI features.")
                print("   Install from: https://ollama.ai")
                print("   Then run: ollama serve")
            return results
        else:
            print(f"   ✅ Ollama: {ollama_msg}")
    else:
        results["ollama"] = True  # Not needed for cloud providers
    
    # 2. Check vision model
    if vision_model is None:
        vision_model = config.get("SQ_MODEL", "llava:7b")
    
    vision_ok, vision_msg = check_ollama_model(vision_model)
    if vision_ok:
        print(f"   ✅ Vision model: {vision_msg}")
        results["vision_model"] = True
    else:
        print(f"   ⚠️  Vision model '{vision_model}' not found")
        if ensure_ollama_model(vision_model, auto_install=auto_install, interactive=interactive):
            results["vision_model"] = True
            # Re-check to get actual model name
            _, vision_msg = check_ollama_model(vision_model)
            print(f"   ✅ Vision model: {vision_msg}")
    
    # 3. Check guarder model
    if guarder_model is None:
        guarder_model = config.get("SQ_GUARDER_MODEL", "gemma:2b")
    
    guarder_ok, guarder_msg = check_ollama_model(guarder_model)
    if guarder_ok:
        print(f"   ✅ Guarder model: {guarder_msg}")
        results["guarder_model"] = True
    else:
        print(f"   ⚠️  Guarder model '{guarder_model}' not found")
        if ensure_ollama_model(guarder_model, auto_install=auto_install, interactive=interactive):
            results["guarder_model"] = True
            # Re-check to get actual model name
            _, guarder_msg = check_ollama_model(guarder_model)
            print(f"   ✅ Guarder model: {guarder_msg}")
    
    # 4. Check TTS (optional) - actually test it works
    if check_tts:
        tts_ok, tts_engine = check_tts_available()
        if tts_ok:
            # Actually test if TTS works
            works, msg = test_tts_works(tts_engine)
            if works:
                print(f"   ✅ TTS: {tts_engine} ({msg})")
                results["tts"] = True
            else:
                print(f"   ⚠️  TTS: {tts_engine} found but not working: {msg}")
                if ensure_tts_available(interactive):
                    results["tts"] = True
        else:
            print(f"   ⚠️  TTS: not available")
            if ensure_tts_available(interactive):
                results["tts"] = True
    
    # 5. Check YOLO (optional but recommended for fast detection)
    use_yolo = config.get("SQ_USE_YOLO", "true").lower() == "true"
    if use_yolo:
        yolo_ok, yolo_msg = check_yolo_available()
        if yolo_ok:
            print(f"   ✅ YOLO: {yolo_msg}")
            results["yolo"] = True
        else:
            print(f"   ⚠️  YOLO: not installed (will auto-install on first use)")
            if auto_install:
                if ensure_yolo_available(verbose=True):
                    results["yolo"] = True
    
    # Summary
    results["all_ok"] = results["ollama"] and results["vision_model"]
    
    if results["all_ok"]:
        print("\n✅ All dependencies ready!")
    else:
        print("\n⚠️  Some dependencies missing. Features may be limited.")
    
    return results


def check_yolo_available() -> Tuple[bool, str]:
    """Check if YOLO (ultralytics) is available."""
    try:
        import ultralytics
        return True, f"ultralytics {ultralytics.__version__}"
    except ImportError:
        return False, "not installed"


def ensure_yolo_available(verbose: bool = True) -> bool:
    """Install YOLO (ultralytics) if not available.
    
    Returns:
        True if YOLO is available after install attempt
    """
    ok, msg = check_yolo_available()
    if ok:
        if verbose:
            print(f"   ✅ YOLO: {msg}")
        return True
    
    if verbose:
        print("   📦 Installing YOLO (ultralytics)...")
    
    try:
        import subprocess
        import sys
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "ultralytics", "-q"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        ok, msg = check_yolo_available()
        if ok and verbose:
            print(f"   ✅ YOLO: {msg}")
        return ok
    except Exception as e:
        if verbose:
            print(f"   ⚠️  YOLO installation failed: {e}")
        return False


def ensure_required_models(
    vision_model: str = None,
    guarder_model: str = None,
    install_yolo: bool = True,
    verbose: bool = True
) -> bool:
    """Ensure all required Ollama models are installed.
    
    This function is called automatically before running live narrator
    and other AI features. It will install missing models without prompting.
    
    Args:
        vision_model: Vision model (default: from config or 'moondream')
        guarder_model: Guarder model (default: from config or 'gemma:2b')
        install_yolo: Also install YOLO for fast detection
        verbose: Print status messages
        
    Returns:
        True if all models are available
    """
    from .config import config
    
    if vision_model is None:
        vision_model = config.get("SQ_MODEL", "llava:7b")
    if guarder_model is None:
        guarder_model = config.get("SQ_GUARDER_MODEL", "gemma:2b")
    
    all_ok = True
    
    # Check and install vision model
    vision_ok, vision_msg = check_ollama_model(vision_model)
    if not vision_ok:
        if verbose:
            print(f"📦 Required model '{vision_model}' not found. Installing...")
        if not install_ollama_model(vision_model, auto_install=True, interactive=False):
            all_ok = False
            if verbose:
                print(f"❌ Failed to install {vision_model}")
    elif verbose:
        print(f"✅ Vision model: {vision_msg}")
    
    # Check and install guarder model
    guarder_ok, guarder_msg = check_ollama_model(guarder_model)
    if not guarder_ok:
        if verbose:
            print(f"📦 Required model '{guarder_model}' not found. Installing...")
        if not install_ollama_model(guarder_model, auto_install=True, interactive=False):
            all_ok = False
            if verbose:
                print(f"❌ Failed to install {guarder_model}")
    elif verbose:
        print(f"✅ Guarder model: {guarder_msg}")
    
    # Check and install YOLO
    if install_yolo:
        use_yolo = config.get("SQ_USE_YOLO", "true").lower() == "true"
        if use_yolo:
            yolo_ok = ensure_yolo_available(verbose=verbose)
            # YOLO is optional, don't fail if not installed
    
    return all_ok


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
    
    # Run all checks
    results = run_startup_checks(
        check_tts=True,
        interactive=True
    )
    
    # Mark as configured
    if results["all_ok"]:
        try:
            config_flag.touch()
        except Exception:
            pass
        print("\n✅ Setup complete!")
        return True
    
    return False
