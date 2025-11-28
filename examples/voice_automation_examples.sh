#!/bin/bash
# Voice & Automation Examples
# Control computer with voice and automate desktop tasks

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo "======================================================================"
echo "VOICE & AUTOMATION EXAMPLES - Streamware"
echo "======================================================================"
echo ""

# Example 1: Voice Commands
echo -e "${BLUE}=== Example 1: Voice Control ===${NC}"
echo ""
echo "# Listen for voice input"
echo "sq voice listen"
echo ""
echo "# Speak text"
echo 'sq voice speak --text "Hello, this is Streamware speaking"'
echo ""
echo "# Voice command mode (listen and execute)"
echo "sq voice command"
echo "# Say: 'list files in current directory'"
echo "# Executes: sq file . --list"
echo ""

# Example 2: Interactive Voice Mode
echo -e "${BLUE}=== Example 2: Interactive Voice Mode ===${NC}"
echo ""
echo "# Start interactive voice control"
echo "sq voice interactive"
echo ""
echo "# Say commands:"
echo "#  - 'check status of services'"
echo "#  - 'list all files'"
echo "#  - 'send message to slack'"
echo "#  - 'exit' to quit"
echo ""

# Example 3: Mouse Automation
echo -e "${BLUE}=== Example 3: Mouse Control ===${NC}"
echo ""
echo "# Click at specific position"
echo "sq auto click --x 100 --y 200"
echo ""
echo "# Move mouse"
echo "sq auto move --x 500 --y 300"
echo ""
echo "# Double click"
echo "sq auto click --x 100 --y 200 --clicks 2"
echo ""

# Example 4: Keyboard Automation
echo -e "${BLUE}=== Example 4: Keyboard Control ===${NC}"
echo ""
echo "# Type text"
echo 'sq auto type --text "Hello World"'
echo ""
echo "# Press key"
echo "sq auto press --key enter"
echo ""
echo "# Hotkey combination"
echo "sq auto hotkey --keys ctrl+c"
echo "sq auto hotkey --keys ctrl+v"
echo ""

# Example 5: AI-Powered Automation
echo -e "${CYAN}=== Example 5: AI Automation ===${NC}"
echo ""
echo "# Describe task in natural language"
echo 'sq auto automate --task "click the submit button and type hello"'
echo ""
echo 'sq auto automate --task "open calculator and type 2+2"'
echo ""
echo 'sq auto automate --task "fill the form with my name"'
echo ""

# Example 6: Voice-Controlled Desktop
echo -e "${CYAN}=== Example 6: Voice-Controlled Desktop ===${NC}"
echo ""
cat << 'EOF'
#!/bin/bash
# Voice-controlled automation

while true; do
    # Listen for command
    command=$(sq voice listen | jq -r '.text')
    
    echo "You said: $command"
    
    # Exit check
    if echo "$command" | grep -i "exit"; then
        sq voice speak --text "Goodbye"
        break
    fi
    
    # Convert to automation task
    sq auto automate --task "$command"
    
    # Confirm
    sq voice speak --text "Task completed"
done
EOF
echo ""

# Example 7: Click Tkinter Button
echo -e "${CYAN}=== Example 7: Automate Tkinter App ===${NC}"
echo ""
cat << 'EOF'
#!/bin/bash
# Automate the test2 tkinter app

# Start app in background
cd test2
python app.py &
APP_PID=$!

sleep 2  # Wait for app to open

# Take screenshot to see positions
sq auto screenshot --text app_screenshot.png

# Click in the input field (adjust coordinates)
sq auto click --x 300 --y 150

# Type text
sq auto type --text "Hello from Streamware!"

# Click Submit button (adjust coordinates)
sq auto click --x 350 --y 180

# Wait and close
sleep 2
kill $APP_PID
EOF
echo ""

# Example 8: Voice-Controlled Tkinter
echo -e "${CYAN}=== Example 8: Voice Control Tkinter App ===${NC}"
echo ""
cat << 'EOF'
#!/bin/bash
# Control tkinter app with voice

# Start app
cd test2
python app.py &
APP_PID=$!

sleep 2

# Voice interaction
sq voice speak --text "What would you like to type?"

# Listen
text=$(sq voice listen | jq -r '.text')

# Click input field
sq auto click --x 300 --y 150

# Type the text
sq auto type --text "$text"

# Click button
sq auto click --x 350 --y 180

# Confirm
sq voice speak --text "Form submitted with: $text"

# Cleanup
sleep 2
kill $APP_PID
EOF
echo ""

# Example 9: Smart Desktop Assistant
echo -e "${CYAN}=== Example 9: Smart Desktop Assistant ===${NC}"
echo ""
cat << 'EOF'
#!/bin/bash
# AI-powered desktop assistant

sq voice speak --text "Desktop assistant activated"

while true; do
    # Listen
    command=$(sq voice listen | jq -r '.text')
    
    echo "Command: $command"
    
    # Check for exit
    if echo "$command" | grep -i "exit\|quit\|stop"; then
        sq voice speak --text "Assistant deactivated"
        break
    fi
    
    # Process command
    case "$command" in
        *"open"*)
            # Extract app name and open
            app=$(echo "$command" | sed 's/.*open //' | awk '{print $1}')
            sq auto automate --task "open $app"
            sq voice speak --text "Opening $app"
            ;;
        *"type"*)
            # Extract text and type
            text=$(echo "$command" | sed 's/.*type //')
            sq auto type --text "$text"
            sq voice speak --text "Typed: $text"
            ;;
        *"click"*)
            # Let AI figure it out
            sq auto automate --task "$command"
            sq voice speak --text "Clicked"
            ;;
        *)
            # General automation
            sq auto automate --task "$command"
            sq voice speak --text "Task completed"
            ;;
    esac
    
    sleep 1
done
EOF
echo ""

# Example 10: Form Filler
echo -e "${CYAN}=== Example 10: Auto Form Filler ===${NC}"
echo ""
cat << 'EOF'
#!/bin/bash
# Fill forms automatically

# Define form data
NAME="John Doe"
EMAIL="john@example.com"
MESSAGE="Hello from Streamware automation"

# Click name field (adjust coordinates)
sq auto click --x 200 --y 100
sq auto type --text "$NAME"

# Tab to next field
sq auto press --key tab

# Type email
sq auto type --text "$EMAIL"

# Tab to message
sq auto press --key tab

# Type message
sq auto type --text "$MESSAGE"

# Submit (Enter or click button)
sq auto press --key enter
# Or: sq auto click --x 300 --y 250

sq voice speak --text "Form submitted successfully"
EOF
echo ""

# Example 11: Screen Reader
echo -e "${CYAN}=== Example 11: Screen Reader ===${NC}"
echo ""
cat << 'EOF'
#!/bin/bash
# Read screen content with OCR and voice

# Take screenshot
sq auto screenshot --text screen.png

# Analyze with AI
desc=$(sq media describe_image --file screen.png | jq -r '.description')

# Read it aloud
sq voice speak --text "$desc"
EOF
echo ""

# Example 12: Accessibility Assistant
echo -e "${CYAN}=== Example 12: Accessibility Assistant ===${NC}"
echo ""
cat << 'EOF'
#!/bin/bash
# Voice-controlled accessibility

sq voice speak --text "Accessibility mode enabled. What would you like to do?"

while true; do
    command=$(sq voice listen | jq -r '.text')
    
    case "$command" in
        *"read"*)
            # Take screenshot and describe
            sq auto screenshot --text temp.png
            desc=$(sq media describe_image --file temp.png | jq -r '.description')
            sq voice speak --text "$desc"
            ;;
        *"click"*|*"press"*|*"tap"*)
            # AI automation
            sq auto automate --task "$command"
            sq voice speak --text "Done"
            ;;
        *"exit"*)
            sq voice speak --text "Goodbye"
            break
            ;;
        *)
            sq voice speak --text "Command: $command"
            sq auto automate --task "$command"
            ;;
    esac
done
EOF
echo ""

echo "======================================================================"
echo "EXAMPLES COMPLETE!"
echo "======================================================================"
echo ""
echo -e "${GREEN}✓ Voice input (STT)${NC}"
echo -e "${GREEN}✓ Voice output (TTS)${NC}"
echo -e "${GREEN}✓ Voice commands${NC}"
echo -e "${GREEN}✓ Mouse control${NC}"
echo -e "${GREEN}✓ Keyboard control${NC}"
echo -e "${GREEN}✓ AI automation${NC}"
echo -e "${GREEN}✓ Desktop assistant${NC}"
echo -e "${GREEN}✓ Accessibility features${NC}"
echo ""
echo "Try it yourself:"
echo "  # Voice input"
echo "  sq voice listen"
echo ""
echo "  # Voice output"
echo "  sq voice speak --text 'Hello World'"
echo ""
echo "  # Click mouse"
echo "  sq auto click --x 100 --y 200"
echo ""
echo "  # Type text"
echo "  sq auto type --text 'Hello'"
echo ""
echo "  # AI automation"
echo "  sq auto automate --task 'click the button'"
echo ""
