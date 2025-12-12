# Streamware Examples

This directory contains example scripts demonstrating various features and usage patterns of the Streamware framework.

## 🤖 Interactive LLM Shell (NEW!)

**Natural language commands with LLM understanding**

```bash
# Start interactive shell (terminal)
sq shell

# Start voice shell (browser)
sq voice-shell
# Open http://localhost:8766 in browser

# List available functions
sq functions
```

### Terminal Shell
```bash
sq shell
sq> detect person and email admin@company.com immediately
✅ Start person detection, send email immediately
   Command: sq watch --detect person --email admin@company.com --notify-mode instant
   Execute? [Y/n]: y
```

### Browser Voice Shell
```bash
sq voice-shell
# Open http://localhost:8766
# Click 🎤 and say: "detect person and email me"
# Say "yes" to confirm
```

See: [LLM Shell Guide](../docs/LLM_SHELL.md) | [Voice Shell Guide](../docs/VOICE_SHELL.md)

---

## 🎥 Real-time Visualizer

**Motion detection with SVG overlays and DSL metadata streaming**

```bash
# Basic usage - open http://localhost:8080
sq visualize --url "rtsp://camera/stream" --port 8080

# Lowest latency configuration
sq visualize --url "rtsp://camera/stream" --port 8080 \
  --video-mode meta --fps 10 --transport udp --backend pyav

# MQTT integration - publish to broker
sq mqtt --url "rtsp://camera/stream" --broker localhost
```

| Mode | Latency | Use Case |
|------|---------|----------|
| `--video-mode ws` | ~100ms | Full video (default) |
| `--video-mode meta` | ~50ms | Metadata + 1 FPS preview |
| `--backend pyav` | ~50ms | Direct API, no subprocess |
| `--transport udp` | ~50ms | Lower latency |

See: [media-processing/realtime_visualizer_examples.sh](media-processing/realtime_visualizer_examples.sh)

---

## 🎯 Live Narrator (Recommended!)

**Real-time video analysis with YOLO + Vision LLM + TTS**

```bash
# Person tracking with voice narration
sq live narrator --url "rtsp://camera/stream" --mode track --focus person --tts

# Bird feeder monitoring
sq live narrator --url "rtsp://birdcam/stream" --mode track --focus bird --tts

# Pet camera (cats & dogs)
sq live narrator --url "rtsp://petcam/stream" --mode track --focus pet --tts

# Verbose mode (see timing)
sq live narrator --url "rtsp://camera/stream" --mode track --focus person --tts --verbose
```

See: [media-processing/live_narrator_examples.sh](media-processing/live_narrator_examples.sh)

---

## 🗣️ Natural Language Configuration (NEW!)

**Configure using natural language - Polish or English**

```bash
# Track person
sq watch "track person"
sq watch "śledź osoby"

# Count objects
sq watch "count people"
sq watch "ile samochodów"

# Describe scene
sq watch "describe what's happening"
sq watch "opisz co się dzieje"

# Security alerts
sq watch "alert when someone enters"
sq watch "powiadom gdy ktoś wchodzi"
```

See: [natural_language/](natural_language/) | [docs/NATURAL_LANGUAGE_CONFIG.md](../docs/NATURAL_LANGUAGE_CONFIG.md)

---

## 📁 New Examples

| Example | Description | Quick Start |
|---------|-------------|-------------|
| [track_person/](track_person/) | Fast person tracking with YOLO | `sq watch "track person"` |
| [security/](security/) | Intrusion detection with LLM | `sq watch "alert when someone enters"` |
| [count_objects/](count_objects/) | Count people, cars, animals | `sq watch "count people"` |
| [describe_scene/](describe_scene/) | LLM scene descriptions | `sq watch "describe scene"` |
| [natural_language/](natural_language/) | Natural language config | `sq watch "śledź osoby"` |

## 📁 Project Examples

| Project | Description | Examples |
|---------|-------------|----------|
| [media-processing/](media-processing/) | **Visualizer, MQTT, Live Narrator** | `realtime_visualizer_examples.sh`, `mqtt_integration.py` |
| [llm-ai/](llm-ai/) | AI text processing, code generation | `text_to_sql.py`, `chat_assistant.py` |
| [voice-control/](voice-control/) | Voice commands, STT/TTS | `voice_keyboard.py`, `voice_mouse.py` |
| [automation/](automation/) | Desktop automation | `mouse_control.py`, `keyboard_control.py` |
| [communication/](communication/) | Email, Slack, Telegram | `slack_bot.py`, `telegram_bot.py` |
| [data-pipelines/](data-pipelines/) | ETL, data transformation | `api_to_database.py`, `csv_processor.py` |
| [deployment/](deployment/) | Docker, K8s, SSH deploy | `docker_deploy.py`, `ssh_deploy.sh` |

## 🚀 Quick Start

```bash
# Real-time Visualizer (NEW - motion detection with SVG overlay)
sq visualize --url "rtsp://camera/stream" --port 8080
sq visualize --url "rtsp://camera/stream" --port 8080 --video-mode meta --backend pyav

# MQTT Publisher (NEW - publish DSL to broker)
sq mqtt --url "rtsp://camera/stream" --broker localhost

# Live Narrator (real-time video with TTS)
sq live narrator --url "rtsp://camera/stream" --mode track --focus person --tts

# LLM/AI
python examples/llm-ai/text_to_sql.py "Get all users"
python examples/llm-ai/chat_assistant.py --provider ollama/qwen2.5:14b

# Voice Control
python examples/voice-control/voice_keyboard.py --interactive

# Automation
python examples/automation/mouse_control.py 100 200

# Communication
python examples/communication/slack_bot.py general "Hello!"

# Data Pipelines
python examples/data-pipelines/api_to_database.py
```

## 🎬 Video Analysis Modes

| Mode | Description | CLI Command |
|------|-------------|-------------|
| `full` | Coherent narrative | `sq media describe_video --file v.mp4 --mode full` |
| `stream` | Frame-by-frame details | `sq media describe_video --file v.mp4 --mode stream` |
| `diff` | Track changes | `sq media describe_video --file v.mp4 --mode diff` |

> 📚 Full documentation: [media-processing/README.md](media-processing/README.md)

## 📚 Related Documentation

| Document | Description |
|----------|-------------|
| [Quick Start](../docs/v2/guides/QUICK_START.md) | Get started in 5 minutes |
| [Quick CLI](../docs/v2/components/QUICK_CLI.md) | `sq` command reference |
| [LLM Component](../docs/v2/components/LLM_COMPONENT.md) | AI providers configuration |
| [Voice Guide](../docs/v2/guides/VOICE_AUTOMATION_GUIDE.md) | Voice control setup |
| [DSL Examples](../docs/v2/components/DSL_EXAMPLES.md) | Pipeline syntax |

## 📦 Legacy Examples

| File | Description |
|------|-------------|
| [basic_usage.py](basic_usage.py) | Fundamental concepts |
| [advanced_patterns.py](advanced_patterns.py) | Workflow patterns |
| [llm_examples.py](llm_examples.py) | LLM demonstrations |
| [ssh_examples.py](ssh_examples.py) | SSH operations |
| [deploy_examples.py](deploy_examples.py) | Deployment patterns |
| [dsl_examples.py](dsl_examples.py) | DSL syntax |
| [text2streamware_examples.py](text2streamware_examples.py) | Natural language to commands |

## 🔗 Source Code References

| Component | Path |
|-----------|------|
| LLM | [streamware/components/llm.py](../streamware/components/llm.py) |
| Voice | [streamware/components/voice.py](../streamware/components/voice.py) |
| Voice Keyboard | [streamware/components/voice_keyboard.py](../streamware/components/voice_keyboard.py) |
| Voice Mouse | [streamware/components/voice_mouse.py](../streamware/components/voice_mouse.py) |
| Automation | [streamware/components/automation.py](../streamware/components/automation.py) |
| Media | [streamware/components/media.py](../streamware/components/media.py) |
| Email | [streamware/components/email.py](../streamware/components/email.py) |
| Slack | [streamware/components/slack.py](../streamware/components/slack.py) |
| Telegram | [streamware/components/telegram.py](../streamware/components/telegram.py)

## Quick Start

### Run All Basic Examples

```bash
cd /path/to/streamware
python examples/basic_usage.py
```

### Run Specific Examples

You can modify the example files to run specific examples:

```python
# In basic_usage.py, modify main() to run specific examples
if __name__ == "__main__":
    example_1_simple_data_flow()
    example_2_file_operations()
    # ... run only what you need
```

## Example Output

When you run the examples, you'll see output like:

```
============================================================
STREAMWARE BASIC USAGE EXAMPLES
============================================================

=== Example 1: Simple Data Flow ===
Input: {'name': 'Alice', 'age': 30, 'city': 'New York'}
Output: {"name": "Alice", "age": 30, "city": "New York"}

=== Example 2: File Operations ===
Write result: {'success': True, 'path': '/tmp/streamware_example.txt'}
Read result: Hello from Streamware!
Cleaned up: /tmp/streamware_example.txt

...
```

## Creating Your Own Examples

You can create custom examples by following these patterns:

```python
#!/usr/bin/env python3
"""
My Custom Streamware Example
"""

from streamware import flow, Component, register

def my_example():
    """
    Description of what this example demonstrates
    """
    print("\n=== My Example ===")
    
    # Your code here
    result = flow("component://operation").run(data)
    print(f"Result: {result}")

if __name__ == "__main__":
    my_example()
```

## Testing Examples

All examples are designed to be runnable without external dependencies (where possible). Some examples that require external services will skip or simulate operations.

To test examples:

```bash
# Run basic examples
python examples/basic_usage.py

# Run advanced examples
python examples/advanced_patterns.py

# Run with pytest (if you have tests for examples)
pytest examples/test_examples.py -v
```

## Common Patterns

### Pattern 1: Simple Pipeline

```python
result = (
    flow("source://data")
    | "transform://process"
    | "sink://destination"
).run()
```

### Pattern 2: With Error Handling

```python
try:
    result = flow("risky://operation").run(data)
except ComponentError as e:
    print(f"Error: {e}")
    result = None
```

### Pattern 3: Custom Component

```python
@register("mycomp")
class MyComponent(Component):
    def process(self, data):
        return transform(data)

result = flow("mycomp://operation").run(data)
```

### Pattern 4: Streaming

```python
for item in flow("source://stream").stream():
    processed = process(item)
    save(processed)
```

## Best Practices

1. **Start Simple**: Begin with basic examples before moving to advanced patterns
2. **Experiment**: Modify examples to understand how components work
3. **Error Handling**: Always include error handling in production code
4. **Testing**: Test your pipelines thoroughly
5. **Documentation**: Document your custom components and pipelines

## Troubleshooting

### Import Errors

If you get import errors, make sure streamware is installed:

```bash
pip install -e .
```

### Missing Dependencies

Some examples require optional dependencies:

```bash
# For communication examples
pip install streamware[communication]

# For all features
pip install streamware[all]
```

### File Permissions

Some examples write to `/tmp/`. If you encounter permission issues, modify the examples to use a different directory:

```python
import tempfile
temp_dir = tempfile.gettempdir()
temp_file = os.path.join(temp_dir, "output.txt")
```

## Contributing Examples

We welcome contributions of new examples! Please:

1. Follow the existing example structure
2. Include clear documentation
3. Test your examples
4. Submit a pull request

## Support

- 📚 Full Documentation: [docs/USAGE_GUIDE.md](../docs/USAGE_GUIDE.md)
- 🐛 Report Issues: [GitHub Issues](https://github.com/softreck/streamware/issues)
- 💬 Ask Questions: [GitHub Discussions](https://github.com/softreck/streamware/discussions)

---

Happy streaming with Streamware! 🚀
