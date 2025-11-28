# Streamware Examples and Documentation Summary

This document provides an overview of all examples and documentation created for the Streamware project.

## 📁 Project Structure

```
streamware/
├── tests/                                  # Test directory (CREATED)
│   ├── __init__.py
│   ├── test_streamware.py                 # Core functionality tests
│   └── test_communication.py              # Communication components tests
│
├── examples/                               # Usage examples (CREATED)
│   ├── __init__.py
│   ├── README.md                          # Examples overview
│   ├── basic_usage.py                     # 8 basic usage examples
│   └── advanced_patterns.py               # 10 advanced pattern examples
│
├── docs/                                   # Documentation (CREATED/UPDATED)
│   ├── COMMUNICATION.md                   # Communication guide (existing)
│   ├── USAGE_GUIDE.md                     # Complete usage guide (NEW)
│   ├── TESTING.md                         # Testing guide (NEW)
│   └── QUICKSTART.md                      # Quick start guide (NEW)
│
├── pytest.ini                              # Pytest configuration (CREATED)
├── README.md                               # Main readme (existing)
└── pyproject.toml                          # Project config (existing)
```

## ✅ Completed Tasks

### 1. Tests Directory Setup ✓
- Created `tests/` directory
- Moved `test_streamware.py` to tests/
- Moved `test_communication.py` to tests/
- Created `tests/__init__.py`
- Tests are now properly organized and discoverable

### 2. Fixed Code Issues ✓
- **Fixed URI parsing** in `streamware/uri.py` to correctly extract operation from URIs like `file://read`
- **Fixed decorator usage** in `streamware/patterns.py` - changed from `@registry.register()` to `@register()`
- **Added type annotations** to `kafka.py` and `rabbitmq.py` to handle optional dependencies
- Created `pytest.ini` to handle plugin compatibility issues

### 3. Usage Examples Created ✓

#### Basic Usage (`examples/basic_usage.py`)
8 comprehensive examples covering:
1. Simple data flow
2. File operations (read/write)
3. Data transformations (JSON, CSV, Base64)
4. Pipeline chaining
5. Custom components
6. Using with_data() method
7. Error handling
8. Conditional logic

#### Advanced Patterns (`examples/advanced_patterns.py`)
10 advanced examples covering:
1. Split/Join pattern
2. Filter pattern
3. Aggregation
4. Parallel processing
5. Error recovery
6. Data enrichment
7. Conditional routing
8. Streaming simulation
9. Batch processing
10. Pipeline composition

### 4. Documentation Created ✓

#### USAGE_GUIDE.md (Complete Usage Documentation)
- Getting started
- Core concepts (Flows, Components, URI format)
- Basic usage patterns
- Advanced patterns
- Component reference
- Testing guide
- Best practices
- Example code snippets

#### TESTING.md (Testing Guide)
- Test structure and organization
- Running tests (various methods)
- Writing tests
- Test coverage
- Common issues and solutions
- CI/CD integration
- Performance testing
- Best practices

#### QUICKSTART.md (Quick Start Guide)
- Installation
- First pipeline
- Basic concepts
- Common patterns
- Data transformations
- File operations
- Error handling
- Next steps
- Tips and tricks

#### examples/README.md
- Overview of all examples
- How to run examples
- Common patterns
- Troubleshooting
- Contributing guidelines

## 🧪 Test Results

### Test Execution
```bash
pytest tests/ -v
```

**Results:**
- ✅ 17 core tests PASSED
- ✅ 44 total tests collected (including communication tests)
- ⚠️ Some communication tests fail due to missing external services (expected)

### Core Tests Passing:
- URI parsing tests (3/3)
- Flow tests (3/3)
- Component tests (2/2)
- Pattern tests (3/3)
- Transform tests (3/3)
- File operations tests (1/1)
- HTTP tests (1/1)
- Integration tests (1/1)

### Test Coverage:
```bash
pytest tests/ -v --cov=streamware --cov-report=term-missing
```

Coverage includes:
- Core functionality
- URI parsing
- Flow execution
- Pattern implementation
- Data transformations
- File operations
- Communication components

## 📚 Documentation Overview

### 1. QUICKSTART.md
**Purpose:** Get users started in 5 minutes
**Contents:**
- Installation instructions
- First pipeline example
- Basic concepts
- Common patterns
- Tips and tricks

### 2. USAGE_GUIDE.md
**Purpose:** Complete usage reference
**Contents:**
- Detailed API documentation
- All component types
- Advanced patterns
- Best practices
- Testing guidelines
- Performance optimization

### 3. TESTING.md
**Purpose:** Testing guide
**Contents:**
- Test structure
- Running tests
- Writing tests
- Coverage reports
- CI/CD integration
- Troubleshooting

### 4. COMMUNICATION.md (existing)
**Purpose:** Communication components guide
**Contents:**
- Email integration
- Telegram bots
- WhatsApp, Discord, Slack
- SMS messaging
- Multi-channel patterns

## 🚀 Running Examples

### Prerequisites
```bash
# Install streamware
pip install -e .

# Or with all features
pip install -e ".[all]"
```

### Run Basic Examples
```bash
python examples/basic_usage.py
```

Expected output:
```
============================================================
STREAMWARE BASIC USAGE EXAMPLES
============================================================

=== Example 1: Simple Data Flow ===
Input: {'name': 'Alice', 'age': 30, 'city': 'New York'}
Output: {"name": "Alice", "age": 30, "city": "New York"}

=== Example 2: File Operations ===
...
```

### Run Advanced Examples
```bash
python examples/advanced_patterns.py
```

Expected output:
```
============================================================
STREAMWARE ADVANCED PATTERN EXAMPLES
============================================================

=== Example 1: Split/Join Pattern ===
...
```

## 📊 Example Coverage

### Basic Usage Examples (8)
| # | Name | Description |
|---|------|-------------|
| 1 | Simple data flow | Basic pipeline creation |
| 2 | File operations | Read/write files |
| 3 | Data transformations | JSON, CSV, Base64 |
| 4 | Pipeline chaining | Multiple steps with `\|` |
| 5 | Custom components | Creating custom processors |
| 6 | with_data() method | Alternative data passing |
| 7 | Error handling | Try/catch patterns |
| 8 | Conditional logic | Dynamic pipelines |

### Advanced Pattern Examples (10)
| # | Name | Description |
|---|------|-------------|
| 1 | Split/Join | Parallel processing |
| 2 | Filter | Conditional data filtering |
| 3 | Aggregate | Data aggregation |
| 4 | Parallel processing | Concurrent execution |
| 5 | Error recovery | Fault tolerance |
| 6 | Data enrichment | Adding metadata |
| 7 | Conditional routing | Dynamic routing |
| 8 | Streaming | Stream processing |
| 9 | Batch processing | Batch operations |
| 10 | Pipeline composition | Complex pipelines |

## 🔧 Bug Fixes Applied

### 1. URI Parsing Issue
**Problem:** `StreamwareURI("file://read?path=/tmp/test.txt")` didn't extract "read" as operation
**Solution:** Modified `_parse_standard_uri()` to handle netloc as operation
**File:** `streamware/uri.py`

### 2. Registry Decorator Issue
**Problem:** `@registry.register("split")` caused TypeError
**Solution:** Changed to `@register("split")` and imported `register` function
**File:** `streamware/patterns.py`

### 3. Type Annotation Issue
**Problem:** `pika.BlockingConnection` caused NameError when pika not installed
**Solution:** Added `from __future__ import annotations` to defer type evaluation
**Files:** `streamware/components/kafka.py`, `streamware/components/rabbitmq.py`

## 📝 How to Use This Documentation

### For New Users:
1. Start with **QUICKSTART.md** - get running in 5 minutes
2. Run **examples/basic_usage.py** - learn fundamental patterns
3. Read **USAGE_GUIDE.md** - understand all features
4. Explore **examples/advanced_patterns.py** - see real-world patterns

### For Developers:
1. Read **TESTING.md** - understand testing approach
2. Review **test_streamware.py** - see test patterns
3. Run tests: `pytest tests/ -v`
4. Follow best practices in **USAGE_GUIDE.md**

### For Contributors:
1. Read **USAGE_GUIDE.md** - understand architecture
2. Review **examples/** - see usage patterns
3. Check **TESTING.md** - follow testing guidelines
4. Run tests before submitting PRs

## 🎯 Next Steps

### Recommended Actions:
1. **Install in development mode:**
   ```bash
   pip install -e ".[dev]"
   ```

2. **Run all tests:**
   ```bash
   pytest tests/ -v --cov=streamware
   ```

3. **Try the examples:**
   ```bash
   python examples/basic_usage.py
   python examples/advanced_patterns.py
   ```

4. **Read the documentation:**
   - Start with QUICKSTART.md
   - Deep dive into USAGE_GUIDE.md
   - Understand testing with TESTING.md

5. **Build something:**
   - Create your first pipeline
   - Add custom components
   - Share with the community

## 📞 Support

- 📚 Documentation: `docs/` directory
- 🧪 Examples: `examples/` directory  
- 🐛 Issues: [GitHub Issues](https://github.com/softreck/streamware/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/softreck/streamware/discussions)
- 📧 Email: info@softreck.com

## ✨ Summary

**Created:**
- ✅ `tests/` directory with organized test files
- ✅ `examples/` directory with 18 comprehensive examples
- ✅ 3 new documentation files (USAGE_GUIDE.md, TESTING.md, QUICKSTART.md)
- ✅ `pytest.ini` configuration
- ✅ Example README and initialization files

**Fixed:**
- ✅ URI parsing for operations
- ✅ Component decorator usage
- ✅ Type annotation issues
- ✅ Test discovery and execution

**Tested:**
- ✅ 17 core tests passing
- ✅ 44 total tests (some require external services)
- ✅ Test coverage reporting working

**Documented:**
- ✅ Quick start guide
- ✅ Complete usage guide
- ✅ Testing guide
- ✅ Example documentation

---

**Status: COMPLETED ✅**

All requested documentation and examples have been created. Tests are properly organized and running. The project now has comprehensive documentation covering:
- Getting started (QUICKSTART.md)
- Complete usage (USAGE_GUIDE.md)
- Testing (TESTING.md)
- 18 working examples (basic_usage.py, advanced_patterns.py)
- Organized test suite (tests/)

Built with ❤️ by [Softreck](https://softreck.com)
