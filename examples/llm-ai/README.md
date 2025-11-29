# LLM & AI Examples

AI-powered text processing, code generation, and natural language conversion.

## 📁 Examples

| File | Description |
|------|-------------|
| [text_to_sql.py](text_to_sql.py) | Convert natural language to SQL queries |
| [text_to_code.py](text_to_code.py) | Generate code from descriptions |
| [chat_assistant.py](chat_assistant.py) | Interactive AI chat assistant |
| [document_analyzer.py](document_analyzer.py) | Analyze and summarize documents |
| [multi_provider.py](multi_provider.py) | Use multiple LLM providers |

## 🚀 Quick Start

```bash
# Using sq CLI
sq llm "Write hello world in Python" --provider ollama/qwen2.5:14b

# Convert to SQL
sq llm "Get all users older than 30" --to-sql --provider openai/gpt-4o

# Analyze text
sq llm --analyze --input document.txt --provider groq/llama3-70b-8192
```

## 🔧 Configuration

```bash
# Set default provider
export LLM_PROVIDER=openai/gpt-4o

# API keys (auto-detected)
export OPENAI_API_KEY=sk-...
export GROQ_API_KEY=gsk_...
export GEMINI_API_KEY=...
```

## 📚 Related Documentation

- [LLM Component](../../docs/v2/components/LLM_COMPONENT.md)
- [Quick CLI](../../docs/v2/components/QUICK_CLI.md)
- [DSL Examples](../../docs/v2/components/DSL_EXAMPLES.md)

## 🔗 Related Examples

- [Data Pipelines](../data-pipelines/) - ETL with AI
- [Automation](../automation/) - AI-powered automation
