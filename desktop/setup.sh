#!/bin/bash
# Streamware Voice Shell Desktop - Setup Script
# Sets up both Python and Rust desktop applications

set -e

echo "🖥️  Streamware Voice Shell Desktop Setup"
echo "========================================"
echo ""

# Detect OS
case "$(uname -s)" in
    Linux*)     OS="Linux";;
    Darwin*)    OS="macOS";;
    MINGW*|MSYS*|CYGWIN*) OS="Windows";;
    *)          OS="Unknown";;
esac

echo "📦 Detected OS: $OS"
echo ""

# ============================================================================
# Python Desktop App Setup
# ============================================================================

setup_python() {
    echo "🐍 Setting up Python Desktop App..."
    cd python
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        echo "   ✅ Created virtual environment"
    fi
    
    # Activate and install dependencies
    source venv/bin/activate
    pip install -q -r requirements.txt
    
    # Install main streamware package in development mode
    pip install -q -e ../..
    
    echo "   ✅ Python app ready!"
    echo "   Run: cd python && source venv/bin/activate && python app.py"
    echo ""
    
    deactivate
    cd ..
}

# ============================================================================
# Rust/Tauri Desktop App Setup
# ============================================================================

setup_rust() {
    echo "🦀 Setting up Rust/Tauri Desktop App..."
    
    # Check if Rust is installed
    if ! command -v cargo &> /dev/null; then
        echo "   ⚠️  Rust not found. Installing..."
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
        source "$HOME/.cargo/env"
    fi
    
    # Check if Tauri CLI is installed
    if ! command -v cargo-tauri &> /dev/null; then
        echo "   📦 Installing Tauri CLI..."
        cargo install tauri-cli
    fi
    
    # Install Linux dependencies if needed
    if [ "$OS" = "Linux" ]; then
        echo "   📦 Checking Linux dependencies..."
        if command -v apt &> /dev/null; then
            sudo apt install -y libwebkit2gtk-4.0-dev build-essential curl wget \
                libssl-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev 2>/dev/null || true
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y webkit2gtk4.0-devel openssl-devel gtk3-devel librsvg2-devel 2>/dev/null || true
        fi
    fi
    
    cd rust/voice-shell-app
    
    # Build in release mode
    echo "   🔨 Building Tauri app (this may take a few minutes)..."
    cargo tauri build 2>/dev/null || echo "   ⚠️  Build may require additional setup, see rust/README.md"
    
    echo "   ✅ Rust app ready!"
    echo "   Run: cd rust/voice-shell-app && cargo tauri dev"
    echo ""
    
    cd ../..
}

# ============================================================================
# Main
# ============================================================================

echo "Select what to set up:"
echo "  1) Python Desktop App (pywebview)"
echo "  2) Rust Desktop App (Tauri)"
echo "  3) Both"
echo ""
read -p "Enter choice [1-3]: " choice

case $choice in
    1)
        setup_python
        ;;
    2)
        setup_rust
        ;;
    3)
        setup_python
        setup_rust
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "✅ Setup complete!"
echo ""
echo "Quick start:"
echo "  Python: cd desktop/python && python app.py"
echo "  Rust:   cd desktop/rust/voice-shell-app && cargo tauri dev"
