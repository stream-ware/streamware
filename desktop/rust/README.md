# Streamware Voice Shell - Rust Desktop App (Tauri)

High-performance desktop application using Tauri framework.
Uses system WebView for minimal binary size and optimal performance.

## Features
- **Lightweight** - Uses system WebView (no bundled Chromium)
- **Fast** - Rust backend for native performance
- **Secure** - Strong isolation, minimal permissions
- **Cross-platform** - Windows, macOS, Linux
- **Small binary** - Typically 3-10MB vs 150MB+ for Electron

## Prerequisites

```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Linux dependencies (Ubuntu/Debian)
sudo apt install libwebkit2gtk-4.0-dev build-essential curl wget \
    libssl-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev

# Install Tauri CLI
cargo install tauri-cli
```

## Development

```bash
cd desktop/rust/voice-shell-app

# Development mode (hot reload)
cargo tauri dev

# Build release
cargo tauri build
```

## Architecture

```
┌────────────────────────────────────────┐
│         Tauri Window (Rust)            │
│  ┌──────────────────────────────────┐  │
│  │    System WebView (WebKit/Edge)  │  │
│  │       Voice Shell Web UI         │  │
│  └──────────────────────────────────┘  │
│                  │ IPC                 │
│  ┌──────────────────────────────────┐  │
│  │    Rust Backend (Commands)       │  │
│  │  - Process management            │  │
│  │  - System tray                   │  │
│  │  - File system access            │  │
│  └──────────────────────────────────┘  │
└────────────────────────────────────────┘
              │ Spawns
              ▼
┌────────────────────────────────────────┐
│   Python Backend (subprocess)          │
│   VoiceShellServer                     │
└────────────────────────────────────────┘
```

## Project Structure

```
voice-shell-app/
├── src/
│   └── main.rs          # Rust entry point
├── src-tauri/
│   ├── src/
│   │   ├── main.rs      # Tauri app logic
│   │   ├── commands.rs  # IPC commands
│   │   └── server.rs    # Python server management
│   ├── Cargo.toml       # Rust dependencies
│   └── tauri.conf.json  # Tauri configuration
└── ui/                  # Symlink to web UI or bundled
```

## Binary Size Comparison

| Framework | Binary Size | RAM Usage |
|-----------|-------------|-----------|
| Tauri     | ~8 MB       | ~50 MB    |
| PyWebView | ~15 MB      | ~80 MB    |
| Electron  | ~150 MB     | ~200 MB   |
