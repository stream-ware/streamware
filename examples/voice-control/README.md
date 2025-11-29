# Voice Control Examples

Voice-controlled automation with STT/TTS and AI vision.

## 📁 Examples

| File | Description |
|------|-------------|
| [voice_keyboard.py](voice_keyboard.py) | Type with voice commands |
| [voice_mouse.py](voice_mouse.py) | Control mouse with voice + AI |
| [voice_assistant.sh](voice_assistant.sh) | Interactive voice assistant |
| [dictation_mode.py](dictation_mode.py) | Continuous voice dictation |

## 🚀 Quick Start

```bash
# Voice keyboard
sq voice-keyboard type "wpisz hello world"

# Voice mouse (AI finds buttons!)
sq voice-click "kliknij w button OK"

# Text to speech
sq voice speak "Hello, I am Streamware"

# Listen for voice
sq voice listen
```

## 🔧 Requirements

```bash
# System tools
sudo apt-get install xdotool espeak scrot

# Python packages (auto-installed)
pip install SpeechRecognition PyAudio pyttsx3
```

## 📚 Related Documentation

- [Voice Automation Guide](../../docs/v2/guides/VOICE_AUTOMATION_GUIDE.md)
- [Voice Mouse Guide](../../docs/v2/guides/VOICE_MOUSE_GUIDE.md)
- [Quick CLI](../../docs/v2/components/QUICK_CLI.md)

## 🔗 Related Examples

- [Automation](../automation/) - Desktop automation
- [LLM AI](../llm-ai/) - AI text processing

## 🎤 Voice Commands (Polish/English)

| Command | Action |
|---------|--------|
| "wpisz hello" / "type hello" | Types "hello" |
| "naciśnij enter" / "press enter" | Presses Enter |
| "kliknij w button" / "click button" | AI finds and clicks |
