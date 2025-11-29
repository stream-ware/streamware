#!/bin/bash
# Deploy VSCode Bot - Your AI Pair Programmer

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║         VSCode Bot - AI Pair Programmer Deploy          ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check requirements
echo -e "${BLUE}=== Checking Requirements ===${NC}"

# Install system and Python dependencies
echo "Installing dependencies..."

# System packages
if command -v apt-get &> /dev/null; then
    sudo apt-get update -qq 2>/dev/null || true
    sudo apt-get install -y -qq gnome-screenshot scrot 2>/dev/null || true
fi

# Python packages
pip install -q "Pillow>=9.2.0" pyscreeze pyautogui 2>/dev/null || true
echo "✓ Dependencies installed"

# Check Ollama
if ! command -v ollama &> /dev/null; then
    echo -e "${YELLOW}⚠️  Ollama not installed${NC}"
    echo "Installing Ollama..."
    curl -fsSL https://ollama.ai/install.sh | sh
else
    echo "✓ Ollama installed"
fi

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Ollama not running${NC}"
    echo "Starting Ollama..."
    ollama serve &
    sleep 3
else
    echo "✓ Ollama running"
fi

# Pull required models
echo ""
echo -e "${BLUE}=== Installing AI Models ===${NC}"

if ! ollama list | grep -q "llava"; then
    echo "Installing LLaVA (vision model)..."
    ollama pull llava
else
    echo "✓ LLaVA installed"
fi

if ! ollama list | grep -q "qwen2.5:14b"; then
    echo "Installing Qwen2.5 14B (code generation)..."
    ollama pull qwen2.5:14b
else
    echo "✓ Qwen2.5 14B installed"
fi

# Fix X11 permissions
echo ""
echo -e "${BLUE}=== Fixing X11 Permissions ===${NC}"
xhost +local: 2>/dev/null && echo "✓ X11 permissions set" || echo "⚠️  Could not set X11 permissions"

# Create bot service
echo ""
echo -e "${BLUE}=== Creating Bot Service ===${NC}"

cat > /tmp/vscode_bot_service.py << 'EOF'
#!/usr/bin/env python3
"""VSCode Bot Service - Runs continuously"""

import time
import sys
from streamware import flow

def run_bot():
    """Run the bot"""
    print("🤖 VSCode Bot Started")
    print("=" * 60)
    
    # Run continuous work
    result = flow(
        "vscode://continue_work?"
        "iterations=10&"
        "delay=3.0&"
        "auto_commit=true"
    ).run()
    
    print("\n📊 Results:")
    print(f"Iterations: {result.get('iterations_completed', 0)}")
    print(f"Success: {result.get('success', False)}")

if __name__ == "__main__":
    try:
        run_bot()
    except KeyboardInterrupt:
        print("\n\n👋 Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
EOF

chmod +x /tmp/vscode_bot_service.py

# Install as service
echo ""
echo -e "${BLUE}=== Installing as Service ===${NC}"

sq service install \
    --name vscode-bot \
    --command "python3 /tmp/vscode_bot_service.py" \
    --dir "$(pwd)"

echo "✓ Service installed"

# Create control scripts
echo ""
echo -e "${BLUE}=== Creating Control Scripts ===${NC}"

# Start script
cat > start_bot.sh << 'EOF'
#!/bin/bash
echo "🤖 Starting VSCode Bot..."

# Fix X11
export DISPLAY=:0
xhost +local: 2>/dev/null

# Start service
sq service start --name vscode-bot

echo "✓ Bot started!"
echo ""
echo "Check status: sq service status --name vscode-bot"
echo "View logs: tail -f ~/.streamware/logs/vscode-bot.log"
echo "Stop bot: ./stop_bot.sh"
EOF

# Stop script
cat > stop_bot.sh << 'EOF'
#!/bin/bash
echo "🛑 Stopping VSCode Bot..."
sq service stop --name vscode-bot
echo "✓ Bot stopped"
EOF

# Status script
cat > bot_status.sh << 'EOF'
#!/bin/bash
sq service status --name vscode-bot
EOF

chmod +x start_bot.sh stop_bot.sh bot_status.sh

echo "✓ Control scripts created"

# Create example usage
echo ""
echo -e "${BLUE}=== Creating Example Scripts ===${NC}"

cat > example_bot_usage.sh << 'EOF'
#!/bin/bash
# Example VSCode Bot Usage

# 1. Click Accept All button
sq bot click_button --button accept_all

# 2. Click Run button
sq bot click_button --button run

# 3. Generate next prompt
sq bot generate_prompt --task "fix failing tests"

# 4. Commit changes
sq bot commit_changes --message "Bot: Auto fixes"

# 5. Continue work for 5 iterations
sq bot continue_work --iterations 5 --delay 2

# 6. Watch and respond automatically
sq bot watch --iterations 10 --delay 3

# 7. Accept changes
sq bot accept_changes

# 8. Reject changes
sq bot reject_changes
EOF

chmod +x example_bot_usage.sh

echo "✓ Example scripts created"

# Summary
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    ✓ DEPLOYMENT COMPLETE                 ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}🤖 VSCode Bot is ready!${NC}"
echo ""
echo -e "${YELLOW}Quick Start:${NC}"
echo "  ./start_bot.sh          # Start the bot"
echo "  ./stop_bot.sh           # Stop the bot"
echo "  ./bot_status.sh         # Check status"
echo ""
echo -e "${YELLOW}Manual Commands:${NC}"
echo "  sq bot click_button --button accept_all"
echo "  sq bot continue_work --iterations 5"
echo "  sq bot watch --iterations 10"
echo ""
echo -e "${YELLOW}Service Management:${NC}"
echo "  sq service start --name vscode-bot"
echo "  sq service stop --name vscode-bot"
echo "  sq service status --name vscode-bot"
echo ""
echo -e "${YELLOW}Logs:${NC}"
echo "  tail -f ~/.streamware/logs/vscode-bot.log"
echo ""
echo -e "${GREEN}Bot will:${NC}"
echo "  ✓ Click Accept/Reject/Run buttons automatically"
echo "  ✓ Generate next development prompts"
echo "  ✓ Recognize UI elements with AI vision"
echo "  ✓ Commit and push changes"
echo "  ✓ Continue work autonomously"
echo ""
echo -e "${CYAN}Happy coding with your AI pair programmer! 🚀${NC}"
echo ""
