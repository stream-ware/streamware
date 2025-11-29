#!/usr/bin/env python3
"""
LLM Component Examples - AI-powered DSL Conversion

Demonstrates natural language to DSL conversion using LLM.

Provider format (LiteLLM compatible):
    provider="openai/gpt-4o"
    provider="ollama/qwen2.5:14b"
    provider="anthropic/claude-3-5-sonnet-20240620"
    provider="gemini/gemini-2.0-flash"
    provider="groq/llama3-70b-8192"
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamware import flow
from streamware.components.llm import llm_generate, llm_to_sql, llm_to_streamware, llm_analyze


def example_1_text_to_sql():
    """Example 1: Natural Language to SQL"""
    print("\n=== Example 1: Natural Language → SQL ===")
    
    examples = [
        "Get all users older than 30",
        "Find active orders from last week",
        "Count how many products are in stock",
        "Show top 10 customers by total purchase amount",
        "Delete users who haven't logged in for 6 months",
    ]
    
    for nl in examples:
        print(f"\nNatural Language: {nl}")
        
        # Convert to SQL using LiteLLM-style provider format
        sql = llm_to_sql(nl, provider="ollama/qwen2.5:14b")  # Use free local Ollama
        print(f"Generated SQL: {sql}")


def example_2_text_to_streamware():
    """Example 2: Natural Language to Streamware Commands"""
    print("\n=== Example 2: Natural Language → Streamware Commands ===")
    
    examples = [
        "upload file to SSH server",
        "get users from API and save to database",
        "send email with attachment",
        "download data from FTP and convert to CSV",
        "monitor server health and alert on Slack",
    ]
    
    for nl in examples:
        print(f"\nRequest: {nl}")
        
        # Convert to Streamware command
        cmd = llm_to_streamware(nl, provider="ollama/llama3.2")
        print(f"Command: {cmd}")


def example_3_analyze_text():
    """Example 3: Text Analysis"""
    print("\n=== Example 3: Text Analysis ===")
    
    text = """
    Streamware is a modern Python framework for stream processing.
    It provides a simple, intuitive API for building data pipelines,
    integrating with various services like Kafka, PostgreSQL, and SSH.
    The framework is designed to be extensible and easy to use.
    """
    
    print(f"Text: {text}")
    
    # Analyze
    analysis = llm_analyze(text, provider="ollama/llama3.2")
    print(f"\nAnalysis:")
    import json
    print(json.dumps(analysis, indent=2))


def example_4_quick_cli():
    """Example 4: Using Quick CLI"""
    print("\n=== Example 4: Quick CLI Examples ===")
    
    print("""
    # Convert natural language to SQL
    sq llm "get all active users" --to-sql
    
    # Convert to Streamware command
    sq llm "upload file to prod server" --to-sq
    
    # Convert and execute
    sq llm "get all users from database" --to-sql --execute
    
    # Analyze text from file
    sq llm --analyze --input document.txt
    
    # Summarize
    echo "long text..." | sq llm --summarize
    
    # Use different providers (LiteLLM format)
    sq llm "generate SQL" --to-sql --provider ollama/qwen2.5:14b
    sq llm "generate SQL" --to-sql --provider openai/gpt-4o
    sq llm "generate SQL" --to-sql --provider groq/llama3-70b-8192
    """)


def example_5_pipeline_generation():
    """Example 5: Generate Complete Pipelines"""
    print("\n=== Example 5: Pipeline Generation ===")
    
    request = """
    Create a pipeline that:
    1. Fetches user data from API
    2. Filters active users
    3. Saves to PostgreSQL
    4. Sends notification to Slack
    """
    
    print(f"Request:\n{request}")
    
    # Generate pipeline with LiteLLM-style provider
    pipeline = flow("llm://generate?prompt=" + request + "&provider=ollama/qwen2.5:14b").run()
    print(f"\nGenerated Pipeline:\n{pipeline}")


def example_6_sql_query_builder():
    """Example 6: Interactive SQL Query Builder"""
    print("\n=== Example 6: SQL Query Builder ===")
    
    print("""
    # Interactive SQL builder service
    
    while true; do
        read -p "What data do you need? " question
        
        # Generate SQL
        sql=$(sq llm "$question" --to-sql --provider ollama)
        echo "SQL: $sql"
        
        # Confirm execution
        read -p "Execute? (y/n) " confirm
        if [[ "$confirm" == "y" ]]; then
            sq postgres "$sql" --json
        fi
    done
    """)


def example_7_automation_assistant():
    """Example 7: Automation Assistant"""
    print("\n=== Example 7: Automation Assistant ===")
    
    print("""
    # AI Assistant for automation
    
    # User request
    request="Backup database to FTP server every day at midnight"
    
    # Generate cron job
    sq llm "$request" --to-bash --provider ollama
    
    # Output example:
    # 0 0 * * * sq postgres "COPY data TO STDOUT" | gzip | curl -T - ftp://backup.com/
    
    # Or generate complete script:
    sq llm "Create a bash script that monitors disk space and sends alerts" --to-bash
    """)


def example_8_data_migration():
    """Example 8: Data Migration Helper"""
    print("\n=== Example 8: Data Migration Helper ===")
    
    print("""
    # Migration assistant
    
    # Describe migration
    task="Migrate users table from MySQL to PostgreSQL"
    
    # Generate migration commands
    sq llm "$task" --to-bash --provider ollama
    
    # Example output:
    # mysqldump -u user -p database users | 
    # sed 's/AUTO_INCREMENT/SERIAL/g' |
    # psql -U user -d newdb
    
    # Or get SQL conversion:
    sq llm "Convert MySQL syntax to PostgreSQL: 
      CREATE TABLE users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100)
      )" --to-sql
    """)


def example_9_monitoring_setup():
    """Example 9: Monitoring Setup Generator"""
    print("\n=== Example 9: Monitoring Setup ===")
    
    monitoring_request = "Monitor API health, check every minute, alert if down"
    
    print(f"Request: {monitoring_request}")
    
    # Generate monitoring script
    script = flow("llm://convert?to=bash&prompt=" + monitoring_request + "&provider=ollama/llama3.2").run()
    print(f"\nGenerated Script:\n{script}")


def example_10_email_automation():
    """Example 10: Email Automation"""
    print("\n=== Example 10: Email Automation ===")
    
    print("""
    # Email automation with LLM
    
    # Process emails with AI
    while true; do
        # Get new emails
        emails=$(sq email imap.gmail.com --user user@example.com --unread --json)
        
        # Analyze each email
        for email in $emails; do
            # Extract intent
            intent=$(echo "$email" | sq llm --analyze --provider ollama | jq -r '.intent')
            
            # Generate appropriate action
            case $intent in
                "deployment_request")
                    # Generate deployment command
                    cmd=$(echo "$email" | sq llm --to-sq --provider ollama)
                    echo "Executing: $cmd"
                    eval "$cmd"
                    ;;
                "data_request")
                    # Generate SQL query
                    sql=$(echo "$email" | sq llm --to-sql --provider ollama)
                    sq postgres "$sql" --csv | sq email --reply
                    ;;
                "support_ticket")
                    # Forward to support
                    sq slack support --message "New ticket: $email"
                    ;;
            esac
        done
        
        sleep 60
    done
    """)


def main():
    """Run all examples"""
    print("=" * 60)
    print("STREAMWARE LLM COMPONENT EXAMPLES")
    print("AI-Powered DSL Conversion")
    print("=" * 60)
    
    examples = [
        example_1_text_to_sql,
        example_2_text_to_streamware,
        example_3_analyze_text,
        example_4_quick_cli,
        example_5_pipeline_generation,
        example_6_sql_query_builder,
        example_7_automation_assistant,
        example_8_data_migration,
        example_9_monitoring_setup,
        example_10_email_automation,
    ]
    
    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"\nNote: {example.__name__} - {e}")
            print("(Some examples show shell scripts, not Python execution)")
            print("(LLM features require API keys or local Ollama)")
    
    print("\n" + "=" * 60)
    print("LLM Examples completed!")
    print("=" * 60)
    print("\n📚 Quick Reference:")
    print("  sq llm 'natural language' --to-sql")
    print("  sq llm 'natural language' --to-sq")
    print("  sq llm 'text' --analyze")
    print("  sq llm 'text' --summarize")
    print("\n🔑 Setup:")
    print("  # Provider format: provider/model")
    print("  export LLM_PROVIDER=openai/gpt-4o")
    print("  export OPENAI_API_KEY=your_key")
    print("  # Or use local Ollama (free):")
    print("  export LLM_PROVIDER=ollama/qwen2.5:14b")
    print("  ollama pull qwen2.5:14b")


if __name__ == "__main__":
    main()
