"""
Streamware Setup Wizard

Detects environment and configures Streamware automatically.
"""

import os
import sys
import requests
import asyncio
from typing import Dict, List, Optional, Tuple
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
    
    # 2. Check Cloud Providers
    providers = check_providers()
    
    # If no local Ollama model, try to pick a cloud provider
    if "SQ_LLM_PROVIDER" not in changes:
        if providers["openai"]:
            print("✅ OpenAI API Key detected")
            changes["SQ_LLM_PROVIDER"] = "openai"
            changes["SQ_MODEL"] = "gpt-4o"
        elif providers["anthropic"]:
            print("✅ Anthropic API Key detected")
            changes["SQ_LLM_PROVIDER"] = "anthropic"
            changes["SQ_MODEL"] = "claude-3-5-sonnet-latest"
        elif providers["groq"]:
            print("✅ Groq API Key detected")
            changes["SQ_LLM_PROVIDER"] = "groq"
            changes["SQ_MODEL"] = "llama3-70b-8192"
        elif providers["gemini"]:
            print("✅ Gemini API Key detected")
            changes["SQ_LLM_PROVIDER"] = "gemini"
            changes["SQ_MODEL"] = "gemini-2.0-flash"
    
    # Report other found keys
    for provider, found in providers.items():
        if found:
            print(f"✅ {provider.title()} API Key detected")

    # 4. Summary and Apply
    if not changes:
        print("\n⚠️ No AI providers detected.")
        print("   Please install Ollama or set OPENAI_API_KEY/ANTHROPIC_API_KEY.")
        return

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
    
    config.save()
    print("\n✅ Configuration saved to .env")

if __name__ == "__main__":
    run_setup()
