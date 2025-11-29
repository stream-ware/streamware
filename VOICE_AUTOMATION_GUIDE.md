# Voice & Automation Guide - Streamware 0.2.0

## 🎤 Overview

Streamware now includes voice control and desktop automation:
- **Voice Input (STT)** - Control sq with your voice
- **Voice Output (TTS)** - sq speaks responses
- **Mouse Control** - Automate mouse clicks and movement
- **Keyboard Control** - Automate typing and key presses
- **AI Automation** - Natural language to desktop actions

## 🚀 Quick Start

### Install Dependencies

```bash
# Voice (STT/TTS)
pip install SpeechRecognition pyttsx3 PyAudio

# Automation
pip install pyautogui

# Or let sq install them automatically!
```

### Basic Usage

```bash
# Voice input
sq voice listen

# Voice output
sq voice speak --text "Hello World"

# Voice command
sq voice command

# Mouse click
sq auto click --x 100 --y 200

# Type text
sq auto type --text "Hello"

# AI automation
sq auto automate --task "click the submit button"
```

## 🎤 Voice Commands

### Listen (STT)

```bash
# Listen for speech
sq voice listen

# Output:
{
  "success": true,
  "text": "list all files",
  "language": "en"
}
```

### Speak (TTS)

```bash
# Speak text
sq voice speak --text "Hello, I am Streamware"

# Different language
sq voice speak --text "Hola" --language es
```

### Voice Command Mode

```bash
# Listen and execute
sq voice command

# You say: "list files in current directory"
# sq executes: sq file . --list
# sq speaks: "Command completed successfully"
```

### Interactive Voice Mode

```bash
# Start interactive mode
sq voice interactive

# Say commands:
#  - "check status of services"
#  - "send message to slack"
#  - "list all files"
#  - "exit" to quit
```

## 🖱️ Mouse Automation

### Click

```bash
# Click at position
sq auto click --x 100 --y 200

# Double click
sq auto click --x 100 --y 200 --clicks 2

# Right click
sq auto click --x 100 --y 200 --button right
```

### Move

```bash
# Move mouse to position
sq auto move --x 500 --y 300

# Slow movement
sq auto move --x 500 --y 300 --duration 1.0
```

### Screenshot

```bash
# Take screenshot
sq auto screenshot --text screenshot.png
```

## ⌨️ Keyboard Automation

### Type Text

```bash
# Type text
sq auto type --text "Hello World"

# Slow typing
sq auto type --text "Hello" --interval 0.5
```

### Press Keys

```bash
# Press Enter
sq auto press --key enter

# Press Tab
sq auto press --key tab

# Press Escape
sq auto press --key esc
```

### Hotkeys

```bash
# Copy
sq auto hotkey --keys ctrl+c

# Paste
sq auto hotkey --keys ctrl+v

# Save
sq auto hotkey --keys ctrl+s

# Undo
sq auto hotkey --keys ctrl+z
```

## 🤖 AI Automation

### Natural Language Tasks

```bash
# Describe what you want
sq auto automate --task "click the submit button"

sq auto automate --task "type hello and press enter"

sq auto automate --task "fill the form with my name"
```

## 💡 Real-World Examples

### Example 1: Control Tkinter App

```bash
#!/bin/bash
# Automate your tkinter app

# Start app
cd test2
python app.py &
APP_PID=$!

sleep 2

# Click input field
sq auto click --x 300 --y 150

# Type text
sq auto type --text "Hello from Streamware!"

# Click Submit button
sq auto click --x 350 --y 180

# Cleanup
sleep 2
kill $APP_PID
```

### Example 2: Voice-Controlled Desktop

```bash
#!/bin/bash
# Control desktop with voice

while true; do
    # Listen
    command=$(sq voice listen | jq -r '.text')
    
    echo "You said: $command"
    
    # Exit check
    if echo "$command" | grep -i "exit"; then
        sq voice speak --text "Goodbye"
        break
    fi
    
    # Execute
    sq auto automate --task "$command"
    
    # Confirm
    sq voice speak --text "Task completed"
done
```

### Example 3: Smart Desktop Assistant

```bash
#!/bin/bash
# AI-powered desktop assistant

sq voice speak --text "Assistant activated"

while true; do
    command=$(sq voice listen | jq -r '.text')
    
    case "$command" in
        *"open"*)
            app=$(echo "$command" | sed 's/.*open //' | awk '{print $1}')
            sq auto automate --task "open $app"
            sq voice speak --text "Opening $app"
            ;;
        *"type"*)
            text=$(echo "$command" | sed 's/.*type //')
            sq auto type --text "$text"
            sq voice speak --text "Typed: $text"
            ;;
        *"exit"*)
            sq voice speak --text "Goodbye"
            break
            ;;
        *)
            sq auto automate --task "$command"
            sq voice speak --text "Done"
            ;;
    esac
done
```

### Example 4: Form Filler

```bash
#!/bin/bash
# Auto-fill forms

# Click name field
sq auto click --x 200 --y 100
sq auto type --text "John Doe"

# Tab to email
sq auto press --key tab
sq auto type --text "john@example.com"

# Tab to message
sq auto press --key tab
sq auto type --text "Hello from automation"

# Submit
sq auto press --key enter

sq voice speak --text "Form submitted"
```

### Example 5: Voice Shell

```bash
#!/bin/bash
# Voice-controlled shell

sq voice speak --text "Voice shell ready"

while true; do
    sq voice speak --text "Say your command"
    
    # Listen
    command=$(sq voice listen | jq -r '.text')
    
    # Exit
    if echo "$command" | grep -i "exit"; then
        sq voice speak --text "Exiting voice shell"
        break
    fi
    
    # Convert to sq command
    sq_cmd=$(sq llm "$command" --to-sq)
    
    # Speak the command
    sq voice speak --text "Executing: $sq_cmd"
    
    # Execute
    output=$(eval "$sq_cmd" 2>&1)
    
    # Speak result (first line only)
    result=$(echo "$output" | head -1)
    sq voice speak --text "$result"
done
```

### Example 6: Accessibility Features

```bash
#!/bin/bash
# Screen reader with voice control

sq voice speak --text "Accessibility mode"

while true; do
    command=$(sq voice listen | jq -r '.text')
    
    case "$command" in
        *"read"*)
            # Screenshot and describe
            sq auto screenshot --text temp.png
            desc=$(sq media describe_image --file temp.png | jq -r '.description')
            sq voice speak --text "$desc"
            ;;
        *"click"*)
            sq auto automate --task "$command"
            sq voice speak --text "Clicked"
            ;;
        *"exit"*)
            sq voice speak --text "Goodbye"
            break
            ;;
    esac
done
```

## 🔧 Finding Coordinates

### Method 1: Mouse Position

```python
import pyautogui
print(pyautogui.position())  # Current mouse position
```

### Method 2: Screenshot + Visual

```bash
# Take screenshot
sq auto screenshot --text screen.png

# Open and find element positions visually
# Use image viewer with coordinate display
```

### Method 3: AI Detection

```bash
# Take screenshot
sq auto screenshot --text app.png

# Ask AI where element is
sq media describe_image --file app.png \
  --prompt "Where is the submit button? Give x,y coordinates"
```

## 📊 Supported Engines

### Voice (STT)
- **Google Speech Recognition** - Default, works offline
- **Whisper** - OpenAI's speech recognition
- **PocketSphinx** - Offline recognition

### Voice (TTS)
- **pyttsx3** - Cross-platform (default)
- **espeak** - Linux
- **say** - macOS
- **PowerShell** - Windows

### Automation
- **pyautogui** - Cross-platform mouse/keyboard

## 🎯 Use Cases

### 1. Accessibility
Voice control for users with disabilities

### 2. Hands-Free Operation
Control computer while cooking, working, etc.

### 3. Testing Automation
Automate GUI testing

### 4. Data Entry
Automate repetitive form filling

### 5. Voice Assistant
Build custom voice assistants

### 6. Process Automation
Automate multi-step desktop workflows

## 📝 Tips

1. **Microphone**: Ensure good microphone quality for STT
2. **Coordinates**: Test coordinates before automation
3. **Delays**: Add small delays between actions
4. **Error Handling**: Wrap automation in try-catch
5. **Voice Feedback**: Use TTS to confirm actions
6. **AI Automation**: Be specific in task descriptions

## 🚀 Deploy Voice Service

```bash
# Create voice service
cat > voice_assistant.py << 'EOF'
from flask import Flask
import subprocess

app = Flask(__name__)

@app.route('/voice/listen')
def listen():
    result = subprocess.run(['sq', 'voice', 'listen'], 
                          capture_output=True, text=True)
    return result.stdout

@app.route('/voice/speak/<text>')
def speak(text):
    subprocess.run(['sq', 'voice', 'speak', '--text', text])
    return {"success": True}

app.run(port=8080)
EOF

# Deploy as service
sq service install --name voice-api --command "python voice_assistant.py"
sq service start --name voice-api
```

---

**Control Your Computer with Voice and AI! 🎤🖱️✨**
