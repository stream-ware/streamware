# Streamware LLM Shell

## Overview

Streamware provides an interactive LLM-powered shell that understands natural language commands and converts them into executable shell commands.

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                     User Input                              │
│         "detect person and email me when found"             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────────────────────┐
│                  Function Registry                        │
│   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐         │
│   │ detect  │ │  track  │ │ notify  │ │ config  │ ...     │
│   │params   │ │params   │ │params   │ │params   │         │
│   │examples │ │examples │ │examples │ │examples │         │
│   │shell_cmd│ │shell_cmd│ │shell_cmd│ │shell_cmd│         │
│   └─────────┘ └─────────┘ └─────────┘ └─────────┘         │
└─────────────────────┬─────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    LLM (Ollama/OpenAI)                      │
│   - Receives function definitions as context                │
│   - Parses natural language                                 │
│   - Maps to functions + extracts parameters                 │
│   - Generates shell command                                 │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   Shell Execution                           │
│   $ sq watch --detect person --email me@x.com               │
│     --notify-mode instant --duration 60                     │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Start Interactive Shell

```bash
# Basic usage
sq shell

# With auto-execute (no confirmation)
sq shell --auto

# With specific model
sq shell --model llama3.2

# Using OpenAI
sq shell --provider openai --model gpt-4o

# Verbose mode (show LLM responses)
sq shell -v
```

### Example Session

```
$ sq shell

============================================================
Streamware Interactive Shell
============================================================
Type natural language commands or 'help' for assistance
Type 'exit' to quit

sq> detect person and email admin@company.com when found
✅ Detect person, send email to admin@company.com immediately
   Command: sq watch --detect person --email admin@company.com --notify-mode instant --duration 60
   Execute? [Y/n]: y
$ sq watch --detect person --email admin@company.com --notify-mode instant --duration 60
[Started in background, PID: 12345]
[Use 'stop' to terminate]

sq> track cars for 10 minutes
✅ Track car objects for 600 seconds
   Command: sq watch --track car --fps 2 --duration 600
   Execute? [Y/n]: y

sq> stop
✅ Stop all detection processes
   Command: pkill -f 'sq watch' || echo 'Nothing running'
   Execute? [Y/n]: y
Nothing running

sq> exit
Goodbye!
```

## Available Functions

### List Functions

```bash
# Human-readable list
sq functions

# JSON format
sq functions --json

# LLM context format
sq functions --llm

# Filter by category
sq functions --category detection
```

### Function Categories

| Category | Functions |
|----------|-----------|
| **detection** | detect, track, count |
| **notification** | notify_email, notify_slack, notify_telegram |
| **output** | screenshot, record, speak |
| **config** | set_source, set_model, show_config |
| **system** | status, stop, help |

## Function Registry

All functions are defined in `function_registry.py` with:

```python
@dataclass  
class RegisteredFunction:
    name: str                    # Function name
    description: str             # Human description
    category: str                # Category for grouping
    params: List[FunctionParam]  # Parameters with types/defaults
    returns: str                 # Return type
    examples: List[str]          # Natural language examples
    shell_template: str          # Shell command template
    callable: Callable           # Optional Python callable
```

### Example Function Definition

```python
registry.add(RegisteredFunction(
    name="detect",
    description="Detect objects in video stream using YOLO or LLM",
    category="detection",
    params=[
        FunctionParam("target", "string", "Object to detect", True, "person",
                     choices=["person", "car", "animal", "motion"]),
        FunctionParam("duration", "integer", "Duration in seconds", False, 60),
        FunctionParam("confidence", "number", "Detection threshold 0-1", False, 0.5),
    ],
    examples=[
        "detect person",
        "detect car with high confidence",
        "detect motion for 5 minutes",
    ],
    shell_template="sq watch --detect {target} --confidence {confidence} --duration {duration}",
))
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SQ_OLLAMA_URL` | Ollama API URL | `http://localhost:11434` |
| `SQ_LLM_MODEL` | Default LLM model | `llama3.2` |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `SQ_DEFAULT_URL` | Default video source | - |
| `SQ_NOTIFY_EMAIL` | Default email for notifications | - |

### LLM Models

Tested models:
- **Ollama**: `llama3.2`, `llama3.1`, `mistral`, `gemma2`
- **OpenAI**: `gpt-4o`, `gpt-4o-mini`, `gpt-3.5-turbo`

## Adding Custom Functions

```python
from streamware.function_registry import registry, RegisteredFunction, FunctionParam

# Add custom function
registry.add(RegisteredFunction(
    name="my_custom_action",
    description="Do something custom",
    category="custom",
    params=[
        FunctionParam("input", "string", "Input value", True),
    ],
    examples=["do my custom thing with X"],
    shell_template="my-tool --input {input}",
))

# Or use decorator
@registry.register(
    name="another_action",
    description="Another custom action",
    category="custom",
    params=[FunctionParam("x", "integer", "Value", True)],
)
def another_action(x: int):
    return x * 2
```

## Programmatic Usage

```python
from streamware.function_registry import registry, invoke, generate_shell
from streamware.llm_shell import LLMShell

# List functions
for fn in registry.functions:
    print(f"{fn.name}: {fn.description}")

# Generate shell command
cmd = generate_shell("detect", target="person", duration=300)
print(cmd)  # sq watch --detect person --duration 300

# Get LLM context
context = registry.get_llm_context()

# Programmatic shell
shell = LLMShell(model="llama3.2")
result = shell.parse("detect person and email me")
print(result.shell_command)
```

## Troubleshooting

### LLM Not Responding

1. Check Ollama is running: `curl http://localhost:11434/api/tags`
2. Check model is installed: `ollama list`
3. Install model: `ollama pull llama3.2`

### Commands Not Executing

1. Check verbose mode: `sq shell -v`
2. Verify generated command manually
3. Check environment variables: `sq config --show`

### Custom Functions Not Working

1. Ensure function is registered before shell starts
2. Check shell_template has correct placeholders
3. Verify parameter types match
