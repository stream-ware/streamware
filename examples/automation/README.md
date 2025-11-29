# Desktop Automation Examples

Control mouse, keyboard, and automate desktop tasks.

## 📁 Examples

| File | Description |
|------|-------------|
| [mouse_control.py](mouse_control.py) | Mouse clicks and movement |
| [keyboard_control.py](keyboard_control.py) | Typing and hotkeys |
| [screenshot_ocr.py](screenshot_ocr.py) | Screenshot and text extraction |
| [ai_automation.py](ai_automation.py) | AI-powered task automation |
| [form_filler.sh](form_filler.sh) | Automate form filling |

## 🚀 Quick Start

```bash
# Take screenshot
sq auto screenshot --text /tmp/screen.png

# Click at position
sq auto click --x 100 --y 200

# Type text
sq auto type --text "Hello World"

# Press hotkey
sq auto hotkey --keys ctrl+s

# AI automation (natural language)
sq auto automate --task "click the submit button"
```

## 🔧 Requirements

```bash
# System tools (recommended)
sudo apt-get install xdotool scrot

# Or Python packages
pip install pyautogui Pillow
```

## 📚 Related Documentation

- [Quick CLI](../../docs/v2/components/QUICK_CLI.md)
- [Voice Automation Guide](../../docs/v2/guides/VOICE_AUTOMATION_GUIDE.md)

## 🔗 Related Examples

- [Voice Control](../voice-control/) - Voice-driven automation
- [LLM AI](../llm-ai/) - AI task generation

## 🔗 Source Code

- [streamware/components/automation.py](../../streamware/components/automation.py)
- [streamware/components/voice_keyboard.py](../../streamware/components/voice_keyboard.py)
