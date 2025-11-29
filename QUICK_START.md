# 🚀 Streamware Quick Start

## 1-Minute Setup

```bash
# Clone
git clone https://github.com/stream-ware/streamware
cd streamware

# Install dependencies
bash install_bot_deps.sh

# Install Streamware
pip install -e .

# Deploy bot
bash deploy_vscode_bot.sh

# Use it!
sq bot continue_work --iterations 5
```

## What Just Happened?

### `install_bot_deps.sh` installed:
- ✅ gnome-screenshot / scrot (for screenshots)
- ✅ Pillow >= 9.2.0 (for image handling)
- ✅ PyAutoGUI (for mouse/keyboard)
- ✅ pyscreeze (for screenshot support)
- ✅ X11 permissions (for display access)

### `deploy_vscode_bot.sh` configured:
- ✅ Ollama + AI models (LLaVA, Qwen2.5)
- ✅ Bot service
- ✅ Control scripts

### Now you can:
```bash
# Click buttons
sq bot click_button --button accept_all

# Work autonomously
sq bot continue_work --iterations 10

# Take screenshots
sq auto screenshot --text screen.png

# Automate desktop
sq auto click --x 100 --y 200
```

## Troubleshooting

### Error: "gnome-screenshot not found"
```bash
sudo apt-get install gnome-screenshot scrot
```

### Error: "Can't connect to display"
```bash
xhost +local:
export DISPLAY=:0
```

### Error: "Pillow version too old"
```bash
pip install --upgrade "Pillow>=9.2.0"
```

### Run full dependency installer:
```bash
bash install_bot_deps.sh
```

## Manual Installation

If automated scripts don't work:

```bash
# 1. System packages
sudo apt-get update
sudo apt-get install -y gnome-screenshot scrot imagemagick xclip xdotool

# 2. Python packages  
pip install --upgrade pip
pip install "Pillow>=9.2.0" pyscreeze pyautogui
pip install SpeechRecognition pyttsx3  # optional: voice
pip install opencv-python              # optional: media

# 3. X11
xhost +local:

# 4. Ollama
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llava
ollama pull qwen2.5:14b

# 5. Streamware
pip install -e .
```

## Verify Installation

```bash
# Test imports
python3 -c "from streamware.components import VSCodeBotComponent; print('✓')"

# Test screenshot
sq auto screenshot --text test.png

# Test bot
sq bot click_button --button accept_all
```

## Next Steps

1. **Read the guide:** `VSCODE_BOT_GUIDE.md`
2. **Try examples:** `examples/voice_automation_examples.sh`
3. **Deploy for real:** `sq bot continue_work --iterations 100`

## Support

- 📖 Documentation: `docs/`
- 🐛 Issues: GitHub Issues
- 💬 Discussions: GitHub Discussions

**Your AI pair programmer is ready! 🤖✨**
