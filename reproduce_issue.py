
import os
import logging
from streamware.core import flow
from streamware.components.llm import LLMComponent
from streamware.uri import StreamwareURI
from streamware.diagnostics import enable_diagnostics

# Enable logging
logging.basicConfig(level=logging.INFO)

# Unset keys
if "OPENAI_API_KEY" in os.environ:
    del os.environ["OPENAI_API_KEY"]
if "SQ_OPENAI_API_KEY" in os.environ:
    del os.environ["SQ_OPENAI_API_KEY"]

print("Testing with default provider (openai) and no key...")
try:
    # This should trigger the warning
    c = LLMComponent(StreamwareURI("llm://generate?provider=openai"))
    print(f"Provider fell back to: {c.provider}")
except Exception as e:
    print(f"Error: {e}")

print("\nTesting with 'openapi' provider...")
try:
    c = LLMComponent(StreamwareURI("llm://generate?provider=openapi"))
except Exception as e:
    print(f"Error: {e}")
