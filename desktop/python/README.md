# Streamware Voice Shell - Python Desktop App

Desktop application wrapper for Streamware Voice Shell using PyWebView.

## Features
- Native desktop window with embedded web UI
- System tray integration
- Cross-platform (Windows, macOS, Linux)
- Automatic backend server management

## Installation

```bash
cd desktop/python
pip install -r requirements.txt
```

## Usage

```bash
# Run the desktop app
python app.py

# With custom port
python app.py --port 9000

# With language
python app.py --lang pl
```

## Architecture

```
┌────────────────────────────────────────┐
│           PyWebView Window             │
│  ┌──────────────────────────────────┐  │
│  │       Voice Shell Web UI         │  │
│  │    (HTML/CSS/JS rendered)        │  │
│  └──────────────────────────────────┘  │
└────────────────────────────────────────┘
              │ HTTP/WS
              ▼
┌────────────────────────────────────────┐
│      VoiceShellServer (Python)         │
│  - WebSocket for real-time comm        │
│  - HTTP for static files & auth        │
│  - SQLite for persistence              │
└────────────────────────────────────────┘
              │
              ▼
┌────────────────────────────────────────┐
│      System Services                   │
│  - Ollama LLM                          │
│  - TTS (espeak/pico)                   │
│  - Audio capture                       │
└────────────────────────────────────────┘
```

## Building Executable

```bash
# Install PyInstaller
pip install pyinstaller

# Build single executable
pyinstaller --onefile --windowed --name "StreamwareVoiceShell" app.py
```
