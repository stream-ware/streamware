#!/usr/bin/env python3
"""
Basic Streamware Usage Examples

This file demonstrates the fundamental concepts and basic usage patterns
of the Streamware framework.
"""

from streamware import flow, Flow


def example_1_simple_data_flow():
    """
    Example 1: Simple data transformation pipeline
    
    Demonstrates:
    - Creating a basic flow
    - Chaining transformations
    - Running the pipeline
    """
    print("\n=== Example 1: Simple Data Flow ===")
    
    # Create a simple data transformation
    data = {"name": "Alice", "age": 30, "city": "New York"}
    
    # Transform data through pipeline
    result = (
        flow("transform://json")
        .run(data)
    )
    
    print(f"Input: {data}")
    print(f"Output: {result}")


def example_2_file_operations():
    """
    Example 2: File read/write operations
    
    Demonstrates:
    - Writing data to files
    - Reading data from files
    - File path parameters
    """
    print("\n=== Example 2: File Operations ===")
    
    import tempfile
    import os
    
    # Create temporary file
    temp_dir = tempfile.gettempdir()
    temp_file = os.path.join(temp_dir, "streamware_example.txt")
    
    # Write to file
    write_result = (
        flow(f"file://write?path={temp_file}")
        .run("Hello from Streamware!")
    )
    print(f"Write result: {write_result}")
    
    # Read from file
    read_result = (
        flow(f"file://read?path={temp_file}")
        .run()
    )
    print(f"Read result: {read_result}")
    
    # Cleanup
    if os.path.exists(temp_file):
        os.remove(temp_file)
        print(f"Cleaned up: {temp_file}")


def example_3_data_transformation():
    """
    Example 3: Data transformation operations
    
    Demonstrates:
    - JSON transformations
    - CSV conversions
    - Base64 encoding/decoding
    """
    print("\n=== Example 3: Data Transformations ===")
    
    # JSON transformation
    json_data = {"users": ["Alice", "Bob", "Charlie"]}
    json_result = flow("transform://json").run(json_data)
    print(f"JSON: {json_result}")
    
    # CSV transformation
    csv_data = [
        {"name": "Alice", "age": 30},
        {"name": "Bob", "age": 25},
        {"name": "Charlie", "age": 35}
    ]
    csv_result = flow("transform://csv").run(csv_data)
    print(f"CSV:\n{csv_result}")
    
    # Base64 encoding
    text = "Hello Streamware"
    encoded = flow("transform://base64").run(text)
    print(f"Encoded: {encoded}")
    
    # Base64 decoding
    decoded = flow("transform://base64?decode=true").run(encoded)
    print(f"Decoded: {decoded}")


def example_4_pipeline_chaining():
    """
    Example 4: Chaining multiple operations
    
    Demonstrates:
    - Multiple pipeline steps
    - Data flow through components
    - Pipeline composition
    """
    print("\n=== Example 4: Pipeline Chaining ===")
    
    import tempfile
    import os
    
    temp_file = os.path.join(tempfile.gettempdir(), "pipeline_output.json")
    
    data = {
        "items": [
            {"name": "Item 1", "price": 100},
            {"name": "Item 2", "price": 200},
            {"name": "Item 3", "price": 150}
        ]
    }
    
    # Chain transformations
    result = (
        flow("transform://json")
        | f"file://write?path={temp_file}"
    ).run(data)
    
    print(f"Pipeline result: {result}")
    
    # Read back
    read_back = flow(f"file://read?path={temp_file}").run()
    print(f"Read back: {read_back}")
    
    # Cleanup
    if os.path.exists(temp_file):
        os.remove(temp_file)


def example_5_custom_component():
    """
    Example 5: Creating and using custom components
    
    Demonstrates:
    - Component registration
    - Custom processing logic
    - Integration with flows
    """
    print("\n=== Example 5: Custom Component ===")
    
    from streamware import Component, register
    
    @register("uppercase")
    class UppercaseComponent(Component):
        """Simple component that converts text to uppercase"""
        
        def process(self, data):
            if isinstance(data, str):
                return data.upper()
            elif isinstance(data, dict):
                return {k: v.upper() if isinstance(v, str) else v 
                       for k, v in data.items()}
            return data
    
    # Use custom component
    result1 = flow("uppercase://").run("hello world")
    print(f"Uppercase text: {result1}")
    
    result2 = flow("uppercase://").run({"message": "hello", "status": "active"})
    print(f"Uppercase dict: {result2}")


def example_6_with_data_method():
    """
    Example 6: Using with_data() method
    
    Demonstrates:
    - Passing data with with_data()
    - Alternative to run() parameter
    - Method chaining
    """
    print("\n=== Example 6: with_data() Method ===")
    
    data = {"value": 42, "name": "test"}
    
    result = (
        flow("transform://json")
        .with_data(data)
        .run()
    )
    
    print(f"Result: {result}")


def example_7_error_handling():
    """
    Example 7: Error handling in pipelines
    
    Demonstrates:
    - Try/catch with flows
    - Error messages
    - Graceful degradation
    """
    print("\n=== Example 7: Error Handling ===")
    
    try:
        # Try to read non-existent file
        result = flow("file://read?path=/nonexistent/file.txt").run()
        print(f"Result: {result}")
    except Exception as e:
        print(f"Caught error: {type(e).__name__}: {e}")
    
    # Graceful handling
    try:
        result = flow("transform://json").run("invalid json {")
    except Exception as e:
        print(f"JSON parse error: {e}")


def example_8_conditional_logic():
    """
    Example 8: Conditional processing
    
    Demonstrates:
    - Conditional execution
    - Dynamic pipeline construction
    - Flow control
    """
    print("\n=== Example 8: Conditional Logic ===")
    
    def process_data(data, use_uppercase=False):
        from streamware import Component, register
        
        # Register uppercase if needed
        if use_uppercase and "uppercase" not in dir():
            @register("uppercase")
            class UppercaseComponent(Component):
                def process(self, data):
                    return data.upper() if isinstance(data, str) else data
        
        if use_uppercase:
            return flow("uppercase://").run(data)
        else:
            return flow("transform://json").run(data)
    
    result1 = process_data("hello", use_uppercase=True)
    print(f"With uppercase: {result1}")
    
    result2 = process_data({"msg": "hello"}, use_uppercase=False)
    print(f"Without uppercase: {result2}")


def main():
    """Run all examples"""
    print("=" * 60)
    print("STREAMWARE BASIC USAGE EXAMPLES")
    print("=" * 60)
    
    examples = [
        example_1_simple_data_flow,
        example_2_file_operations,
        example_3_data_transformation,
        example_4_pipeline_chaining,
        example_5_custom_component,
        example_6_with_data_method,
        example_7_error_handling,
        example_8_conditional_logic,
    ]
    
    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"\nError in {example.__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
