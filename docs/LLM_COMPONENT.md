# LLM Component - AI-Powered DSL Conversion

Komponent LLM dla Streamware - konwersja języka naturalnego na SQL, Streamware commands i inne DSL.

## 🤖 Co To Jest?

LLM Component pozwala używać AI do:
- ✅ Konwersji języka naturalnego na SQL
- ✅ Generowania komend Streamware (sq)
- ✅ Tworzenia bash scripts
- ✅ Analizy tekstów
- ✅ Automatyzacji zadań

## 🚀 Quick Start

### Instalacja

```bash
# Opcja 1: OpenAI (płatne, najlepsze wyniki)
pip install openai
export OPENAI_API_KEY=your_key_here

# Opcja 2: Anthropic Claude (płatne)
pip install anthropic
export ANTHROPIC_API_KEY=your_key_here

# Opcja 3: Ollama (DARMOWE, lokalne!)
# Download from: https://ollama.ai
ollama pull llama3.2
```

## 💡 Przykłady Użycia - Quick Style

### 1. Natural Language → SQL

```bash
# Prosty query
sq llm "get all users older than 30" --to-sql

# Output:
# SELECT * FROM users WHERE age > 30;

# Z wykonaniem
sq llm "find active orders from last week" --to-sql --execute

# Różne provider
sq llm "count products in stock" --to-sql --provider ollama
```

### 2. Natural Language → Streamware Commands

```bash
# Generate sq command
sq llm "upload file to SSH server" --to-sq

# Output:
# sq ssh prod.com --upload file.txt --remote /data/

# Execute generated command
sq llm "get users from API and save to database" --to-sq --execute

# More examples
sq llm "send email with report" --to-sq
sq llm "backup database to FTP" --to-sq
sq llm "monitor server and alert on Slack" --to-sq
```

### 3. Text Analysis

```bash
# Analyze text
sq llm "Streamware is great!" --analyze

# Output JSON:
# {
#   "sentiment": "positive",
#   "key_points": [...],
#   "summary": "..."
# }

# From file
sq llm --analyze --input document.txt

# From stdin
cat report.txt | sq llm --analyze
```

### 4. Summarization

```bash
# Summarize text
echo "Long article text..." | sq llm --summarize

# From file
sq llm --summarize --input article.txt
```

## 🎯 Real-World Examples

### Example 1: Interactive SQL Builder

```bash
#!/bin/bash
# sql-assistant.sh - Interactive SQL query builder

while true; do
    echo ""
    read -p "What data do you need? " question
    
    # Generate SQL
    sql=$(sq llm "$question" --to-sql --provider ollama --quiet)
    
    echo "Generated SQL:"
    echo "$sql"
    echo ""
    
    # Confirm execution
    read -p "Execute query? (y/n) " confirm
    
    if [[ "$confirm" == "y" ]]; then
        sq postgres "$sql" --json
    fi
done
```

**Użycie:**
```bash
./sql-assistant.sh

# What data do you need? all users who signed up this month
# Generated SQL: SELECT * FROM users WHERE created_at >= DATE_TRUNC('month', CURRENT_DATE)
# Execute query? (y/n) y
```

### Example 2: Email-Driven Automation

```bash
#!/bin/bash
# email-automation.sh - Process emails with AI

while true; do
    # Check for command emails
    sq email deploy@company.com \
        --password "$EMAIL_PASSWORD" \
        --subject "COMMAND:" \
        --save /tmp/commands.json
    
    # Process each email
    for email in $(cat /tmp/commands.json | jq -r '.[].body'); do
        # Generate Streamware command from email
        cmd=$(sq llm "$email" --to-sq --provider ollama --quiet)
        
        echo "Email request: $email"
        echo "Generated command: $cmd"
        
        # Execute command
        eval "$cmd"
        
        # Notify completion
        sq slack automation \
            --message "✓ Executed: $cmd" \
            --token "$SLACK_TOKEN"
    done
    
    sleep 60
done
```

**Email Examples:**
```
Subject: COMMAND: Deploy application
Body: Upload app.tar.gz to production server and restart the service

→ Generates: sq ssh prod.com --deploy app.tar.gz --restart myapp
```

### Example 3: Data Migration Assistant

```bash
# migration-assistant.sh

echo "Data Migration Assistant"
read -p "Describe the migration: " task

# Generate migration plan
plan=$(sq llm "$task" --to-bash --provider ollama)

echo ""
echo "Generated Migration Plan:"
echo "$plan"
echo ""

read -p "Proceed with migration? (y/n) " confirm

if [[ "$confirm" == "y" ]]; then
    eval "$plan"
    sq postgres "INSERT INTO migration_log (task, timestamp) VALUES ('$task', NOW())"
    sq slack data --message "✓ Migration completed: $task"
fi
```

### Example 4: Monitoring Setup Generator

```bash
# Generate monitoring script from description
task="Monitor API health every minute, check /health endpoint, alert on Slack if down"

# Generate script
sq llm "$task" --to-bash --provider ollama > monitor.sh
chmod +x monitor.sh

# Review and run
cat monitor.sh
./monitor.sh
```

### Example 5: Report Generator

```bash
#!/bin/bash
# smart-reports.sh - AI-powered reporting

# User describes what they want
request="Generate a weekly sales report showing top 10 products by revenue"

# Convert to SQL
sql=$(sq llm "$request" --to-sql --provider ollama --quiet)

# Execute query
sq postgres "$sql" --csv --save report.csv

# Generate insights
insights=$(cat report.csv | sq llm --analyze --provider ollama)

# Create summary email
sq email manager@company.com \
    --subject "Weekly Sales Report" \
    --body "$insights" \
    --attach report.csv
```

## 🐍 Python API

### Flow Style

```python
from streamware import flow

# Generate SQL
sql = flow("llm://sql?prompt=get all active users&provider=ollama").run()
print(sql)

# Generate Streamware command
cmd = flow("llm://streamware?prompt=upload file to server&provider=ollama").run()
print(cmd)

# Analyze text
analysis = flow("llm://analyze?prompt=your text here&provider=ollama").run()
print(analysis)
```

### Helper Functions

```python
from streamware.components.llm import llm_to_sql, llm_to_streamware, llm_analyze

# SQL conversion
sql = llm_to_sql("find users created last week", provider="ollama")

# Streamware conversion
cmd = llm_to_streamware("backup database", provider="ollama")

# Text analysis
analysis = llm_analyze("Long text to analyze...", provider="ollama")
```

## 🔧 Configuration

### Environment Variables

```bash
# OpenAI
export OPENAI_API_KEY=sk-...
export LLM_PROVIDER=openai

# Anthropic
export ANTHROPIC_API_KEY=sk-ant-...
export LLM_PROVIDER=anthropic

# Ollama (local)
export OLLAMA_URL=http://localhost:11434
export LLM_PROVIDER=ollama
```

### Provider Comparison

| Provider | Cost | Speed | Quality | Local |
|----------|------|-------|---------|-------|
| **OpenAI** | 💰💰 | ⚡⚡⚡ | ⭐⭐⭐⭐⭐ | ❌ |
| **Anthropic** | 💰💰 | ⚡⚡ | ⭐⭐⭐⭐⭐ | ❌ |
| **Ollama** | 🆓 FREE | ⚡ | ⭐⭐⭐⭐ | ✅ |

**Rekomendacja:** Zaczn from Ollama (darmowe, lokalne), później przejdź na OpenAI jeśli potrzebujesz lepszej jakości.

## 📊 Supported DSL Conversions

### 1. SQL

**Input:** "Get all users who signed up last month"  
**Output:** `SELECT * FROM users WHERE created_at >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')`

### 2. Streamware (sq)

**Input:** "Upload file to production server"  
**Output:** `sq ssh prod.company.com --upload file.txt --remote /app/`

### 3. Bash

**Input:** "Monitor disk space and alert if above 90%"  
**Output:** 
```bash
while true; do
  usage=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')
  if [ $usage -gt 90 ]; then
    echo "Disk usage: ${usage}%" | mail -s "Disk Alert" admin@company.com
  fi
  sleep 300
done
```

### 4. Python

**Input:** "Parse JSON and extract emails"  
**Output:**
```python
import json
with open('data.json') as f:
    data = json.load(f)
emails = [item['email'] for item in data if 'email' in item]
```

## 🎓 Advanced Examples

### Multi-step Pipeline Generation

```bash
# Complex request
request="Create a pipeline that:
1. Fetches data from API every hour
2. Transforms to CSV
3. Uploads to FTP
4. Logs to database
5. Sends Slack notification"

# Generate complete solution
sq llm "$request" --to-bash --provider ollama > pipeline.sh

# Result: Complete bash script with cron job
```

### Intelligent Data Processing

```bash
#!/bin/bash
# smart-processor.sh

# User describes processing
echo "Describe data transformation:"
read description

# Generate processing script
script=$(sq llm "$description" --to-bash --provider ollama)

echo "Generated script:"
echo "$script"

# Execute with confirmation
read -p "Execute? (y/n) " confirm
[[ "$confirm" == "y" ]] && eval "$script"
```

### AI-Powered Debugging

```bash
# Analyze error logs
cat /var/log/app.log | sq llm --analyze --provider ollama > analysis.json

# Get suggested fixes
sq llm "Based on this error analysis, suggest fixes" \
    --input analysis.json \
    --provider ollama
```

## 🔐 Security Best Practices

### 1. API Key Management

```bash
# Store in .env file
echo "OPENAI_API_KEY=sk-..." > ~/.streamware_env
chmod 600 ~/.streamware_env

# Load in scripts
source ~/.streamware_env
```

### 2. Command Validation

```bash
# Always review before executing
cmd=$(sq llm "user input" --to-sq)
echo "Generated: $cmd"
read -p "Safe to execute? (y/n) " confirm
[[ "$confirm" == "y" ]] && eval "$cmd"
```

### 3. Rate Limiting

```bash
# Limit LLM calls
last_call_file="/tmp/llm_last_call"
if [ -f "$last_call_file" ]; then
    last_call=$(cat "$last_call_file")
    if [ $(($(date +%s) - last_call)) -lt 1 ]; then
        echo "Rate limit: wait 1 second"
        sleep 1
    fi
fi
date +%s > "$last_call_file"
```

## 🐛 Troubleshooting

### Error: "OPENAI_API_KEY not set"

```bash
export OPENAI_API_KEY=sk-your-key-here
# Or use Ollama instead:
sq llm "your prompt" --provider ollama
```

### Error: "Ollama not available"

```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Pull model
ollama pull llama3.2

# Test
ollama run llama3.2 "hello"
```

### Poor Quality Results

```bash
# Use better model
sq llm "your prompt" --model gpt-4o --provider openai

# Or be more specific in prompt
sq llm "Generate PostgreSQL query (not MySQL) to find users..." --to-sql
```

## 📚 More Resources

- **Examples:** `examples/llm_examples.py`
- **Component:** `streamware/components/llm.py`
- **Quick CLI:** `sq llm --help`

## 🎉 Quick Commands

```bash
# SQL generation
sq llm "your question" --to-sql

# Streamware command
sq llm "what you want" --to-sq

# Bash script
sq llm "automation task" --to-bash

# Analysis
sq llm --analyze --input file.txt

# Summarize
cat article.txt | sq llm --summarize

# Use Ollama (free!)
sq llm "prompt" --provider ollama
```

---

**Pro Tip:** Start with Ollama (free, local) for testing, then use OpenAI for production!

```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh
ollama pull llama3.2

# Test
sq llm "get all users" --to-sql --provider ollama
```

Happy AI-powered automation! 🤖✨
