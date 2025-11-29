#!/usr/bin/env python3
"""
Text to SQL - Convert natural language to SQL queries

Examples:
    python text_to_sql.py "Get all users older than 30"
    python text_to_sql.py "Find orders from last week" --provider groq/llama3-70b-8192
    
Related:
    - docs/v2/components/LLM_COMPONENT.md
    - examples/data-pipelines/etl_with_ai.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from streamware import flow
from streamware.components.llm import llm_to_sql


def main():
    # Example queries
    queries = [
        "Get all users older than 30",
        "Find active orders from last week",
        "Count products by category",
        "Show top 10 customers by total purchases",
        "Delete inactive users from last year",
    ]
    
    provider = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == "--provider" else "ollama/qwen2.5:14b"
    
    if len(sys.argv) > 1 and sys.argv[1] != "--provider":
        # Single query from command line
        query = sys.argv[1]
        print(f"Query: {query}")
        sql = llm_to_sql(query, provider=provider)
        print(f"SQL: {sql}")
    else:
        # Demo all examples
        print("=" * 60)
        print("TEXT TO SQL CONVERTER")
        print(f"Provider: {provider}")
        print("=" * 60)
        
        for query in queries:
            print(f"\n📝 Query: {query}")
            try:
                sql = llm_to_sql(query, provider=provider)
                print(f"💾 SQL: {sql}")
            except Exception as e:
                print(f"❌ Error: {e}")
        
        print("\n" + "=" * 60)
        print("Usage: python text_to_sql.py 'your query' [--provider provider/model]")


if __name__ == "__main__":
    main()
