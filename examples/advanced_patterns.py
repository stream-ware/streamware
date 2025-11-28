#!/usr/bin/env python3
"""
Advanced Streamware Pattern Examples

This file demonstrates advanced patterns and real-world usage scenarios
for the Streamware framework.
"""

from streamware import flow, Component, register
from streamware.patterns import SplitPattern, JoinPattern, FilterPattern
import json


def example_1_split_join_pattern():
    """
    Example 1: Split and Join pattern
    
    Demonstrates:
    - Splitting data into individual items
    - Processing each item independently
    - Joining results back together
    """
    print("\n=== Example 1: Split/Join Pattern ===")
    
    data = {
        "items": [
            {"id": 1, "value": 10},
            {"id": 2, "value": 20},
            {"id": 3, "value": 30}
        ]
    }
    
    # Split pattern
    splitter = SplitPattern()
    items = splitter.split(data["items"])
    print(f"Split items: {items}")
    
    # Process each item
    processed = [{"id": item["id"], "value": item["value"] * 2} for item in items]
    
    # Join pattern
    joiner = JoinPattern("list")
    result = joiner.join(processed)
    print(f"Joined result: {result}")


def example_2_filter_pattern():
    """
    Example 2: Filtering data streams
    
    Demonstrates:
    - Creating filter conditions
    - Applying filters to data
    - Chaining filters
    """
    print("\n=== Example 2: Filter Pattern ===")
    
    data = [
        {"name": "Alice", "age": 30, "active": True},
        {"name": "Bob", "age": 17, "active": False},
        {"name": "Charlie", "age": 25, "active": True},
        {"name": "David", "age": 15, "active": True}
    ]
    
    # Filter adults
    age_filter = FilterPattern(lambda x: x.get("age", 0) >= 18)
    adults = [item for item in data if age_filter.filter(item)]
    print(f"Adults: {adults}")
    
    # Filter active users
    active_filter = FilterPattern(lambda x: x.get("active", False))
    active_adults = [item for item in adults if active_filter.filter(item)]
    print(f"Active adults: {active_adults}")


def example_3_aggregate_pattern():
    """
    Example 3: Data aggregation
    
    Demonstrates:
    - Sum aggregation
    - Average calculation
    - Custom aggregation functions
    """
    print("\n=== Example 3: Aggregate Pattern ===")
    
    data = [10, 20, 30, 40, 50]
    
    # Sum
    joiner_sum = JoinPattern("sum")
    total = joiner_sum.join(data)
    print(f"Sum: {total}")
    
    # Average
    average = sum(data) / len(data)
    print(f"Average: {average}")
    
    # Min/Max
    print(f"Min: {min(data)}, Max: {max(data)}")


def example_4_parallel_processing():
    """
    Example 4: Parallel processing simulation
    
    Demonstrates:
    - Processing multiple items
    - Simulating parallel execution
    - Collecting results
    """
    print("\n=== Example 4: Parallel Processing ===")
    
    @register("multiply")
    class MultiplyComponent(Component):
        def process(self, data):
            factor = self.uri.get_param("factor", 2)
            if isinstance(data, (int, float)):
                return data * factor
            elif isinstance(data, dict) and "value" in data:
                return {**data, "value": data["value"] * factor}
            return data
    
    items = [
        {"id": 1, "value": 10},
        {"id": 2, "value": 20},
        {"id": 3, "value": 30}
    ]
    
    # Process each item
    results = []
    for item in items:
        result = flow("multiply://?factor=3").run(item)
        results.append(result)
    
    print(f"Processed items: {results}")


def example_5_error_recovery():
    """
    Example 5: Error handling and recovery
    
    Demonstrates:
    - Try/catch in pipelines
    - Fallback strategies
    - Error logging
    """
    print("\n=== Example 5: Error Recovery ===")
    
    @register("safe-divide")
    class SafeDivideComponent(Component):
        def process(self, data):
            try:
                numerator = data.get("numerator", 0)
                denominator = data.get("denominator", 1)
                
                if denominator == 0:
                    return {"error": "Division by zero", "result": None}
                
                return {"result": numerator / denominator}
            except Exception as e:
                return {"error": str(e), "result": None}
    
    test_cases = [
        {"numerator": 10, "denominator": 2},
        {"numerator": 10, "denominator": 0},
        {"numerator": 15, "denominator": 3}
    ]
    
    for case in test_cases:
        result = flow("safe-divide://").run(case)
        print(f"{case} -> {result}")


def example_6_data_enrichment():
    """
    Example 6: Data enrichment pipeline
    
    Demonstrates:
    - Adding metadata
    - Enriching with external data
    - Merging data sources
    """
    print("\n=== Example 6: Data Enrichment ===")
    
    @register("enrich")
    class EnrichComponent(Component):
        def process(self, data):
            # Simulate enrichment
            enriched = {**data}
            enriched["timestamp"] = "2024-01-01T00:00:00Z"
            enriched["enriched"] = True
            
            # Add computed fields
            if "price" in data:
                enriched["tax"] = data["price"] * 0.1
                enriched["total"] = data["price"] * 1.1
            
            return enriched
    
    products = [
        {"id": 1, "name": "Product A", "price": 100},
        {"id": 2, "name": "Product B", "price": 200}
    ]
    
    enriched_products = []
    for product in products:
        enriched = flow("enrich://").run(product)
        enriched_products.append(enriched)
    
    print(f"Enriched products: {json.dumps(enriched_products, indent=2)}")


def example_7_conditional_routing():
    """
    Example 7: Conditional routing
    
    Demonstrates:
    - Route based on data content
    - Dynamic pipeline selection
    - Multi-path processing
    """
    print("\n=== Example 7: Conditional Routing ===")
    
    @register("route")
    class RouteComponent(Component):
        def process(self, data):
            priority = data.get("priority", "normal")
            
            routes = {
                "high": "Processed with high priority",
                "normal": "Processed with normal priority",
                "low": "Processed with low priority"
            }
            
            data["route"] = routes.get(priority, "Unknown route")
            return data
    
    items = [
        {"id": 1, "priority": "high", "message": "Urgent"},
        {"id": 2, "priority": "normal", "message": "Regular"},
        {"id": 3, "priority": "low", "message": "Can wait"}
    ]
    
    for item in items:
        routed = flow("route://").run(item)
        print(f"{item['message']}: {routed['route']}")


def example_8_streaming_simulation():
    """
    Example 8: Streaming data simulation
    
    Demonstrates:
    - Generator-based processing
    - Stream transformations
    - Continuous data flow
    """
    print("\n=== Example 8: Streaming Simulation ===")
    
    def data_generator():
        """Simulate streaming data"""
        for i in range(5):
            yield {"sequence": i, "value": i * 10}
    
    @register("stream-process")
    class StreamProcessComponent(Component):
        def stream(self, input_stream):
            for item in input_stream:
                # Process each item
                processed = {
                    **item,
                    "processed": True,
                    "doubled": item.get("value", 0) * 2
                }
                yield processed
    
    # Simulate streaming
    print("Streaming data:")
    for item in data_generator():
        result = flow("stream-process://").run(item)
        print(f"  {result}")


def example_9_batch_processing():
    """
    Example 9: Batch processing
    
    Demonstrates:
    - Batching items
    - Batch transformations
    - Batch size control
    """
    print("\n=== Example 9: Batch Processing ===")
    
    def create_batches(items, batch_size=2):
        """Create batches from list"""
        for i in range(0, len(items), batch_size):
            yield items[i:i + batch_size]
    
    @register("batch-sum")
    class BatchSumComponent(Component):
        def process(self, data):
            if isinstance(data, list):
                total = sum(item.get("value", 0) for item in data)
                return {"batch_size": len(data), "total": total}
            return data
    
    items = [
        {"id": 1, "value": 10},
        {"id": 2, "value": 20},
        {"id": 3, "value": 30},
        {"id": 4, "value": 40},
        {"id": 5, "value": 50}
    ]
    
    print("Processing in batches:")
    for batch in create_batches(items, batch_size=2):
        result = flow("batch-sum://").run(batch)
        print(f"  Batch: {result}")


def example_10_pipeline_composition():
    """
    Example 10: Complex pipeline composition
    
    Demonstrates:
    - Multi-stage pipelines
    - Component reuse
    - Complex data flows
    """
    print("\n=== Example 10: Pipeline Composition ===")
    
    @register("validate")
    class ValidateComponent(Component):
        def process(self, data):
            data["validated"] = True
            data["valid"] = "name" in data and "email" in data
            return data
    
    @register("format")
    class FormatComponent(Component):
        def process(self, data):
            if data.get("valid"):
                data["formatted"] = f"{data['name']} <{data['email']}>"
            return data
    
    users = [
        {"name": "Alice", "email": "alice@example.com"},
        {"name": "Bob"},  # Missing email
        {"name": "Charlie", "email": "charlie@example.com"}
    ]
    
    print("Processing pipeline:")
    for user in users:
        # Multi-stage pipeline
        validated = flow("validate://").run(user)
        formatted = flow("format://").run(validated)
        
        status = "✓" if formatted.get("valid") else "✗"
        output = formatted.get("formatted", "Invalid user")
        print(f"  {status} {output}")


def main():
    """Run all advanced examples"""
    print("=" * 60)
    print("STREAMWARE ADVANCED PATTERN EXAMPLES")
    print("=" * 60)
    
    examples = [
        example_1_split_join_pattern,
        example_2_filter_pattern,
        example_3_aggregate_pattern,
        example_4_parallel_processing,
        example_5_error_recovery,
        example_6_data_enrichment,
        example_7_conditional_routing,
        example_8_streaming_simulation,
        example_9_batch_processing,
        example_10_pipeline_composition,
    ]
    
    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"\nError in {example.__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Advanced examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
