# Streamware Voice Shell - Desktop Applications

Native desktop applications for Streamware Voice Shell.
Two implementations are provided: Python (PyWebView) and Rust (Tauri).

## Quick Comparison

| Feature | Python (PyWebView) | Rust (Tauri) |
|---------|-------------------|--------------|
| **Binary Size** | ~15 MB | ~8 MB |
| **RAM Usage** | ~80 MB | ~50 MB |
| **Startup Time** | ~2s | ~1s |
| **Build Time** | Fast | Slow (first build) |
| **Development** | Easy | Moderate |
| **Cross-compile** | Tricky | Excellent |

## Quick Start

```bash
# Setup wizard
./setup.sh

# Or manually:

# Python
cd python
pip install -r requirements.txt
python app.py

# Rust
cd rust/voice-shell-app
cargo tauri dev
```

## Project Structure

```
desktop/
├── README.md           # This file
├── setup.sh           # Setup wizard
├── python/            # Python/PyWebView implementation
│   ├── app.py         # Main application
│   ├── requirements.txt
│   └── README.md
└── rust/              # Rust/Tauri implementation
    ├── README.md
    └── voice-shell-app/
        ├── src-tauri/
        │   ├── src/
        │   │   ├── main.rs
        │   │   ├── commands.rs
        │   │   └── server.rs
        │   ├── Cargo.toml
        │   └── tauri.conf.json
        └── ui/
            └── index.html
```

## Architecture

Both implementations follow the same layered architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                       │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │           Native Window (PyWebView / Tauri)             │ │
│  │  ┌───────────────────────────────────────────────────┐  │ │
│  │  │              System WebView                        │  │ │
│  │  │        (WebKit / WebView2 / Blink)                │  │ │
│  │  │  ┌─────────────────────────────────────────────┐  │  │ │
│  │  │  │         Voice Shell Web UI                  │  │  │ │
│  │  │  │       (HTML/CSS/JavaScript)                 │  │  │ │
│  │  │  └─────────────────────────────────────────────┘  │  │ │
│  │  └───────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                    HTTP / WebSocket
                              │
┌─────────────────────────────────────────────────────────────┐
│                      SERVICE LAYER                           │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              VoiceShellServer (Python)                  │ │
│  │  - WebSocket server for real-time communication         │ │
│  │  - HTTP server for static files & REST API              │ │
│  │  - Session management                                    │ │
│  │  - Authentication (magic links)                          │ │
│  └─────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              LLMShell (Python)                          │ │
│  │  - Natural language parsing                              │ │
│  │  - Command generation                                    │ │
│  │  - Multi-language support                                │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                     DATA/STORAGE LAYER                       │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐ │
│  │   SQLite     │ │  Config      │ │  Session State       │ │
│  │   Database   │ │  Files       │ │  (in-memory)         │ │
│  └──────────────┘ └──────────────┘ └──────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                     EXTERNAL SERVICES                        │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐ │
│  │   Ollama     │ │  TTS Engine  │ │  Video Sources       │ │
│  │   (LLM API)  │ │  (espeak/    │ │  (RTSP/webcam)       │ │
│  │              │ │   pico)      │ │                      │ │
│  └──────────────┘ └──────────────┘ └──────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Isolation & Security

### Python (PyWebView)
- Process isolation via Python multiprocessing
- Server runs as daemon thread
- WebView sandboxed by system

### Rust (Tauri)
- Strong Rust memory safety
- Minimal permission model (allowlist)
- CSP headers enforced
- IPC validation via Rust type system
- Python backend as separate subprocess

## Building Executables

### Python

```bash
cd python
pip install pyinstaller
pyinstaller --onefile --windowed --name "StreamwareVoiceShell" app.py
# Output: dist/StreamwareVoiceShell
```

### Rust

```bash
cd rust/voice-shell-app
cargo tauri build
# Output: target/release/bundle/
```

## System Requirements

### Python
- Python 3.9+
- GTK3 (Linux) / WebView2 (Windows) / WebKit (macOS)

### Rust
- Rust 1.70+
- WebKit2GTK (Linux) / WebView2 (Windows) / WebKit (macOS)

## Troubleshooting

### Linux: WebView not found
```bash
sudo apt install libwebkit2gtk-4.0-dev
```

### macOS: Security warning
Right-click the app and select "Open" to bypass Gatekeeper.

### Windows: WebView2 missing
Download and install WebView2 Runtime from Microsoft.
