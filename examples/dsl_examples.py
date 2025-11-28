#!/usr/bin/env python3
"""
Streamware DSL Examples - Simplified API Usage

Demonstrates different DSL styles for creating pipelines.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamware import Pipeline, pipeline, quick, PipelineBuilder, compose, as_component
from streamware import read_file, save_file, to_json, to_csv
import tempfile


def example_1_fluent_api():
    """
    Example 1: Fluent API - Method Chaining
    
    Najbardziej Pythonowy i czytelny styl
    """
    print("\n=== Example 1: Fluent API ===")
    
    # Prosty przykład
    temp_file = os.path.join(tempfile.gettempdir(), "fluent_output.json")
    
    data = {"users": [
        {"name": "Alice", "age": 30},
        {"name": "Bob", "age": 17},
        {"name": "Charlie", "age": 25}
    ]}
    
    # Zbuduj i wykonaj pipeline
    result = (
        Pipeline()
        .read_file(temp_file) if os.path.exists(temp_file) else
        Pipeline()  # Dummy start
    )
    
    # Zapisz test data
    import json
    with open(temp_file, 'w') as f:
        json.dump(data, f)
    
    # Process with fluent API
    result = (
        Pipeline()
        .read_file(temp_file)
        .to_json()
        .filter(lambda x: x.get('age', 0) > 18)  # Only adults
    )
    
    processed = result.run()
    print(f"Filtered adults: {processed}")
    
    # Cleanup
    if os.path.exists(temp_file):
        os.remove(temp_file)


def example_2_context_manager():
    """
    Example 2: Context Manager
    
    Dla operacji krok-po-kroku
    """
    print("\n=== Example 2: Context Manager ===")
    
    temp_input = os.path.join(tempfile.gettempdir(), "context_input.json")
    temp_output = os.path.join(tempfile.gettempdir(), "context_output.json")
    
    # Przygotuj dane
    import json
    test_data = {"message": "Hello from context manager", "count": 42}
    with open(temp_input, 'w') as f:
        json.dump(test_data, f)
    
    # Użyj context manager
    with pipeline() as p:
        # Czytaj
        data = p.read(temp_input)
        print(f"Read data: {data}")
        
        # Transform
        json_data = p.transform(data, "json")
        print(f"Transformed: {json_data}")
        
        # Zapisz
        p.save(json_data, temp_output)
        print(f"Saved to: {temp_output}")
    
    # Cleanup
    for f in [temp_input, temp_output]:
        if os.path.exists(f):
            os.remove(f)


def example_3_quick_shortcuts():
    """
    Example 3: Quick Shortcuts
    
    Dla szybkich, jednolinijkowych operacji
    """
    print("\n=== Example 3: Quick Shortcuts ===")
    
    temp_file = os.path.join(tempfile.gettempdir(), "quick_test.json")
    
    # Przygotuj dane
    import json
    with open(temp_file, 'w') as f:
        json.dump({"quick": "test", "value": 123}, f)
    
    # Quick operation - jedna linijka!
    try:
        result = quick(f"file://read?path={temp_file}").json().run()
        print(f"Quick result: {result}")
    except Exception as e:
        print(f"Quick operation: {e}")
    
    # Cleanup
    if os.path.exists(temp_file):
        os.remove(temp_file)


def example_4_function_composition():
    """
    Example 4: Function Composition
    
    Funkcyjny styl programowania
    """
    print("\n=== Example 4: Function Composition ===")
    
    # Custom transform functions
    def double_values(data):
        """Double all numeric values"""
        if isinstance(data, dict):
            return {k: v*2 if isinstance(v, (int, float)) else v 
                   for k, v in data.items()}
        return data
    
    def add_timestamp(data):
        """Add timestamp to data"""
        from datetime import datetime
        if isinstance(data, dict):
            data['timestamp'] = datetime.now().isoformat()
        return data
    
    # Test data
    test_data = {"value": 10, "count": 5}
    
    # Compose functions
    process = compose(
        lambda: test_data,  # Source
        double_values,      # Transform 1
        add_timestamp,      # Transform 2
    )
    
    result = process()
    print(f"Composed result: {result}")


def example_5_builder_pattern():
    """
    Example 5: Builder Pattern
    
    Dla czytelnych, złożonych pipeline'ów
    """
    print("\n=== Example 5: Builder Pattern ===")
    
    temp_input = os.path.join(tempfile.gettempdir(), "builder_input.json")
    temp_output = os.path.join(tempfile.gettempdir(), "builder_output.csv")
    
    # Przygotuj dane
    import json
    data = {
        "users": [
            {"name": "Alice", "age": 30, "active": True},
            {"name": "Bob", "age": 25, "active": False},
            {"name": "Charlie", "age": 35, "active": True}
        ]
    }
    with open(temp_input, 'w') as f:
        json.dump(data, f)
    
    try:
        # Build pipeline with builder pattern
        result = (
            PipelineBuilder()
            .source_file(temp_input)
            .transform_json()
            .sink_file(temp_output)
            .execute()
        )
        
        print(f"Builder result: {result}")
        
        # Verify output
        if os.path.exists(temp_output):
            print(f"Output file created: {temp_output}")
    except Exception as e:
        print(f"Builder example: {e}")
    
    # Cleanup
    for f in [temp_input, temp_output]:
        if os.path.exists(f):
            os.remove(f)


def example_6_decorators():
    """
    Example 6: Decorators
    
    Dla reużywalnych komponentów
    """
    print("\n=== Example 6: Decorators ===")
    
    # Register custom component
    @as_component("multiply")
    def multiply_by_two(data):
        """Multiply numeric values by 2"""
        if isinstance(data, (int, float)):
            return data * 2
        elif isinstance(data, dict):
            return {k: v*2 if isinstance(v, (int, float)) else v 
                   for k, v in data.items()}
        return data
    
    # Use it in pipeline
    from streamware import flow
    
    result = flow("multiply://").run(5)
    print(f"Multiply result: {result}")
    
    result2 = flow("multiply://").run({"value": 10, "count": 3})
    print(f"Multiply dict: {result2}")


def example_7_comparison():
    """
    Example 7: Comparison of All Styles
    
    To samo zadanie wykonane różnymi stylami
    """
    print("\n=== Example 7: Style Comparison ===")
    
    temp_file = os.path.join(tempfile.gettempdir(), "comparison.json")
    
    # Test data
    import json
    data = [
        {"name": "Alice", "age": 30},
        {"name": "Bob", "age": 17},
        {"name": "Charlie", "age": 25}
    ]
    with open(temp_file, 'w') as f:
        json.dump(data, f)
    
    print("\n--- Original DSL ---")
    from streamware import flow
    try:
        result = flow(f"file://read?path={temp_file}").run()
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n--- Fluent API ---")
    try:
        result = (
            Pipeline()
            .read_file(temp_file)
            .to_json()
            .run()
        )
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n--- Context Manager ---")
    try:
        with pipeline() as p:
            data = p.read(temp_file)
            result = p.transform(data, "json")
            print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Cleanup
    if os.path.exists(temp_file):
        os.remove(temp_file)


def example_8_real_world():
    """
    Example 8: Real-World Use Case
    
    Praktyczny przykład: ETL pipeline
    """
    print("\n=== Example 8: Real-World ETL ===")
    
    temp_input = os.path.join(tempfile.gettempdir(), "raw_data.json")
    temp_output = os.path.join(tempfile.gettempdir(), "processed_data.csv")
    
    # Simulate raw data
    import json
    raw_data = [
        {"id": 1, "name": "Product A", "price": 100, "status": "active"},
        {"id": 2, "name": "Product B", "price": 200, "status": "inactive"},
        {"id": 3, "name": "Product C", "price": 150, "status": "active"},
        {"id": 4, "name": "Product D", "price": 50, "status": "active"}
    ]
    with open(temp_input, 'w') as f:
        json.dump(raw_data, f)
    
    print(f"Processing {len(raw_data)} records...")
    
    # ETL with Fluent API
    try:
        result = (
            Pipeline()
            .read_file(temp_input)
            .to_json()
            .filter(lambda x: x['status'] == 'active')  # Extract
            .filter(lambda x: x['price'] >= 100)         # Transform
            .to_csv()                                     # Load
            .save(temp_output)
            .run()
        )
        
        print(f"Processed successfully!")
        print(f"Output: {temp_output}")
        
        # Show results
        if os.path.exists(temp_output):
            with open(temp_output, 'r') as f:
                print(f"CSV output:\n{f.read()}")
    except Exception as e:
        print(f"ETL error: {e}")
        import traceback
        traceback.print_exc()
    
    # Cleanup
    for f in [temp_input, temp_output]:
        if os.path.exists(f):
            os.remove(f)


def main():
    """Run all DSL examples"""
    print("=" * 60)
    print("STREAMWARE SIMPLIFIED DSL EXAMPLES")
    print("=" * 60)
    
    examples = [
        example_1_fluent_api,
        example_2_context_manager,
        example_3_quick_shortcuts,
        example_4_function_composition,
        example_5_builder_pattern,
        example_6_decorators,
        example_7_comparison,
        example_8_real_world,
    ]
    
    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"\nError in {example.__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("DSL Examples completed!")
    print("=" * 60)
    
    print("\n📚 Documentation: docs/DSL_EXAMPLES.md")
    print("💡 Wybierz styl, który Ci najbardziej odpowiada!")


if __name__ == "__main__":
    main()
