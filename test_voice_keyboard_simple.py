#!/usr/bin/env python3
"""Simple test of voice keyboard component"""

print("Testing Voice Keyboard Component\n")

# Test 1: Direct import and use
print("1. Testing direct component usage...")
from streamware.components.voice_keyboard import VoiceKeyboardComponent
from streamware.uri import StreamwareURI

uri = StreamwareURI("voice_keyboard://type?command=wpisz hello world")
component = VoiceKeyboardComponent(uri)
result = component.process(None)
print(f"   Result: {result}\n")

# Test 2: Through flow
print("2. Testing through flow...")
try:
    from streamware import flow
    result = flow("voice_keyboard://type?command=wpisz test 123").run()
    print(f"   Result: {result}\n")
except Exception as e:
    print(f"   Error: {e}\n")

# Test 3: Check registration
print("3. Checking component registration...")
from streamware.core import registry
schemes = list(registry._components.keys())
print(f"   Registered schemes: {[s for s in schemes if 'voice' in s]}\n")

print("✓ Tests complete!")
