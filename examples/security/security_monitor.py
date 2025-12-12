#!/usr/bin/env python3
"""
Security Monitoring Example
Intrusion detection with LLM verification.
"""

from streamware.intent import parse_intent, apply_intent
from streamware.workflow import load_workflow
from streamware.config import config
from streamware.core import flow

URL = config.get("SQ_DEFAULT_URL") or "rtsp://admin:admin@192.168.1.100:554/stream"

def main():
    # Method 1: Natural language
    intent = parse_intent("alert when someone enters")
    apply_intent(intent)
    print(f"Intent: {intent.describe()}")
    
    # Method 2: Workflow preset
    workflow = load_workflow(preset="security")
    print(f"\nSecurity preset:")
    print(f"  LLM: {workflow.llm}")
    print(f"  Guarder: {workflow.guarder}")
    print(f"  FPS: {workflow.fps}")
    
    # Build security URI
    uri = f"live://narrator?source={URL}"
    uri += "&mode=track"
    uri += "&focus=person"
    uri += "&tts=true"
    uri += "&tts_mode=diff"
    uri += "&duration=300"  # 5 minutes
    
    print(f"\nStarting security monitor...")
    result = flow(uri).run()
    return result

if __name__ == "__main__":
    main()
