#!/usr/bin/env python3
"""
Interactive Chat Assistant

Usage:
    python chat_assistant.py
    python chat_assistant.py --provider openai/gpt-4o

Related:
    - docs/v2/components/LLM_COMPONENT.md
    - examples/voice-control/voice_chat.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from streamware import flow


def chat(provider: str = "ollama/qwen2.5:14b"):
    """Interactive chat session"""
    print("=" * 60)
    print("STREAMWARE CHAT ASSISTANT")
    print(f"Provider: {provider}")
    print("Type 'exit' or 'quit' to end")
    print("=" * 60)
    
    history = []
    
    while True:
        try:
            user_input = input("\n👤 You: ").strip()
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("👋 Goodbye!")
                break
            
            if not user_input:
                continue
            
            # Add context from history
            context = "\n".join([f"User: {h['user']}\nAssistant: {h['assistant']}" 
                                for h in history[-3:]])  # Last 3 exchanges
            
            prompt = f"{context}\n\nUser: {user_input}\nAssistant:" if context else user_input
            
            # Get response
            result = flow(f"llm://chat?prompt={prompt}&provider={provider}").run()
            
            print(f"\n🤖 Assistant: {result}")
            
            # Save to history
            history.append({"user": user_input, "assistant": result})
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


def main():
    provider = "ollama/qwen2.5:14b"
    
    for i, arg in enumerate(sys.argv):
        if arg == "--provider" and i + 1 < len(sys.argv):
            provider = sys.argv[i + 1]
    
    chat(provider)


if __name__ == "__main__":
    main()
