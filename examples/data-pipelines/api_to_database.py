#!/usr/bin/env python3
"""
API to Database Pipeline

Fetches data from API, transforms it, and saves to PostgreSQL.

Related:
    - docs/v2/components/DSL_EXAMPLES.md
    - streamware/components/http.py
    - streamware/components/postgres.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from streamware import flow


def api_to_db(api_url: str, table: str, transform: str = None):
    """
    Fetch from API and save to database
    
    Args:
        api_url: API endpoint
        table: Target database table
        transform: Optional JSONPath transform
    """
    print(f"📥 Fetching from: {api_url}")
    
    # Build pipeline
    if transform:
        pipeline = (
            flow(f"https://{api_url}")
            .pipe(f"transform://jsonpath?query={transform}")
            .pipe(f"postgres://insert?table={table}")
        )
    else:
        pipeline = (
            flow(f"https://{api_url}")
            .pipe(f"postgres://insert?table={table}")
        )
    
    result = pipeline.run()
    print(f"✅ Saved to table: {table}")
    return result


def demo():
    print("=" * 60)
    print("API TO DATABASE PIPELINE")
    print("=" * 60)
    
    print("\n📋 Pipeline examples:")
    
    examples = [
        # Simple fetch and save
        ("sq get api.example.com/users | sq postgres --insert users",
         "Fetch users and insert to DB"),
        
        # With transform
        ("sq get api.example.com/data | sq transform --jsonpath '$.items[*]' | sq postgres --insert items",
         "Transform JSON then insert"),
        
        # With filter
        ("sq get api.example.com/orders | sq filter --jq '.[] | select(.status==\"active\")' | sq postgres --insert active_orders",
         "Filter then insert"),
    ]
    
    for cmd, desc in examples:
        print(f"\n{desc}:")
        print(f"   {cmd}")
    
    print("\n🔧 Setup:")
    print("   export POSTGRES_URL=postgresql://user:pass@host/db")
    
    print("\n📚 Python usage:")
    print("""
    from streamware import flow
    
    result = (
        flow("https://api.example.com/users")
        .pipe("transform://jsonpath?query=$.data[*]")
        .pipe("postgres://insert?table=users")
    ).run()
    """)


if __name__ == "__main__":
    demo()
