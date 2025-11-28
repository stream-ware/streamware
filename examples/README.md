# Streamware Examples

This directory contains example scripts demonstrating various features and usage patterns of the Streamware framework.

## Available Examples

### 1. Basic Usage (`basic_usage.py`)

Fundamental concepts and basic usage patterns:

- **Example 1**: Simple data flow
- **Example 2**: File operations (read/write)
- **Example 3**: Data transformations (JSON, CSV, Base64)
- **Example 4**: Pipeline chaining
- **Example 5**: Custom components
- **Example 6**: Using `with_data()` method
- **Example 7**: Error handling
- **Example 8**: Conditional logic

**Run it:**
```bash
python examples/basic_usage.py
```

### 2. Advanced Patterns (`advanced_patterns.py`)

Advanced workflow patterns and real-world scenarios:

- **Example 1**: Split/Join pattern
- **Example 2**: Filter pattern
- **Example 3**: Aggregation
- **Example 4**: Parallel processing
- **Example 5**: Error recovery
- **Example 6**: Data enrichment
- **Example 7**: Conditional routing
- **Example 8**: Streaming simulation
- **Example 9**: Batch processing
- **Example 10**: Pipeline composition

**Run it:**
```bash
python examples/advanced_patterns.py
```

### 3. Communication Examples (`examples_communication.py`)

Communication component examples (in root directory):

- Email integration (send, receive, watch)
- Telegram bots and messaging
- WhatsApp integration
- Discord bots and webhooks
- Slack integration
- SMS messaging

**Run it:**
```bash
python examples_communication.py
```

### 4. Advanced Communication (`examples_advanced_communication.py`)

Production-ready communication patterns (in root directory):

- Multi-channel notifications
- Customer support systems
- Marketing automation
- Incident response
- Monitoring and alerting

**Run it:**
```bash
python examples_advanced_communication.py
```

## Quick Start

### Run All Basic Examples

```bash
cd /path/to/streamware
python examples/basic_usage.py
```

### Run Specific Examples

You can modify the example files to run specific examples:

```python
# In basic_usage.py, modify main() to run specific examples
if __name__ == "__main__":
    example_1_simple_data_flow()
    example_2_file_operations()
    # ... run only what you need
```

## Example Output

When you run the examples, you'll see output like:

```
============================================================
STREAMWARE BASIC USAGE EXAMPLES
============================================================

=== Example 1: Simple Data Flow ===
Input: {'name': 'Alice', 'age': 30, 'city': 'New York'}
Output: {"name": "Alice", "age": 30, "city": "New York"}

=== Example 2: File Operations ===
Write result: {'success': True, 'path': '/tmp/streamware_example.txt'}
Read result: Hello from Streamware!
Cleaned up: /tmp/streamware_example.txt

...
```

## Creating Your Own Examples

You can create custom examples by following these patterns:

```python
#!/usr/bin/env python3
"""
My Custom Streamware Example
"""

from streamware import flow, Component, register

def my_example():
    """
    Description of what this example demonstrates
    """
    print("\n=== My Example ===")
    
    # Your code here
    result = flow("component://operation").run(data)
    print(f"Result: {result}")

if __name__ == "__main__":
    my_example()
```

## Testing Examples

All examples are designed to be runnable without external dependencies (where possible). Some examples that require external services will skip or simulate operations.

To test examples:

```bash
# Run basic examples
python examples/basic_usage.py

# Run advanced examples
python examples/advanced_patterns.py

# Run with pytest (if you have tests for examples)
pytest examples/test_examples.py -v
```

## Common Patterns

### Pattern 1: Simple Pipeline

```python
result = (
    flow("source://data")
    | "transform://process"
    | "sink://destination"
).run()
```

### Pattern 2: With Error Handling

```python
try:
    result = flow("risky://operation").run(data)
except ComponentError as e:
    print(f"Error: {e}")
    result = None
```

### Pattern 3: Custom Component

```python
@register("mycomp")
class MyComponent(Component):
    def process(self, data):
        return transform(data)

result = flow("mycomp://operation").run(data)
```

### Pattern 4: Streaming

```python
for item in flow("source://stream").stream():
    processed = process(item)
    save(processed)
```

## Best Practices

1. **Start Simple**: Begin with basic examples before moving to advanced patterns
2. **Experiment**: Modify examples to understand how components work
3. **Error Handling**: Always include error handling in production code
4. **Testing**: Test your pipelines thoroughly
5. **Documentation**: Document your custom components and pipelines

## Troubleshooting

### Import Errors

If you get import errors, make sure streamware is installed:

```bash
pip install -e .
```

### Missing Dependencies

Some examples require optional dependencies:

```bash
# For communication examples
pip install streamware[communication]

# For all features
pip install streamware[all]
```

### File Permissions

Some examples write to `/tmp/`. If you encounter permission issues, modify the examples to use a different directory:

```python
import tempfile
temp_dir = tempfile.gettempdir()
temp_file = os.path.join(temp_dir, "output.txt")
```

## Contributing Examples

We welcome contributions of new examples! Please:

1. Follow the existing example structure
2. Include clear documentation
3. Test your examples
4. Submit a pull request

## Support

- 📚 Full Documentation: [docs/USAGE_GUIDE.md](../docs/USAGE_GUIDE.md)
- 🐛 Report Issues: [GitHub Issues](https://github.com/softreck/streamware/issues)
- 💬 Ask Questions: [GitHub Discussions](https://github.com/softreck/streamware/discussions)

---

Happy streaming with Streamware! 🚀
