# Streamware Usage Guide

Complete guide for using the Streamware framework for stream processing and data pipelines.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Core Concepts](#core-concepts)
3. [Basic Usage](#basic-usage)
4. [Advanced Patterns](#advanced-patterns)
5. [Component Reference](#component-reference)
6. [Testing](#testing)
7. [Best Practices](#best-practices)

## Getting Started

### Installation

```bash
# Basic installation
pip install streamware

# With all features
pip install streamware[all]

# Specific features
pip install streamware[kafka,rabbitmq,postgres]
```

### Quick Example

```python
from streamware import flow

# Simple pipeline
result = (
    flow("http://api.example.com/data")
    | "transform://json"
    | "file://write?path=output.json"
).run()
```

## Core Concepts

### Flows

A `Flow` is the fundamental building block in Streamware. It represents a series of processing steps that data passes through.

```python
from streamware import flow

# Create a flow
my_flow = flow("file://read?path=input.txt")

# Chain operations
my_flow = my_flow | "transform://uppercase" | "file://write?path=output.txt"

# Execute
result = my_flow.run()
```

### Components

Components are the processing units in a flow. Each component:
- Has a unique scheme (e.g., `file`, `http`, `transform`)
- Accepts input data
- Produces output data
- Can be chained together

```python
from streamware import Component, register

@register("mycomponent")
class MyComponent(Component):
    def process(self, data):
        # Your processing logic
        return processed_data
```

### URI Format

Streamware uses URI-style syntax for component configuration:

```
scheme://operation?param1=value1&param2=value2
```

Examples:
```python
"file://read?path=/tmp/data.json"
"http://api.example.com/users?method=post"
"transform://csv?delimiter=;"
"kafka://consume?topic=events&group=processor"
```

## Basic Usage

### File Operations

#### Read File
```python
# Read text file
content = flow("file://read?path=/tmp/input.txt").run()

# Read JSON file
data = flow("file://read?path=/tmp/data.json").run()
```

#### Write File
```python
# Write text
flow("file://write?path=/tmp/output.txt").run("Hello World")

# Write JSON
flow("file://write?path=/tmp/data.json").run({"key": "value"})

# Append mode
flow("file://write?path=/tmp/log.txt&mode=append").run("Log entry\n")
```

### Data Transformations

#### JSON Operations
```python
# Parse JSON string
data = flow("transform://json").run('{"name":"Alice"}')

# Convert to JSON string
json_str = flow("transform://json").run({"name": "Alice"})
```

#### CSV Operations
```python
# Convert list of dicts to CSV
csv_data = flow("transform://csv").run([
    {"name": "Alice", "age": 30},
    {"name": "Bob", "age": 25}
])

# Custom delimiter
csv_data = flow("transform://csv?delimiter=;").run(data)
```

#### Base64 Encoding
```python
# Encode
encoded = flow("transform://base64").run("Hello World")

# Decode
decoded = flow("transform://base64?decode=true").run(encoded)
```

### HTTP Requests

#### GET Request
```python
# Simple GET
response = flow("http://api.example.com/data").run()

# With parameters
response = flow("http://api.example.com/users?limit=10").run()
```

#### POST Request
```python
# POST with JSON body
response = flow("http://api.example.com/users?method=post").run({
    "name": "Alice",
    "email": "alice@example.com"
})
```

### Pipeline Chaining

```python
# Multi-step pipeline
result = (
    flow("http://api.example.com/data")
    | "transform://jsonpath?query=$.items[*]"
    | "transform://csv"
    | "file://write?path=output.csv"
).run()
```

## Advanced Patterns

### Split/Join Pattern

Process array items individually and collect results:

```python
from streamware.patterns import SplitPattern, JoinPattern

# Split data
splitter = SplitPattern()
items = splitter.split([1, 2, 3, 4, 5])

# Process each item
processed = [item * 2 for item in items]

# Join results
joiner = JoinPattern("list")
result = joiner.join(processed)
```

### Filter Pattern

Filter data based on conditions:

```python
from streamware.patterns import FilterPattern

# Create filter
age_filter = FilterPattern(lambda x: x.get("age", 0) >= 18)

# Apply filter
users = [
    {"name": "Alice", "age": 30},
    {"name": "Bob", "age": 17},
    {"name": "Charlie", "age": 25}
]

adults = [user for user in users if age_filter.filter(user)]
```

### Aggregation

Aggregate data with various strategies:

```python
from streamware.patterns import JoinPattern

# Sum
joiner = JoinPattern("sum")
total = joiner.join([10, 20, 30, 40])  # Result: 100

# List (collect)
joiner = JoinPattern("list")
items = joiner.join([1, 2, 3])  # Result: [1, 2, 3]
```

### Conditional Processing

Route data based on conditions:

```python
def process_by_priority(data):
    priority = data.get("priority", "normal")
    
    if priority == "high":
        return flow("process://urgent").run(data)
    elif priority == "normal":
        return flow("process://standard").run(data)
    else:
        return flow("process://batch").run(data)
```

### Error Handling

Handle errors gracefully:

```python
try:
    result = (
        flow("http://api.example.com/data")
        | "transform://json"
        | "validate://schema"
        | "file://write?path=output.json"
    ).run()
except ComponentError as e:
    print(f"Pipeline error: {e}")
    # Handle error or fallback
```

### Streaming Data

Process data as a stream:

```python
# Stream processing
for item in flow("kafka://consume?topic=events").stream():
    processed = flow("transform://normalize").run(item)
    flow("postgres://insert?table=events").run(processed)
```

## Component Reference

### Core Components

#### File Component
- **Scheme**: `file`
- **Operations**: `read`, `write`, `delete`, `watch`
- **Parameters**: `path`, `mode`, `encoding`

```python
# Examples
flow("file://read?path=/tmp/data.txt")
flow("file://write?path=/tmp/output.json&mode=append")
flow("file://delete?path=/tmp/temp.txt")
```

#### HTTP Component
- **Scheme**: `http`, `https`
- **Operations**: Auto-detected from method parameter
- **Parameters**: `method`, `headers`, `timeout`

```python
# Examples
flow("http://api.example.com/users")
flow("http://api.example.com/users?method=post")
```

#### Transform Component
- **Scheme**: `transform`
- **Operations**: `json`, `csv`, `base64`, `jsonpath`, `template`
- **Parameters**: Operation-specific

```python
# Examples
flow("transform://json")
flow("transform://csv?delimiter=;")
flow("transform://base64?decode=true")
flow("transform://jsonpath?query=$.items[*]")
```

### Communication Components

#### Email Component
```python
flow("email://send?to=user@example.com&subject=Hello").run("Message body")
```

#### Telegram Component
```python
flow("telegram://send?chat_id=@channel&token=BOT_TOKEN").run("Hello!")
```

#### SMS Component
```python
flow("sms://send?provider=twilio&to=+1234567890").run("Alert!")
```

### Message Queue Components

#### Kafka Component
```python
# Consume
flow("kafka://consume?topic=events&group=processor")

# Produce
flow("kafka://produce?topic=events&key=id")
```

#### RabbitMQ Component
```python
# Consume
flow("rabbitmq://consume?queue=tasks")

# Publish
flow("rabbitmq://publish?exchange=events&routing_key=new")
```

### Database Components

#### PostgreSQL Component
```python
# Query
flow("postgres://query?sql=SELECT * FROM users")

# Insert
flow("postgres://insert?table=users")

# Update
flow("postgres://update?table=users&where=id=1")
```

## Testing

### Writing Tests

```python
import pytest
from streamware import flow, Component, register

def test_simple_pipeline():
    """Test basic pipeline"""
    data = {"test": "data"}
    result = flow("transform://json").run(data)
    assert isinstance(result, str)

def test_custom_component():
    """Test custom component"""
    @register("test-component")
    class TestComponent(Component):
        def process(self, data):
            return data * 2
    
    result = flow("test-component://").run(5)
    assert result == 10
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=streamware --cov-report=term-missing

# Run specific test file
pytest tests/test_streamware.py -v
```

## Best Practices

### 1. Component Design

- Keep components focused on single responsibility
- Use clear, descriptive scheme names
- Document required parameters
- Handle errors gracefully

```python
@register("process")
class ProcessComponent(Component):
    """
    Process data with specific transformation
    
    Parameters:
        mode (str): Processing mode (default: 'normal')
        validate (bool): Enable validation (default: True)
    """
    def process(self, data):
        mode = self.uri.get_param("mode", "normal")
        validate = self.uri.get_param("validate", True)
        
        if validate:
            self._validate(data)
        
        return self._process(data, mode)
```

### 2. Error Handling

Always handle errors appropriately:

```python
from streamware.exceptions import ComponentError

try:
    result = flow("risky://operation").run(data)
except ComponentError as e:
    # Log error
    logger.error(f"Operation failed: {e}")
    # Fallback strategy
    result = default_value
```

### 3. Pipeline Organization

Organize complex pipelines for readability:

```python
# Good: Clear stages
result = (
    flow("source://data")
    | "validate://schema"
    | "transform://normalize"
    | "enrich://metadata"
    | "sink://destination"
).run()

# Better: With comments
result = (
    flow("source://data")              # Fetch data
    | "validate://schema"               # Validate structure
    | "transform://normalize"           # Normalize format
    | "enrich://metadata"              # Add metadata
    | "sink://destination"             # Store result
).run()
```

### 4. Resource Management

Clean up resources properly:

```python
import tempfile
import os

temp_file = tempfile.mktemp(suffix=".json")
try:
    result = (
        flow("transform://json")
        | f"file://write?path={temp_file}"
    ).run(data)
finally:
    if os.path.exists(temp_file):
        os.remove(temp_file)
```

### 5. Testing

Test components in isolation:

```python
def test_component_isolation():
    """Test component without dependencies"""
    component = MyComponent(StreamwareURI("mycomp://"))
    
    # Test with mock data
    result = component.process({"test": "data"})
    
    # Assert expectations
    assert result["processed"] == True
```

### 6. Logging and Diagnostics

Enable diagnostics for debugging:

```python
import streamware

# Enable debug logging
streamware.enable_diagnostics(level="DEBUG")

# Use diagnostics in flows
flow("http://api.example.com/data") \
    .with_diagnostics(trace=True) \
    | "transform://json" \
    | "file://write?path=output.json"
```

### 7. Performance Optimization

- Use streaming for large datasets
- Batch operations when possible
- Cache expensive operations
- Monitor pipeline performance

```python
# Stream large datasets
for batch in flow("source://large-dataset").stream(batch_size=1000):
    process_batch(batch)

# Cache expensive lookups
@cache
def get_reference_data():
    return flow("database://reference").run()
```

## Examples

See the `examples/` directory for complete working examples:

- `basic_usage.py` - Basic patterns and operations
- `advanced_patterns.py` - Advanced workflow patterns
- `examples_communication.py` - Communication components
- `examples_advanced_communication.py` - Production patterns

## Support

- 📧 Email: info@softreck.com
- 🐛 Issues: [GitHub Issues](https://github.com/softreck/streamware/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/softreck/streamware/discussions)
- 📚 Documentation: [Read the Docs](https://streamware.readthedocs.io)

---

Built with ❤️ by [Softreck](https://softreck.com)
