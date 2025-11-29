#!/usr/bin/env python3
"""
Multi-Provider LLM - Compare responses from different providers

Demonstrates LiteLLM-compatible provider format:
    openai/gpt-4o, ollama/qwen2.5:14b, groq/llama3-70b-8192, etc.

Related:
    - docs/v2/components/LLM_COMPONENT.md
    - streamware/components/llm.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from streamware import flow


# Available providers (LiteLLM format)
PROVIDERS = {
    "ollama": "ollama/qwen2.5:14b",      # Local, free
    "openai": "openai/gpt-4o-mini",       # Requires OPENAI_API_KEY
    "groq": "groq/llama3-70b-8192",       # Requires GROQ_API_KEY (fast!)
    "gemini": "gemini/gemini-2.0-flash",  # Requires GEMINI_API_KEY
    "anthropic": "anthropic/claude-3-haiku-20240307",  # Requires ANTHROPIC_API_KEY
    "deepseek": "deepseek/deepseek-chat", # Requires DEEPSEEK_API_KEY
}


def test_provider(provider: str, prompt: str) -> str:
    """Test a single provider"""
    try:
        result = flow(f"llm://generate?prompt={prompt}&provider={provider}").run()
        return result[:200] + "..." if len(result) > 200 else result
    except Exception as e:
        return f"Error: {e}"


def main():
    prompt = sys.argv[1] if len(sys.argv) > 1 else "Say hello in 3 different languages"
    
    print("=" * 70)
    print("MULTI-PROVIDER LLM COMPARISON")
    print("=" * 70)
    print(f"Prompt: {prompt}\n")
    
    for name, provider in PROVIDERS.items():
        print(f"\n{'─' * 70}")
        print(f"🤖 {name.upper()} ({provider})")
        print("─" * 70)
        
        result = test_provider(provider, prompt)
        print(result)
    
    print("\n" + "=" * 70)
    print("Provider Format: provider/model")
    print("API Keys: OPENAI_API_KEY, GROQ_API_KEY, GEMINI_API_KEY, etc.")
    print("=" * 70)


if __name__ == "__main__":
    main()
