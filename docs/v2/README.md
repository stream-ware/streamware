# Streamware v2 Documentation

## Quick Navigation

### 📚 Guides
- [Quick Start](guides/QUICK_START.md) - Get started in 5 minutes
- [Quick Reference](guides/QUICK_REFERENCE.md) - Command cheatsheet
- [Docker Quickstart](guides/DOCKER_QUICKSTART.md) - Container deployment
- [App Creation Guide](guides/APP_CREATION_GUIDE.md) - Build apps with sq
- [Voice Mouse Guide](guides/VOICE_MOUSE_GUIDE.md) - Voice-controlled mouse
- [Voice Automation Guide](guides/VOICE_AUTOMATION_GUIDE.md) - Voice commands
- [VSCode Bot Guide](guides/VSCODE_BOT_GUIDE.md) - AI pair programmer
- [Media Guide](guides/MEDIA_GUIDE.md) - Image/video processing
- [Test Guide](guides/TEST_GUIDE.md) - Testing workflows

### 🔧 Components
- [CLI Usage](components/CLI_USAGE.md) - Full CLI reference
- [Quick CLI](components/QUICK_CLI.md) - `sq` command reference
- [LLM Component](components/LLM_COMPONENT.md) - AI text generation
- [SSH Component](components/SSH_COMPONENT.md) - Remote operations
- [Deploy Component](components/DEPLOY_COMPONENT.md) - Deployments
- [Communication](components/COMMUNICATION.md) - Email, Slack, Telegram
- [DSL Examples](components/DSL_EXAMPLES.md) - Pipeline examples
- [Usage Guide](components/USAGE_GUIDE.md) - Complete usage
- [Testing](components/TESTING.md) - Test framework

## LLM Provider Configuration

Streamware uses LiteLLM-compatible provider format:

```python
# Format: provider/model
provider="openai/gpt-4o"
provider="ollama/qwen2.5:14b"
provider="anthropic/claude-3-5-sonnet-20240620"
provider="gemini/gemini-2.0-flash"
provider="groq/llama3-70b-8192"
provider="deepseek/deepseek-chat"
```

### Supported Providers
| Provider | Models | API Key Env |
|----------|--------|-------------|
| openai | gpt-4o, gpt-4o-mini, o1-mini | OPENAI_API_KEY |
| anthropic | claude-3-5-sonnet, claude-3-haiku | ANTHROPIC_API_KEY |
| ollama | llama3.2, qwen2.5, llava (local) | - |
| gemini | gemini-2.0-flash, gemini-1.5-pro | GEMINI_API_KEY |
| groq | llama3-70b-8192, llama3-8b-8192 | GROQ_API_KEY |
| deepseek | deepseek-chat | DEEPSEEK_API_KEY |
| mistral | mistral-large-latest | MISTRAL_API_KEY |

### Examples

```bash
# OpenAI
sq llm "Write a poem" --provider openai/gpt-4o

# Local Ollama
sq llm "Explain Python" --provider ollama/qwen2.5:14b

# Groq (fast)
sq llm "Summarize this" --provider groq/llama3-70b-8192

# Auto-detect from environment
export LLM_PROVIDER="gemini/gemini-2.0-flash"
sq llm "Generate SQL for users table"
```

## Quick Start Commands

```bash
# Install
pip install streamware

# Basic usage
sq llm "Hello world" --provider ollama/llama3.2
sq file . --list
sq get https://api.example.com/users --json

# Voice control
sq voice-click listen_and_click
sq voice speak "Hello!"

# Automation
sq auto screenshot --text /tmp/screen.png
sq auto click --x 100 --y 200
```

## Version

Current: **Streamware 0.2.1**

See [../v1/](../v1/) for deprecated documentation.
