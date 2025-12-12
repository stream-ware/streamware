#!/usr/bin/env python3
"""
Track Person Example
Fast person tracking using YOLO without LLM.

NEW: For LLM-based parsing, use:
    from streamware.llm_intent import parse_command
    intent = parse_command("track person for 5 minutes")
    
Or interactive shell:
    sq shell
    sq> track person for 5 minutes
    sq> track cars and email alerts@x.com
"""

from streamware.intent import parse_intent, apply_intent
from streamware.config import config
from streamware.core import flow

# Get URL from config or use default
URL = config.get("SQ_DEFAULT_URL") or "rtsp://admin:admin@192.168.1.100:554/stream"

def main():
    # Method 1: Natural language
    intent = parse_intent("track person")
    apply_intent(intent)
    
    print(f"Intent: {intent.describe()}")
    print(f"URL: {URL}")
    print()
    
    # Method 2: Direct flow
    uri = f"live://narrator?source={URL}"
    uri += "&mode=track"
    uri += "&focus=person"
    uri += "&tts=true"
    uri += "&tts_mode=diff"
    uri += "&duration=60"
    
    result = flow(uri).run()
    return result

if __name__ == "__main__":
    main()
