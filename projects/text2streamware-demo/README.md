# Text to Streamware - Qwen2.5 14B Demo

Konwersja języka naturalnego na Streamware Quick komendy używając Qwen2.5 14B.

## 🚀 Quick Start

```bash
# 1. Zainstaluj Qwen2.5 14B
ollama pull qwen2.5:14b

# 2. Uruchom demo
bash demo.sh

# 3. Testuj!
```

## 💡 Przykłady Użycia

### Przykład 1: Proste Konwersje

```python
from streamware.components.text2streamware import text_to_sq

# Prosty request
cmd = text_to_sq("upload file to server", model="qwen2.5:14b")
print(cmd)
# Output: sq ssh prod.company.com --upload file.txt --remote /data/ --user deploy
```

### Przykład 2: Złożone Zadania

```python
# Złożony workflow
request = "get data from API, filter active users, save to CSV, upload to FTP"
cmd = text_to_sq(request, model="qwen2.5:14b")
print(cmd)
# Output: Multi-step command or pipeline
```

### Przykład 3: Quick CLI

```bash
# Użyj z linii komend
sq llm "backup database to remote server" \
    --to-sq \
    --provider ollama \
    --model qwen2.5:14b

# Output: sq postgres "pg_dump dbname" | gzip | sq ssh backup.com --upload ...
```

### Przykład 4: Interactive Mode

```bash
# Interaktywny asystent
while true; do
    read -p "What do you want to do? " request
    
    cmd=$(python3 -c "
from streamware.components.text2streamware import text_to_sq
print(text_to_sq('$request', model='qwen2.5:14b'))
")
    
    echo "Generated: $cmd"
    
    read -p "Execute? (y/n) " confirm
    [[ "$confirm" == "y" ]] && eval "$cmd"
done
```

### Przykład 5: Email to Command

```bash
# Przetwarzaj emaile jako komendy
sq email ops@company.com --subject "COMMAND:" --unread | \
while read email; do
    cmd=$(python3 -c "
from streamware.components.text2streamware import text_to_sq
print(text_to_sq('$email', model='qwen2.5:14b'))
")
    
    echo "Executing: $cmd"
    eval "$cmd"
done
```

### Przykład 6: Voice Commands

```bash
# 1. Nagraj głos
arecord -d 5 -f cd voice.wav

# 2. Transkrypcja (Whisper)
text=$(whisper voice.wav --model base)

# 3. Konwersja na sq
cmd=$(python3 -c "
from streamware.components.text2streamware import text_to_sq
print(text_to_sq('$text', model='qwen2.5:14b'))
")

# 4. Wykonaj
echo "Command: $cmd"
eval "$cmd"
```

### Przykład 7: AI DevOps Assistant

```bash
#!/bin/bash
# ai-devops.sh

devops_task() {
    local description="$1"
    
    echo "🤖 Processing: $description"
    
    # Generate command
    cmd=$(python3 -c "
from streamware.components.text2streamware import text_to_sq
print(text_to_sq('$description', model='qwen2.5:14b'))
")
    
    echo "Command: $cmd"
    
    # Safety check
    if [[ "$cmd" =~ (rm|delete|drop) ]]; then
        read -p "Dangerous operation! Confirm? (yes/no) " confirm
        [[ "$confirm" != "yes" ]] && return
    fi
    
    # Execute
    eval "$cmd"
    
    # Log
    sq postgres "INSERT INTO devops_log VALUES ('$description', '$cmd', NOW())"
}

# Usage
devops_task "deploy application to production"
devops_task "backup all databases"
devops_task "check disk space on servers"
```

### Przykład 8: Pipeline Builder

```python
#!/usr/bin/env python3
from streamware.components.text2streamware import text_to_sq

def build_pipeline(description):
    """Build pipeline from natural language"""
    
    # Split into steps
    steps = [s.strip() for s in description.split(',')]
    
    print(f"Building pipeline: {len(steps)} steps")
    print()
    
    commands = []
    for i, step in enumerate(steps):
        print(f"Step {i+1}: {step}")
        cmd = text_to_sq(step, model="qwen2.5:14b")
        print(f"Command: {cmd}")
        print()
        commands.append(cmd)
    
    # Create script
    script = "#!/bin/bash\nset -e\n\n"
    for i, cmd in enumerate(commands):
        script += f"# Step {i+1}\n{cmd}\n\n"
    
    return script

# Example
pipeline = build_pipeline("""
    fetch data from API endpoint,
    transform JSON to CSV format,
    upload CSV to FTP server,
    send completion notification to Slack
""")

print("Generated Pipeline:")
print(pipeline)

# Save and execute
with open('pipeline.sh', 'w') as f:
    f.write(pipeline)

import os
os.chmod('pipeline.sh', 0o755)
```

### Przykład 9: Monitoring Generator

```bash
# Generate monitoring script from description
monitoring="Check API health every minute, if down restart service and alert Slack"

python3 << EOF
from streamware.components.text2streamware import text_to_sq

cmd = text_to_sq("$monitoring", model="qwen2.5:14b")

script = f'''#!/bin/bash
# Auto-generated monitoring
while true; do
    {cmd}
    sleep 60
done
'''

with open('monitor.sh', 'w') as f:
    f.write(script)

import os
os.chmod('monitor.sh', 0o755)
print("Generated monitor.sh")
EOF

# Run monitoring
./monitor.sh
```

### Przykład 10: Explain Commands

```python
from streamware.components.text2streamware import explain_command

# Wyjaśnij co robi komenda
cmd = "sq ssh prod.com --deploy app.tar.gz --restart myapp --user deploy"

explanation = explain_command(cmd, model="qwen2.5:14b")
print(explanation)

# Output: "This command deploys app.tar.gz to production server, 
#          restarts the myapp service, using deploy user credentials"
```

## 🎯 Use Cases

### 1. DevOps Automation
```bash
# Natural language DevOps
"deploy latest version to all production servers"
→ sq ssh prod{1..3}.com --deploy app.tar.gz --restart service
```

### 2. Data Engineering
```bash
# ETL pipelines
"extract users from database, transform to JSON, load to data lake"
→ sq postgres "SELECT * FROM users" --json | sq s3 upload data-lake/users.json
```

### 3. Monitoring & Alerts
```bash
# Setup monitoring
"check server every 5 minutes, alert if CPU > 80%"
→ while sleep 300; do sq ssh server --exec "top -bn1" | grep "Cpu" | ... ; done
```

### 4. Backup Automation
```bash
# Backup workflows
"backup database daily at midnight to three locations"
→ cron job with sq postgres dump + sq ssh upload to multiple servers
```

### 5. Incident Response
```bash
# Quick incident handling
"restart all failed services and notify team"
→ sq ssh servers --exec "systemctl restart failed-services" && sq slack ops "Services restarted"
```

## 🔧 Configuration

### Environment Variables

```bash
# Qwen model
export QWEN_MODEL="qwen2.5:14b"

# Ollama URL
export OLLAMA_URL="http://localhost:11434"

# Temperature (lower = more precise)
export LLM_TEMPERATURE=0.1
```

### Model Selection

```bash
# Default: Qwen2.5 14B (best for code)
model="qwen2.5:14b"

# Alternatives
model="qwen2.5:7b"    # Faster, less accurate
model="qwen2.5:32b"   # Slower, more accurate
```

## 📊 Performance

| Model | Speed | Accuracy | RAM |
|-------|-------|----------|-----|
| qwen2.5:7b | Fast | Good | 8 GB |
| qwen2.5:14b | Medium | Excellent | 16 GB |
| qwen2.5:32b | Slow | Best | 32 GB |

**Recommended: qwen2.5:14b** (best balance)

## 🐛 Troubleshooting

### Model not found

```bash
ollama pull qwen2.5:14b
ollama list  # Verify installation
```

### Low accuracy

```bash
# Use larger model
export QWEN_MODEL="qwen2.5:32b"

# Or adjust temperature
export LLM_TEMPERATURE=0.05  # More deterministic
```

### Slow generation

```bash
# Use smaller model
export QWEN_MODEL="qwen2.5:7b"

# Or reduce max tokens
export MAX_TOKENS=200
```

## 📚 Documentation

- **Component:** `streamware/components/text2streamware.py`
- **Examples:** `examples/text2streamware_examples.py`
- **Demo:** `projects/text2streamware-demo/demo.sh`

## 🎓 Why Qwen2.5 14B?

✅ **Best for code generation** - Trained on code  
✅ **14B parameters** - Good accuracy/speed balance  
✅ **Open source** - FREE to use  
✅ **Local** - No API keys needed  
✅ **Fast** - Optimized for Ollama  
✅ **Multilingual** - Supports many languages  

## 🚀 Quick Commands

```bash
# Install model
ollama pull qwen2.5:14b

# Convert text
python3 -c "from streamware.components.text2streamware import text_to_sq; print(text_to_sq('upload file'))"

# Quick CLI
sq llm "your request" --to-sq --model qwen2.5:14b

# Run demo
bash demo.sh
```

---

**Built with ❤️ using Streamware + Qwen2.5 14B**

🤖 AI-Powered Command Generation!
