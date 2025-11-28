# Streamware Testing Guide

Complete guide for testing the Streamware framework.

## Test Structure

```
streamware/
├── tests/                          # Test directory
│   ├── __init__.py
│   ├── test_streamware.py         # Core functionality tests
│   └── test_communication.py       # Communication components tests
├── examples/                       # Usage examples
│   ├── __init__.py
│   ├── README.md
│   ├── basic_usage.py
│   └── advanced_patterns.py
└── pytest.ini                      # Pytest configuration
```

## Running Tests

### Basic Test Execution

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_streamware.py -v

# Run specific test class
pytest tests/test_streamware.py::TestURI -v

# Run specific test
pytest tests/test_streamware.py::TestURI::test_basic_uri -v
```

### With Coverage

```bash
# Run with coverage report
pytest tests/ -v --cov=streamware --cov-report=term-missing

# Generate HTML coverage report
pytest tests/ -v --cov=streamware --cov-report=html

# View HTML report
open htmlcov/index.html
```

### Using Make

```bash
# Run tests using Makefile
make test

# Note: If you encounter plugin compatibility issues, use:
python3 -m pytest tests/ -v --cov=streamware --cov-report=term-missing
```

## Test Organization

### Core Tests (`test_streamware.py`)

#### TestURI
Tests for URI parsing and parameter extraction:
- `test_basic_uri` - Basic URI parsing
- `test_http_uri` - HTTP/HTTPS URL parsing
- `test_complex_params` - Complex parameter handling

#### TestFlow
Tests for flow creation and execution:
- `test_flow_creation` - Flow initialization
- `test_flow_chaining` - Pipeline chaining with `|`
- `test_flow_with_data` - Using `with_data()` method

#### TestComponent
Tests for component registration and execution:
- `test_component_registration` - Custom component registration
- `test_component_mime_validation` - MIME type validation

#### TestPatterns
Tests for workflow patterns:
- `test_split_pattern` - Split data into parts
- `test_join_pattern` - Join split data
- `test_filter_pattern` - Filter data

#### TestTransformComponent
Tests for data transformations:
- `test_json_transform` - JSON parsing/serialization
- `test_csv_transform` - CSV conversion
- `test_base64_transform` - Base64 encoding/decoding

#### TestFileComponent
Tests for file operations:
- `test_file_operations` - Read, write, delete files

#### TestHTTPComponent
Tests for HTTP operations:
- `test_http_uri_parsing` - HTTP URI parsing

#### TestIntegration
Integration tests for complete pipelines:
- `test_simple_pipeline` - End-to-end pipeline test

### Communication Tests (`test_communication.py`)

Tests for all communication components:
- Email (SMTP/IMAP)
- Telegram
- WhatsApp
- Discord
- Slack
- SMS

## Writing Tests

### Basic Test Structure

```python
import pytest
from streamware import flow, Component, register

def test_my_feature():
    """Test description"""
    # Arrange
    data = {"test": "data"}
    
    # Act
    result = flow("transform://json").run(data)
    
    # Assert
    assert isinstance(result, str)
    assert "test" in result
```

### Testing Custom Components

```python
def test_custom_component():
    """Test custom component"""
    @register("mycomp")
    class MyComponent(Component):
        def process(self, data):
            return data * 2
    
    result = flow("mycomp://").run(5)
    assert result == 10
```

### Testing with Fixtures

```python
import pytest

@pytest.fixture
def sample_data():
    """Sample test data"""
    return {"users": ["Alice", "Bob", "Charlie"]}

def test_with_fixture(sample_data):
    """Test using fixture"""
    result = flow("transform://json").run(sample_data)
    assert "Alice" in result
```

### Mocking External Services

```python
from unittest.mock import patch, MagicMock

def test_with_mock():
    """Test with mocked external service"""
    with patch('requests.get') as mock_get:
        mock_get.return_value.json.return_value = {"data": "test"}
        
        # Test your code that uses requests.get
        result = flow("http://api.example.com/data").run()
        assert result["data"] == "test"
```

### Testing Async Components

```python
import pytest
import asyncio

@pytest.mark.asyncio
async def test_async_component():
    """Test async component"""
    @register("async-comp")
    class AsyncComponent(Component):
        async def process_async(self, data):
            await asyncio.sleep(0.1)
            return data * 2
    
    result = await flow("async-comp://").run_async(5)
    assert result == 10
```

## Test Coverage

Current test coverage includes:

### Core Functionality ✓
- URI parsing and parameter handling
- Flow creation and chaining
- Component registration
- Pattern execution (split, join, filter)
- Data transformations
- File operations

### Communication Components ✓
- Email (SMTP/IMAP)
- Telegram
- WhatsApp
- Discord
- Slack
- SMS

### Advanced Patterns ✓
- Multicast
- Choice/routing
- Aggregation
- Streaming

## Common Issues and Solutions

### Issue: Import Errors

```bash
# Solution: Install streamware in development mode
pip install -e .

# Or install with dev dependencies
pip install -e ".[dev]"
```

### Issue: Plugin Compatibility

```bash
# Error: AttributeError: module 'pytest_asyncio' has no attribute 'fixture'

# Solution: Use pytest.ini with plugin exclusions
# Already configured in pytest.ini:
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -p no:aiohttp --tb=short
```

### Issue: Missing Dependencies

```bash
# Some tests require optional dependencies

# Install all dependencies
pip install streamware[all]

# Or install specific dependencies
pip install streamware[communication]
pip install streamware[kafka,rabbitmq]
```

### Issue: Connection Tests Failing

Some tests attempt to connect to external services (SMTP, IMAP, etc.) and may fail if services are unavailable. These are expected failures in CI/local environments without those services.

```bash
# Skip tests requiring external services
pytest tests/ -v -k "not email_read and not whatsapp_send"
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, 3.10, 3.11, 3.12]
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v2
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install -e ".[dev]"
    
    - name: Run tests
      run: |
        pytest tests/ -v --cov=streamware --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
      with:
        file: ./coverage.xml
```

## Test Data

Test data should be:
- **Minimal**: Use the smallest data set that tests the feature
- **Isolated**: Don't depend on external state
- **Deterministic**: Same input should always produce same output
- **Clean**: Use fixtures and teardown to avoid side effects

### Example Test Data

```python
# Good: Minimal and clear
TEST_USER = {"name": "Alice", "age": 30}

# Good: Deterministic
TEST_TIMESTAMP = "2024-01-01T00:00:00Z"

# Good: Multiple test cases
TEST_CASES = [
    ({"input": 1}, {"output": 2}),
    ({"input": 2}, {"output": 4}),
    ({"input": 3}, {"output": 6}),
]
```

## Performance Testing

### Benchmark Tests

```python
import time

def test_performance():
    """Test pipeline performance"""
    data = [{"id": i, "value": i * 10} for i in range(1000)]
    
    start = time.time()
    result = flow("transform://json").run(data)
    elapsed = time.time() - start
    
    assert elapsed < 1.0, f"Pipeline too slow: {elapsed}s"
```

### Load Testing

```python
def test_concurrent_execution():
    """Test concurrent pipeline execution"""
    from concurrent.futures import ThreadPoolExecutor
    
    def run_pipeline(data):
        return flow("transform://json").run(data)
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(run_pipeline, {"id": i}) 
                  for i in range(100)]
        results = [f.result() for f in futures]
    
    assert len(results) == 100
```

## Test Maintenance

### Running Tests Before Commit

```bash
# Run tests and ensure they pass
pytest tests/ -v

# Check code style
black streamware/ tests/
flake8 streamware/ tests/

# Type checking
mypy streamware/
```

### Updating Tests

When adding new features:
1. Write tests first (TDD approach)
2. Ensure existing tests pass
3. Add tests for edge cases
4. Update documentation

## Best Practices

1. **One assertion per test** (when possible)
2. **Clear test names** describing what is being tested
3. **Arrange-Act-Assert** pattern
4. **Use fixtures** for common setup
5. **Mock external dependencies**
6. **Test edge cases** and error conditions
7. **Keep tests fast** - avoid slow operations
8. **Test in isolation** - no dependencies between tests

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [unittest.mock documentation](https://docs.python.org/3/library/unittest.mock.html)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)

---

For more information, see:
- [Usage Guide](USAGE_GUIDE.md)
- [Communication Guide](COMMUNICATION.md)
- [API Reference](https://streamware.readthedocs.io)
