"""
Streamware Setup Wizard

Detects environment and configures Streamware automatically.
"""

import os
import sys
import requests
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from .config import config

def check_ollama() -> Tuple[bool, List[str], str]:
    """
    Check if Ollama is running and get available models.
    Returns (is_running, models, url)
    """
    url = config.get("SQ_OLLAMA_URL", "http://localhost:11434")
    try:
        response = requests.get(f"{url}/api/tags", timeout=2)
        if response.status_code == 200:
            data = response.json()
            models = [m["name"] for m in data.get("models", [])]
            return True, models, url
    except Exception:
        pass
    return False, [], url

def check_env_key(provider_name: str, key_names: List[str]) -> bool:
    """Check if any of the keys exist in environment or config"""
    for key in key_names:
        if os.environ.get(key) or config.get(key):
            return True
    return False

def check_providers() -> Dict[str, bool]:
    """Check for API keys for various providers"""
    providers = {
        "openai": ["OPENAI_API_KEY", "SQ_OPENAI_API_KEY"],
        "anthropic": ["ANTHROPIC_API_KEY", "SQ_ANTHROPIC_API_KEY"],
        "groq": ["GROQ_API_KEY"],
        "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "deepseek": ["DEEPSEEK_API_KEY"],
        "mistral": ["MISTRAL_API_KEY"],
    }
    
    results = {}
    for provider, keys in providers.items():
        results[provider] = check_env_key(provider, keys)
    return results

def run_setup(interactive: bool = True):
    """
    Run the setup wizard.
    
    If interactive is True, asks for confirmation.
    If interactive is False, applies best defaults automatically.
    """
    # Detect non-interactive environment (CI, Docker, pipes)
    if interactive and (not sys.stdin.isatty() or os.environ.get("CI") or os.environ.get("NON_INTERACTIVE")):
        print("⚠️ Non-interactive environment detected. Switching to auto mode.")
        interactive = False

    print("🔍 Detecting environment...")
    
    changes = {}
    
    # 1. Check Ollama
    ollama_running, ollama_models, ollama_url = check_ollama()
    
    if ollama_running:
        print(f"✅ Ollama detected at {ollama_url}")
        
        # Select best model
        vision_models = [m for m in ollama_models if "vision" in m or "llava" in m or "bielik" in m]
        chat_models = [m for m in ollama_models if m not in vision_models]
        
        # Prefer vision models unless user explicitly wants chat
        best_model = None
        if vision_models:
            best_model = vision_models[0]
            print(f"   Found vision model: {best_model}")
        elif chat_models:
            best_model = chat_models[0]
            print(f"   Found chat model: {best_model}")
            
        if best_model:
            # We found a local model, this is usually preferred over cloud unless keys exist
            changes["SQ_LLM_PROVIDER"] = "ollama"
            changes["SQ_OLLAMA_URL"] = ollama_url
            changes["SQ_MODEL"] = best_model
        else:
            print("   Ollama running but no models found.")
            print("   Run `ollama pull llama3` to get started.")
    else:
        print("❌ Ollama not detected")
    
def select_provider_interactive(options: List[Dict]) -> Dict:
    """Handle interactive provider selection"""
    print("\nSelect AI Provider:")
    for idx, opt in enumerate(options):
        print(f"   {idx + 1}. {opt['name']}")
        if opt['id'] == 'ollama':
            preview = ", ".join(opt['models'][:3])
            if len(opt['models']) > 3:
                preview += "..."
            print(f"      Available models: {preview}")
    
    while True:
        try:
            choice = input(f"\nChoose provider [1-{len(options)}] (default 1): ").strip()
            if not choice:
                return options[0]
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return options[idx]
        except ValueError:
            pass
        print("Invalid selection.")

def select_model_interactive(provider_name: str, models: List[str], recommended: str = None) -> str:
    """Handle interactive model selection"""
    print(f"\nSelect model for {provider_name}:")
    
    # Sort: recommended first, then others
    sorted_models = []
    if recommended and recommended in models:
        sorted_models.append(recommended)
        
    sorted_models.extend([m for m in models if m != recommended])
    
    for idx, m in enumerate(sorted_models):
        marker = " (recommended)" if m == recommended else ""
        print(f"   {idx + 1}. {m}{marker}")
    
    choice = input(f"\nChoose model [1-{len(models)}] (default 1): ").strip()
    if choice:
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(sorted_models):
                return sorted_models[idx]
        except ValueError:
            pass
            
    return sorted_models[0]

def verify_environment() -> Dict[str, Any]:
    """
    Check environment readiness without modifying it.
    Returns status dict.
    """
    status = {
        "ollama": False,
        "ollama_url": "",
        "ollama_models": [],
        "api_keys": {}
    }
    
    # Check Ollama
    running, models, url = check_ollama()
    if running:
        status["ollama"] = True
        status["ollama_url"] = url
        status["ollama_models"] = models
        
    # Check Keys
    providers = check_providers()
    status["api_keys"] = providers
    
    return status

def run_setup(interactive: bool = True, mode: str = "balance"):
    """
    Run the setup wizard.
    
    Args:
        interactive: If True, asks for confirmation.
        mode: Configuration mode (eco, balance, performance)
    """
    # Detect non-interactive environment (CI, Docker, pipes)
    if interactive and (not sys.stdin.isatty() or os.environ.get("CI") or os.environ.get("NON_INTERACTIVE")):
        print("⚠️ Non-interactive environment detected. Switching to auto mode.")
        interactive = False

    print(f"🔍 Detecting environment (Mode: {mode})...")
    
    # Mode definitions
    mode_config = {
        "fast": {
            "whisper": "tiny",
            "ollama_vision": "moondream",      # Fastest vision model (~1.5s)
            "ollama_chat": "gemma:2b",        # Fast chat/guarder
            "desc": "Maximum speed, real-time monitoring (recommended)"
        },
        "eco": {
            "whisper": "tiny",
            "ollama_vision": "moondream",      # Fast and lightweight
            "ollama_chat": "gemma:2b",
            "desc": "Lightweight, low resource usage"
        },
        "balance": {
            "whisper": "base",
            "ollama_vision": "llava:7b",       # Good balance
            "ollama_chat": "llama3:8b",
            "desc": "Good trade-off between speed and quality"
        },
        "performance": {
            "whisper": "large",
            "ollama_vision": "llava:13b",      # Best quality
            "ollama_chat": "llama3",
            "desc": "Best quality, slower processing"
        }
    }
    
    selected_config = mode_config.get(mode, mode_config["fast"])  # Default to fast mode
    
    env_status = verify_environment()
    changes = {}
    
    # 1. Report Ollama status
    if env_status["ollama"]:
        print(f"✅ Ollama detected at {env_status['ollama_url']}")
    else:
        print("❌ Ollama not detected")
        
    # 2. Report Cloud Keys
    for provider, found in env_status["api_keys"].items():
        if found:
            print(f"✅ {provider.title()} API Key detected")
            
    # Gather all options
    options = []
    
    # Add Ollama option if running
    if env_status["ollama"] and env_status["ollama_models"]:
        options.append({
            "id": "ollama",
            "name": "Ollama (Local)",
            "models": env_status["ollama_models"],
            "url": env_status["ollama_url"]
        })
        
    # Add Cloud options if keys found
    cloud_defaults = {
        "openai": "gpt-4o",
        "anthropic": "claude-3-5-sonnet-latest",
        "groq": "llama3-70b-8192",
        "gemini": "gemini-2.0-flash",
        "deepseek": "deepseek-chat",
        "mistral": "mistral-large-latest"
    }
    
    for provider, found in env_status["api_keys"].items():
        if found and provider in cloud_defaults:
            options.append({
                "id": provider,
                "name": f"{provider.title()} (Cloud)", 
                "model": cloud_defaults[provider]
            })

    # Auto-selection logic (if non-interactive or only one option)
    selected_option = None
    
    if not options:
        print("\n⚠️ No AI providers detected.")
        print("   Please install Ollama or set OPENAI_API_KEY/ANTHROPIC_API_KEY.")
        return

    if interactive and len(options) > 1:
        selected_option = select_provider_interactive(options)
    else:
        # Default to first option (Ollama if available, or first cloud provider)
        selected_option = options[0]

    # Configure selected provider
    changes["SQ_LLM_PROVIDER"] = selected_option["id"]
    
    if selected_option["id"] == "ollama":
        changes["SQ_OLLAMA_URL"] = selected_option["url"]
        
        # Model selection for Ollama
        models = selected_option["models"]
        
        # Smart model selection based on mode
        preferred_vision = selected_config["ollama_vision"]
        preferred_chat = selected_config["ollama_chat"]
        
        # Try to find best matching vision model
        vision_models = [m for m in models if "vision" in m or "llava" in m or "bielik" in m]
        
        selected_model = None
        
        # 1. Try exact mode match (e.g. llava:13b)
        if preferred_vision in models:
            selected_model = preferred_vision
        # 2. Try any vision model
        elif vision_models:
            selected_model = vision_models[0]
        # 3. Try exact chat match
        elif preferred_chat in models:
            selected_model = preferred_chat
        # 4. Fallback
        else:
            selected_model = models[0]
        
        if interactive and len(models) > 1:
            selected_model = select_model_interactive("Ollama", models, recommended=selected_model)
        
        changes["SQ_MODEL"] = selected_model
        
        # Auto-pull recommendation if missing and mode is performance
        if mode == "performance" and selected_model != preferred_vision and preferred_vision not in models:
             print(f"\n💡 Tip: For performance mode, consider pulling: {preferred_vision}")
             print(f"   Command: ollama pull {preferred_vision}")

    else:
        # Cloud provider default model
        changes["SQ_MODEL"] = selected_option["model"]

    # 3. Voice/Audio Configuration
    if interactive:
        print("\n🔊 Voice & Audio Configuration")
        print("   Select Speech-to-Text (STT) provider:")
        
        stt_options = [
            {"id": "google", "name": "Google Web Speech (Default, requires internet)", "desc": "Free, good quality, requires internet"},
            {"id": "whisper_local", "name": f"OpenAI Whisper (Local) - {mode.title()} Mode", "desc": f"Uses '{selected_config['whisper']}' model"},
            {"id": "whisper_api", "name": "OpenAI Whisper (API)", "desc": "Highest quality, paid, requires OPENAI_API_KEY"},
        ]
        
        for idx, opt in enumerate(stt_options):
            print(f"   {idx + 1}. {opt['name']}")
            print(f"      {opt['desc']}")
            
        while True:
            try:
                choice = input(f"\nChoose STT [1-{len(stt_options)}] (default 1): ").strip()
                if not choice:
                    stt_choice = stt_options[0]
                    break
                idx = int(choice) - 1
                if 0 <= idx < len(stt_options):
                    stt_choice = stt_options[idx]
                    break
            except ValueError:
                pass
            print("Invalid selection.")
            
        changes["SQ_STT_PROVIDER"] = stt_choice["id"]
        
        if stt_choice["id"] == "whisper_local":
            # Default to mode's preference
            default_whisper = selected_config["whisper"]
            
            print("\n   Select Whisper Model Size:")
            model_sizes = ["tiny", "base", "small", "medium", "large"]
            print(f"   Available: {', '.join(model_sizes)}")
            model_choice = input(f"   Enter model size (default {default_whisper}): ").strip()
            
            if not model_choice:
                model_choice = default_whisper
            if model_choice not in model_sizes:
                model_choice = "base"
            changes["SQ_WHISPER_MODEL"] = model_choice

        # TTS configuration (engine, voice, rate)
        print("\n🔉 Text-to-Speech (TTS) Configuration")
        print("   Choose default TTS engine:")

        tts_options = [
            {"id": "pyttsx3", "name": "pyttsx3 (cross-platform, recommended)"},
            {"id": "espeak", "name": "espeak (Linux CLI, lightweight)"},
            {"id": "pico", "name": "pico (Linux, better quality) - apt install libttspico-utils"},
            {"id": "festival", "name": "festival (Linux, full-featured) - apt install festival"},
            {"id": "say", "name": "say (macOS built-in)"},
            {"id": "powershell", "name": "PowerShell (Windows built-in)"},
            {"id": "auto", "name": "auto (let Streamware choose based on OS)"},
        ]

        for idx, opt in enumerate(tts_options):
            print(f"   {idx + 1}. {opt['name']}")

        while True:
            try:
                choice = input(f"\nChoose TTS engine [1-{len(tts_options)}] (default 1): ").strip()
                if not choice:
                    tts_choice = tts_options[0]
                    break
                idx = int(choice) - 1
                if 0 <= idx < len(tts_options):
                    tts_choice = tts_options[idx]
                    break
            except ValueError:
                pass
            print("Invalid selection.")

        changes["SQ_TTS_ENGINE"] = tts_choice["id"]

        # TTS rate
        default_rate = "150"
        rate_input = input(f"   TTS speech rate (words per minute, default {default_rate}): ").strip()
        if not rate_input:
            rate_input = default_rate
        try:
            int(rate_input)
        except ValueError:
            rate_input = default_rate
        changes["SQ_TTS_RATE"] = rate_input

        # Optional voice hint
        voice_hint = input("   Preferred voice name (substring, e.g. 'polski', leave empty for default): ").strip()
        changes["SQ_TTS_VOICE"] = voice_hint

    else:
        # Auto-configure voice based on mode
        # If GPU available or high perf mode, prefer Whisper Local, otherwise Google
        # For simplicity in auto-mode, stick to Google unless configured otherwise or performance mode
        if mode in ["performance", "balance", "eco"]:
            changes["SQ_STT_PROVIDER"] = "whisper_local"
            changes["SQ_WHISPER_MODEL"] = selected_config["whisper"]
        else:
            changes["SQ_STT_PROVIDER"] = "google"

        # TTS defaults in auto mode
        changes["SQ_TTS_ENGINE"] = "pyttsx3"
        changes["SQ_TTS_RATE"] = "150"
        changes["SQ_TTS_VOICE"] = ""

    # 4. Summary and Apply

    # 4. Summary and Apply
    print("\nProposed Configuration:")
    for key, value in changes.items():
        print(f"   {key} = {value}")

    if interactive:
        response = input("\nApply these changes? [Y/n] ").strip().lower()
        if response in ("n", "no"):
            print("Setup cancelled.")
            return

    # Apply changes
    for key, value in changes.items():
        config.set(key, value)
    
    # Save only changed keys to preserve other settings
    config.save(keys_only=list(changes.keys()))
    print("\n✅ Configuration saved to .env")


def run_setup_tts(interactive: bool = True):
    """Run TTS-only setup wizard.

    This configures only SQ_TTS_ENGINE, SQ_TTS_VOICE and SQ_TTS_RATE
    without touching LLM or STT settings.
    """

    # Detect non-interactive environment
    if interactive and (not sys.stdin.isatty() or os.environ.get("CI") or os.environ.get("NON_INTERACTIVE")):
        print("⚠️ Non-interactive environment detected. Switching to auto mode.")
        interactive = False

    changes: Dict[str, Any] = {}

    print("\n🔉 Text-to-Speech (TTS) Configuration Only")

    if interactive:
        print("   Choose default TTS engine:")

        tts_options = [
            {"id": "pyttsx3", "name": "pyttsx3 (cross-platform, recommended)"},
            {"id": "espeak", "name": "espeak (Linux CLI, lightweight)"},
            {"id": "pico", "name": "pico (Linux, better quality) - apt install libttspico-utils"},
            {"id": "festival", "name": "festival (Linux, full-featured) - apt install festival"},
            {"id": "say", "name": "say (macOS built-in)"},
            {"id": "powershell", "name": "PowerShell (Windows built-in)"},
            {"id": "auto", "name": "auto (let Streamware choose based on OS)"},
        ]

        for idx, opt in enumerate(tts_options):
            print(f"   {idx + 1}. {opt['name']}")

        while True:
            try:
                choice = input(f"\nChoose TTS engine [1-{len(tts_options)}] (default 1): ").strip()
                if not choice:
                    tts_choice = tts_options[0]
                    break
                idx = int(choice) - 1
                if 0 <= idx < len(tts_options):
                    tts_choice = tts_options[idx]
                    break
            except ValueError:
                pass
            print("Invalid selection.")

        changes["SQ_TTS_ENGINE"] = tts_choice["id"]

        # TTS rate
        default_rate = "150"
        rate_input = input(f"   TTS speech rate (words per minute, default {default_rate}): ").strip()
        if not rate_input:
            rate_input = default_rate
        try:
            int(rate_input)
        except ValueError:
            rate_input = default_rate
        changes["SQ_TTS_RATE"] = rate_input

        # Optional voice hint
        voice_hint = input("   Preferred voice name (substring, e.g. 'polski', leave empty for default): ").strip()
        changes["SQ_TTS_VOICE"] = voice_hint
    else:
        # Non-interactive: keep existing values or apply sensible defaults
        current_engine = config.get("SQ_TTS_ENGINE", "pyttsx3") or "pyttsx3"
        current_rate = config.get("SQ_TTS_RATE", "150") or "150"
        current_voice = config.get("SQ_TTS_VOICE", "")

        changes["SQ_TTS_ENGINE"] = current_engine
        changes["SQ_TTS_RATE"] = current_rate
        changes["SQ_TTS_VOICE"] = current_voice

    print("\nProposed TTS Configuration:")
    for key, value in changes.items():
        print(f"   {key} = {value}")

    if interactive:
        response = input("\nApply these TTS changes? [Y/n] ").strip().lower()
        if response in ("n", "no"):
            print("TTS setup cancelled.")
            return

    for key, value in changes.items():
        config.set(key, value)

    # Save only changed keys to preserve other settings
    config.save(keys_only=list(changes.keys()))
    print("\n✅ TTS configuration saved to .env")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="balance", help="Configuration mode")
    args = parser.parse_args()
    run_setup(mode=args.mode)
