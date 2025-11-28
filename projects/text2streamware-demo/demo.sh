#!/bin/bash
# Text to Streamware Demo - Qwen2.5 14B
# Interactive demonstration of natural language to sq commands

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info() {
    echo -e "${BLUE}→ $1${NC}"
}

success() {
    echo -e "${GREEN}✓ $1${NC}"
}

prompt_ai() {
    echo -e "${CYAN}🤖 $1${NC}"
}

echo "======================================================================"
echo "TEXT TO STREAMWARE - QWEN2.5 14B DEMO"
echo "======================================================================"
echo ""

# Check if Qwen2.5 is installed
info "Checking Qwen2.5 14B..."
if ! ollama list | grep -q "qwen2.5:14b"; then
    echo "⚠️  Qwen2.5 14B not found"
    read -p "Install now? (y/n) " install
    if [[ "$install" == "y" ]]; then
        info "Pulling Qwen2.5 14B (this may take a while)..."
        ollama pull qwen2.5:14b
        success "Model installed"
    else
        echo "Please install: ollama pull qwen2.5:14b"
        exit 1
    fi
else
    success "Qwen2.5 14B ready"
fi
echo ""

# Demo 1: Basic conversion
echo "=== Demo 1: Basic Natural Language to sq ==="
echo ""

requests=(
    "upload app.tar.gz to production server"
    "get all users from database and save as CSV"
    "send notification to Slack channel"
    "backup database to FTP server"
    "check if service is running on server"
)

for request in "${requests[@]}"; do
    info "Request: $request"
    
    # Convert using Qwen2.5
    cmd=$(python3 << EOF
from streamware.components.text2streamware import text_to_sq
result = text_to_sq("$request", model="qwen2.5:14b")
print(result)
EOF
    )
    
    prompt_ai "Generated: $cmd"
    echo ""
    sleep 1
done

echo ""
read -p "Press Enter to continue to Demo 2..."
echo ""

# Demo 2: Interactive mode
echo "=== Demo 2: Interactive Assistant ==="
echo ""
info "Type your requests and get sq commands instantly!"
info "Type 'quit' to exit"
echo ""

while true; do
    read -p "$(echo -e ${CYAN})What do you want to do? $(echo -e ${NC})" request
    
    if [[ "$request" == "quit" ]] || [[ "$request" == "exit" ]]; then
        break
    fi
    
    if [[ -z "$request" ]]; then
        continue
    fi
    
    # Generate command
    info "Thinking..."
    cmd=$(python3 << EOF
from streamware.components.text2streamware import text_to_sq
try:
    result = text_to_sq("$request", model="qwen2.5:14b")
    print(result)
except Exception as e:
    print(f"Error: {e}")
EOF
    )
    
    prompt_ai "Command: $cmd"
    
    # Ask to execute
    read -p "Execute this command? (y/n) " confirm
    if [[ "$confirm" == "y" ]]; then
        info "Executing..."
        if eval "$cmd" 2>&1; then
            success "Command executed successfully"
        else
            echo "⚠️  Command failed"
        fi
    fi
    
    echo ""
done

echo ""
read -p "Press Enter to continue to Demo 3..."
echo ""

# Demo 3: Complex scenarios
echo "=== Demo 3: Complex Multi-step Tasks ==="
echo ""

complex_requests=(
    "download data from API, convert to CSV, and upload to S3"
    "monitor all servers, if any fails alert on Slack and restart service"
    "query last week orders, generate report, email to manager"
)

for request in "${complex_requests[@]}"; do
    info "Task: $request"
    
    cmd=$(python3 << EOF
from streamware.components.text2streamware import text_to_sq
result = text_to_sq("$request", model="qwen2.5:14b")
print(result)
EOF
    )
    
    prompt_ai "Solution: $cmd"
    echo ""
    sleep 2
done

echo ""
read -p "Press Enter to continue to Demo 4..."
echo ""

# Demo 4: Command explanation
echo "=== Demo 4: Command Explanation ==="
echo ""

commands=(
    "sq ssh prod.com --deploy app.tar.gz --restart myapp"
    "sq postgres \"SELECT * FROM users WHERE active=true\" --csv"
    "sq kafka events --consume --json --stream"
)

for cmd in "${commands[@]}"; do
    info "Command: $cmd"
    
    explanation=$(python3 << EOF
from streamware.components.text2streamware import explain_command
result = explain_command("$cmd", model="qwen2.5:14b")
print(result)
EOF
    )
    
    prompt_ai "Explanation: $explanation"
    echo ""
    sleep 2
done

echo ""
read -p "Press Enter to continue to Demo 5..."
echo ""

# Demo 5: Real-world automation
echo "=== Demo 5: Build Real Automation ==="
echo ""

info "Let's build a monitoring script using natural language!"
echo ""

read -p "Describe what you want to monitor (e.g., 'check server health every minute'): " monitoring_task

if [[ -n "$monitoring_task" ]]; then
    info "Generating monitoring script..."
    
    script=$(python3 << EOF
from streamware.components.text2streamware import text_to_sq

task = "$monitoring_task"
cmd = text_to_sq(task, model="qwen2.5:14b")

# Create monitoring script
script = f"""#!/bin/bash
# Auto-generated monitoring script
# Task: {task}

while true; do
    {cmd}
    sleep 60
done
"""

print(script)
EOF
    )
    
    echo "$script" > monitor_generated.sh
    chmod +x monitor_generated.sh
    
    success "Generated monitor_generated.sh"
    echo ""
    info "Script content:"
    cat monitor_generated.sh
    echo ""
    
    read -p "Test run the monitoring script? (y/n) " test_run
    if [[ "$test_run" == "y" ]]; then
        info "Running for 10 seconds..."
        timeout 10s ./monitor_generated.sh || true
        success "Test completed"
    fi
fi

echo ""
echo "======================================================================"
echo "DEMO COMPLETE!"
echo "======================================================================"
echo ""
success "You've seen how to:"
echo "  1. Convert natural language to sq commands"
echo "  2. Use interactive mode"
echo "  3. Handle complex multi-step tasks"
echo "  4. Explain existing commands"
echo "  5. Build real automation scripts"
echo ""
info "Try it yourself:"
echo '  python3 -c "from streamware.components.text2streamware import text_to_sq; print(text_to_sq(\\"your request\\"))"'
echo ""
echo "Or use Quick CLI:"
echo "  sq llm 'upload file to server' --to-sq --provider ollama --model qwen2.5:14b"
echo ""
info "Qwen2.5 14B Model Info:"
echo "  • 14 billion parameters"
echo "  • Optimized for code generation"
echo "  • Runs locally with Ollama"
echo "  • FREE and open source"
echo ""
success "Happy automating! 🤖✨"
