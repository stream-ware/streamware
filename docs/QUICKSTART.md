# Streamware Quick Start Guide

Get started with Streamware in 5 minutes!

## Installation

```bash
# Basic installation
pip install streamware

# With all features
pip install streamware[all]
```

## Your First Pipeline

Create a file `hello_streamware.py`:

```python
from streamware import flow

# Create a simple pipeline
result = flow("transform://json").run({"message": "Hello, Streamware!"})
print(result)
```

Run it:
```bash
python hello_streamware.py
```

Output:
```json
{"message": "Hello, Streamware!"}
```

## Basic Concepts

### 1. Flows

A **Flow** is a pipeline of processing steps:

```python
from streamware import flow

# Single step
flow("component://operation")

# Multiple steps (chaining)
flow("step1://") | "step2://" | "step3://"
```

### 2. Components

**Components** are the building blocks that process data:

```python
# File operations
flow("file://read?path=/tmp/data.txt")
flow("file://write?path=/tmp/output.txt")

# Data transformation
flow("transform://json")
flow("transform://csv")

# HTTP requests
flow("http://api.example.com/data")
```

### 3. URI Syntax

Components use URI-style syntax:

```
scheme://operation?param1=value1&param2=value2
```

Examples:
```python
"file://read?path=/tmp/data.json"
"http://api.example.com/users?limit=10"
"transform://csv?delimiter=;"
```

## Common Patterns

### Pattern 1: Read → Transform → Write

```python
import tempfile
import os

temp_file = os.path.join(tempfile.gettempdir(), "output.json")

data = {"users": ["Alice", "Bob", "Charlie"]}

result = (
    flow("transform://json")
    | f"file://write?path={temp_file}"
).run(data)

print(f"Written to: {temp_file}")
```

### Pattern 2: HTTP → Process → Save

```python
# Fetch data from API, transform it, and save
result = (
    flow("http://api.example.com/data")
    | "transform://jsonpath?query=$.items[*]"
    | "file://write?path=results.json"
).run()
```

### Pattern 3: Custom Processing

```python
from streamware import Component, register

@register("uppercase")
class UppercaseComponent(Component):
    def process(self, data):
        return data.upper() if isinstance(data, str) else data

# Use your custom component
result = flow("uppercase://").run("hello world")
print(result)  # Output: HELLO WORLD
```

## Data Transformations

### JSON

```python
# Parse JSON string
data = flow("transform://json").run('{"key": "value"}')

# Convert to JSON string
json_str = flow("transform://json").run({"key": "value"})
```

### CSV

```python
# Convert list of dicts to CSV
data = [
    {"name": "Alice", "age": 30},
    {"name": "Bob", "age": 25}
]
csv_output = flow("transform://csv").run(data)
print(csv_output)
```

### Base64

```python
# Encode
encoded = flow("transform://base64").run("Hello World")

# Decode
decoded = flow("transform://base64?decode=true").run(encoded)
```

## File Operations

### Read File

```python
content = flow("file://read?path=/tmp/input.txt").run()
print(content)
```

### Write File

```python
flow("file://write?path=/tmp/output.txt").run("Hello, World!")
```

### Append to File

```python
flow("file://write?path=/tmp/log.txt&mode=append").run("Log entry\n")
```

## Error Handling

```python
try:
    result = flow("file://read?path=/nonexistent.txt").run()
except Exception as e:
    print(f"Error: {e}")
    result = None
```

## Next Steps

### 1. Run Examples

```bash
# Basic usage patterns
python examples/basic_usage.py

# Advanced patterns
python examples/advanced_patterns.py
```

### 2. Read Documentation

- [Usage Guide](USAGE_GUIDE.md) - Complete usage documentation
- [Testing Guide](TESTING.md) - Testing your pipelines
- [Communication Guide](COMMUNICATION.md) - Email, SMS, chat integration

### 3. Explore Components

```python
from streamware.core import registry

# List all available components
print(registry.list_components())
```

### 4. Build Your First Real Pipeline

```python
from streamware import flow
import os

def process_data_pipeline():
    """
    Example: Read CSV, process data, save results
    """
    try:
        # Your pipeline here
        result = (
            flow("file://read?path=input.csv")
            | "transform://csv"
            | "your-processing://"
            | "file://write?path=output.json"
        ).run()
        
        print("Pipeline completed successfully!")
        return result
        
    except Exception as e:
        print(f"Pipeline failed: {e}")
        return None

# Run it
if __name__ == "__main__":
    process_data_pipeline()
```

## Common Use Cases

### 1. Data ETL

```python
# Extract, Transform, Load
(
    flow("database://query?sql=SELECT * FROM users")
    | "transform://normalize"
    | "transform://validate"
    | "database://insert?table=processed_users"
).run()
```

### 2. API Integration

```python
# Fetch from API and process
(
    flow("http://api.example.com/data")
    | "transform://jsonpath?query=$.results[*]"
    | "enrich://metadata"
    | "kafka://produce?topic=events"
).run()
```

### 3. File Processing

```python
# Process multiple files
import glob

for file_path in glob.glob("/data/*.json"):
    (
        flow(f"file://read?path={file_path}")
        | "validate://schema"
        | "transform://clean"
        | f"file://write?path=/processed/{os.path.basename(file_path)}"
    ).run()
```

### 4. Monitoring & Alerts

```python
# Check system and send alerts
status = flow("system://health").run()

if status["cpu_percent"] > 80:
    (
        flow("slack://send?channel=ops&token=TOKEN")
    ).run(f"High CPU usage: {status['cpu_percent']}%")
```

## Tips and Tricks

### 1. Enable Debug Logging

```python
import streamware
streamware.enable_diagnostics(level="DEBUG")

# Now all pipeline operations will be logged
flow("http://api.example.com").run()
```

### 2. Chain Multiple Operations

```python
# Use | operator for clean chaining
result = (
    flow("step1://")
    | "step2://"
    | "step3://"
    | "step4://"
).run(input_data)
```

### 3. Reuse Flows

```python
# Create reusable flow
normalize_flow = (
    flow("validate://schema")
    | "transform://normalize"
    | "enrich://metadata"
)

# Use it multiple times
result1 = normalize_flow.run(data1)
result2 = normalize_flow.run(data2)
```

### 4. Conditional Processing

```python
def process_by_type(data):
    data_type = data.get("type")
    
    if data_type == "json":
        return flow("transform://json").run(data)
    elif data_type == "csv":
        return flow("transform://csv").run(data)
    else:
        return flow("transform://text").run(data)
```

## Getting Help

- 📚 [Documentation](https://streamware.readthedocs.io)
- 💬 [GitHub Discussions](https://github.com/softreck/streamware/discussions)
- 🐛 [Report Issues](https://github.com/softreck/streamware/issues)
- 📧 [Email Support](mailto:info@softreck.com)

## What's Next?

Now that you've learned the basics, explore:

1. **Advanced Patterns** - Split/join, multicast, conditional routing
2. **Communication Components** - Email, SMS, Slack, Telegram
3. **Message Brokers** - Kafka, RabbitMQ integration
4. **Custom Components** - Build your own components
5. **Production Deployment** - Best practices and patterns

---

Happy streaming! 🚀

Built with ❤️ by [Softreck](https://softreck.com)
