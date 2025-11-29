# 🤖 VSCode Bot Guide - Your AI Pair Programmer

## Overview

VSCode Bot is an AI-powered assistant that automates your development workflow in VSCode:
- **Clicks buttons** automatically (Accept, Reject, Run, Skip)
- **Recognizes UI** using AI vision (LLaVA)
- **Generates prompts** for continued development
- **Commits changes** to git automatically
- **Works autonomously** while you focus on architecture

## 🚀 Quick Start

### 1. Deploy the Bot
```bash
# Run deployment script
bash deploy_vscode_bot.sh

# Or manually
sq service install --name vscode-bot --command "python3 bot_service.py"
sq service start --name vscode-bot
```

### 2. Basic Usage
```bash
# Click Accept All
sq bot click_button --button accept_all

# Continue work for 5 iterations
sq bot continue_work --iterations 5

# Watch and respond automatically
sq bot watch --iterations 10
```

## 📋 Features

### 1. Button Clicking
```bash
# Accept all changes
sq bot click_button --button accept_all

# Reject all changes  
sq bot click_button --button reject_all

# Click Run button
sq bot click_button --button run

# Click Skip button
sq bot click_button --button skip

# Click Continue button
sq bot click_button --button continue
```

### 2. AI Vision Recognition
```bash
# Find button by name
sq bot find_button --button "Submit" --screenshot vscode.png

# Bot will use LLaVA to:
# - Analyze the screenshot
# - Find the button
# - Return exact coordinates
```

### 3. Prompt Generation
```bash
# Generate next development task
sq bot generate_prompt --task "fix failing tests"

# Bot analyzes:
# - Git status
# - Recent changes
# - Test results
# - Generates intelligent next step
```

### 4. Git Operations
```bash
# Commit changes
sq bot commit_changes --message "Bot: Auto fixes"

# Commit and push
sq bot commit_changes --message "Bot update" --push true
```

### 5. Autonomous Work
```bash
# Continue work for N iterations
sq bot continue_work --iterations 10 --delay 3

# Each iteration:
# 1. Takes screenshot
# 2. Analyzes what to do (AI vision)
# 3. Clicks appropriate buttons
# 4. Generates prompts if needed
# 5. Commits changes periodically
```

### 6. Watch Mode
```bash
# Watch and respond automatically
sq bot watch --iterations 20 --delay 2

# Bot monitors VSCode and:
# - Accepts changes when prompted
# - Runs commands when needed
# - Generates prompts when waiting
# - Responds to UI events
```

## 💡 Real-World Workflows

### Workflow 1: Continuous Development
```bash
#!/bin/bash
# Bot continues your work while you're away

# Start autonomous bot
sq bot continue_work \
    --iterations 50 \
    --delay 3 \
    --task "implement remaining features"
    --workspace ~/myproject

# Bot will:
# - Click Accept/Reject as needed
# - Run tests
# - Generate next tasks
# - Commit every 3 iterations
```

### Workflow 2: Test Fixing Loop
```bash
#!/bin/bash
# Bot fixes tests automatically

while true; do
    # Run tests
    sq bot click_button --button run
    sleep 5
    
    # If tests fail, generate fix
    sq bot generate_prompt --task "fix failing tests"
    sleep 2
    
    # Accept AI suggestions
    sq bot click_button --button accept_all
    sleep 2
    
    # Commit if tests pass
    if make test 2>&1 | grep -q "passed"; then
        sq bot commit_changes --message "Bot: Fixed tests"
        break
    fi
done
```

### Workflow 3: PR Review Automation
```bash
#!/bin/bash
# Bot helps with PR reviews

# Accept obvious changes
sq bot click_button --button accept_all

# For complex changes, ask AI
sq media describe_image --file vscode.png \
    --prompt "Should I accept these code changes? Explain."

# Generate review comments
sq bot generate_prompt --task "write PR review comments"

# Commit review
git add .
git commit -m "Review: $(sq bot generate_prompt --task 'summarize review')"
```

### Workflow 4: Documentation Generation
```bash
#!/bin/bash
# Bot generates docs while coding

for iteration in {1..10}; do
    # Accept code changes
    sq bot click_button --button accept_all
    sleep 2
    
    # Generate documentation
    sq bot generate_prompt --task "write documentation for new code"
    sleep 2
    
    # Accept documentation
    sq bot click_button --button accept_all
    sleep 2
    
    # Commit
    sq bot commit_changes --message "Bot: Code + docs iteration $iteration"
done
```

### Workflow 5: Voice-Controlled Bot
```bash
#!/bin/bash
# Control bot with voice commands

while true; do
    # Listen for command
    command=$(sq voice listen | jq -r '.text')
    
    case "$command" in
        *"accept"*)
            sq bot click_button --button accept_all
            sq voice speak --text "Changes accepted"
            ;;
        *"reject"*)
            sq bot click_button --button reject_all
            sq voice speak --text "Changes rejected"
            ;;
        *"continue"*)
            sq bot continue_work --iterations 5
            sq voice speak --text "Continuing work"
            ;;
        *"commit"*)
            sq bot commit_changes --message "Voice command commit"
            sq voice speak --text "Changes committed"
            ;;
        *"stop"*)
            sq voice speak --text "Bot stopped"
            break
            ;;
    esac
done
```

## 🎯 Integration with Cascade

### Scenario: Working with Cascade in VSCode

```bash
#!/bin/bash
# Bot works with Cascade AI assistant

# Bot loop
while true; do
    # Screenshot VSCode
    sq auto screenshot --text vscode.png
    
    # Analyze with AI
    action=$(sq media describe_image --file vscode.png \
        --prompt "What should I do? Accept all, Reject all, Run, or Continue?" \
        --model llava | jq -r '.description')
    
    echo "AI suggests: $action"
    
    # Take action
    if echo "$action" | grep -i "accept"; then
        sq bot click_button --button accept_all
        echo "✓ Accepted changes"
        
    elif echo "$action" | grep -i "run"; then
        sq bot click_button --button run
        echo "✓ Ran command"
        
    elif echo "$action" | grep -i "continue"; then
        sq bot click_button --button continue
        echo "✓ Clicked continue"
        
    elif echo "$action" | grep -i "generate"; then
        # Generate next prompt
        prompt=$(sq bot generate_prompt --task "next development step" | jq -r '.prompt')
        echo "Generated prompt: $prompt"
        
        # Could send to Cascade via API
        # curl -X POST cascade-api/prompt -d "$prompt"
    fi
    
    sleep 3
done
```

## 🔧 Configuration

### Button Locations
Bot knows typical locations but can learn yours:

```python
# In vscode_bot.py, customize BUTTON_PATTERNS
BUTTON_PATTERNS = {
    "accept_all": {
        "text": ["Accept all"],
        "typical_location": (870, 130),  # Your screen
    }
}
```

### AI Models
```bash
# Use different models
sq bot continue_work --model qwen2.5:14b  # Code generation
sq bot find_button --model llava           # Vision
```

### Timing
```bash
# Adjust delays
sq bot continue_work --delay 2  # 2 seconds between actions
sq bot watch --delay 5          # 5 seconds in watch mode
```

## 📊 Monitoring

### Check Bot Status
```bash
# Service status
sq service status --name vscode-bot

# Logs
tail -f ~/.streamware/logs/vscode-bot.log

# Results
sq bot continue_work --iterations 5 | jq '.results'
```

### Debug Mode
```bash
# Run with verbose output
sq bot continue_work --iterations 1 --debug
```

## 🛡️ Safety

### Safeguards
1. **Manual Review**: Bot can run in "review mode" where it shows what it would do
2. **Commit Messages**: All commits tagged with "Bot:"
3. **Iteration Limits**: Set max iterations to prevent runaway
4. **Branch Protection**: Work on feature branches only

```bash
# Safe mode
git checkout -b bot-work
sq bot continue_work --iterations 10 --auto-commit false
# Review changes before committing
```

## 🎓 Tips & Tricks

### Tip 1: Find Coordinates
```bash
# Method 1: PyAutoGUI
python3 -c "import pyautogui; print(pyautogui.position())"

# Method 2: AI Vision
sq auto screenshot --text screen.png
sq media describe_image --file screen.png \
    --prompt "Where is the Accept All button? Give x,y coordinates"
```

### Tip 2: Custom Buttons
```bash
# Bot can find any button
sq bot find_button --button "Your Custom Button" --screenshot vscode.png
```

### Tip 3: Combine with Other Tools
```bash
# Bot + Tests + Lint
sq bot continue_work --iterations 1
make test && make lint
sq bot commit_changes --message "Bot: Tests passing"
```

## 📦 Deployment Options

### Option 1: Systemd Service
```bash
bash deploy_vscode_bot.sh
```

### Option 2: Docker
```dockerfile
FROM python:3.11
RUN pip install streamware
CMD ["sq", "bot", "watch", "--iterations", "100"]
```

### Option 3: Cron Job
```cron
# Run bot every hour
0 * * * * cd ~/project && sq bot continue_work --iterations 5
```

## 🎉 Summary

VSCode Bot is your AI pair programmer that:
- ✅ **Automates clicking** Accept/Reject/Run buttons
- ✅ **Recognizes UI** with AI vision (LLaVA)
- ✅ **Generates prompts** intelligently
- ✅ **Commits changes** automatically
- ✅ **Works autonomously** for hours
- ✅ **Integrates with voice** control
- ✅ **Deploys easily** as a service

**Let the bot handle the repetitive tasks while you focus on architecture! 🚀**

---

**Deploy now:**
```bash
bash deploy_vscode_bot.sh
./start_bot.sh
```
