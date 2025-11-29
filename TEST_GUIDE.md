# Test Guide - Streamware 0.2.0

## 📋 Overview

Comprehensive test suite for LLM-based components.

## 🧪 Test Files

### 1. `test_llm_components.py` - Unit Tests
Tests individual LLM components with mocking.

**Coverage:**
- LLM Component (generate, to_sql, analyze)
- Text2Streamware Component (convert, explain, optimize)
- Media Component (describe_video, describe_image, transcribe)
- Voice Component (listen, speak, command)
- Automation Component (click, type, hotkey, automate)
- Integration flows
- Quick helpers

**Run:**
```bash
pytest tests/test_llm_components.py -v
```

### 2. `test_llm_integration.py` - Integration Tests
Tests with actual Ollama/LLaVA models.

**Requirements:**
- Ollama installed and running
- Models: llama3.2, llava, qwen2.5:14b

**Coverage:**
- Real Ollama integration
- LLaVA image/video analysis
- Qwen2.5 command generation
- End-to-end workflows
- Performance tests

**Run:**
```bash
# Install Ollama first
curl -fsSL https://ollama.ai/install.sh | sh

# Pull models
ollama pull llama3.2
ollama pull llava
ollama pull qwen2.5:14b

# Run tests
pytest tests/test_llm_integration.py -v -s
```

### 3. `test_llm_edge_cases.py` - Edge Case Tests
Tests error handling and unusual inputs.

**Coverage:**
- Empty/invalid inputs
- Network errors
- File errors
- Concurrency
- Resource cleanup
- Rate limiting

**Run:**
```bash
pytest tests/test_llm_edge_cases.py -v
```

## 🚀 Running Tests

### All Tests
```bash
# Run all tests
make test

# Or manually
pytest tests/ -v
```

### Specific Tests
```bash
# Unit tests only (no Ollama needed)
pytest tests/test_llm_components.py -v

# Integration tests (needs Ollama)
pytest tests/test_llm_integration.py -v

# Edge cases
pytest tests/test_llm_edge_cases.py -v
```

### With Coverage
```bash
pytest tests/ -v --cov=streamware --cov-report=html
open htmlcov/index.html
```

### Specific Test
```bash
# Run single test
pytest tests/test_llm_components.py::TestLLMComponent::test_llm_component_creation -v

# Run test class
pytest tests/test_llm_components.py::TestLLMComponent -v
```

## 📊 Test Categories

### Unit Tests (Mocked)
✅ Fast execution  
✅ No dependencies  
✅ Test logic only  

```bash
pytest tests/test_llm_components.py -v
```

### Integration Tests (Real Models)
⚠️ Requires Ollama  
⚠️ Slower execution  
✅ Tests actual functionality  

```bash
pytest tests/test_llm_integration.py -v
```

### Edge Cases
✅ Error handling  
✅ Invalid inputs  
✅ Resource limits  

```bash
pytest tests/test_llm_edge_cases.py -v
```

## 🎯 Test Examples

### Test LLM Generation
```python
def test_llm_generate():
    result = flow("llm://generate?prompt=Say hello&provider=ollama").run()
    assert "hello" in str(result).lower()
```

### Test Image Description
```python
def test_describe_image():
    result = flow("media://describe_image?file=photo.jpg&model=llava").run()
    assert result["success"] == True
    assert len(result["description"]) > 0
```

### Test Voice Control
```python
def test_voice_speak():
    result = flow("voice://speak?text=Hello World").run()
    assert result["success"] == True
```

### Test Automation
```python
def test_mouse_click():
    result = flow("automation://click?x=100&y=200").run()
    assert result["success"] == True
```

## 🔧 Setup for Testing

### 1. Install Test Dependencies
```bash
pip install pytest pytest-cov pytest-mock
```

### 2. Install Ollama (for integration tests)
```bash
# Linux/Mac
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama
ollama serve

# Pull models
ollama pull llama3.2
ollama pull llava
ollama pull qwen2.5:14b
```

### 3. Optional Dependencies
```bash
# Voice
pip install SpeechRecognition pyttsx3 PyAudio

# Automation
pip install pyautogui

# Media
pip install opencv-python Pillow
```

## 📈 Test Coverage Goals

| Component | Current | Goal |
|-----------|---------|------|
| LLM | 25% | 80% |
| Media | 17% | 70% |
| Voice | New | 60% |
| Automation | New | 60% |
| Overall | 25% | 70% |

## 🐛 Known Issues

### 1. Ollama Connection
**Issue:** Tests fail if Ollama not running  
**Fix:** Start Ollama: `ollama serve`

### 2. Missing Models
**Issue:** LLaVA tests skip if model not available  
**Fix:** `ollama pull llava`

### 3. No Microphone
**Issue:** Voice tests fail without microphone  
**Expected:** Tests should skip gracefully

### 4. Headless Environment
**Issue:** Automation tests fail without display  
**Expected:** Tests should skip or mock

## 💡 Writing New Tests

### Template for Unit Test
```python
from unittest.mock import patch
from streamware import flow

class TestMyFeature:
    @patch('requests.post')
    def test_my_feature(self, mock_post):
        # Setup mock
        mock_post.return_value = Mock(
            ok=True,
            json=lambda: {"response": "test"}
        )
        
        # Run
        result = flow("component://operation?param=value").run()
        
        # Assert
        assert result is not None
```

### Template for Integration Test
```python
import pytest
from streamware import flow

@pytest.mark.skipif(not ollama_available(), reason="Ollama not available")
class TestMyIntegration:
    def test_real_ollama(self):
        result = flow("llm://generate?prompt=test").run()
        assert len(str(result)) > 0
```

## 🎓 Best Practices

1. **Mock External APIs** - Use mocks for unit tests
2. **Skip If Unavailable** - Use pytest.skipif for optional features
3. **Test Edge Cases** - Include error scenarios
4. **Clean Up Resources** - Close files, connections
5. **Use Fixtures** - Share setup code with fixtures
6. **Descriptive Names** - Test names should explain what they test
7. **Assert Clearly** - Clear assertion messages
8. **Keep Tests Fast** - Mock slow operations

## 📝 Test Matrix

### Components to Test

| Component | Unit | Integration | Edge Cases |
|-----------|------|-------------|------------|
| llm | ✅ | ✅ | ✅ |
| media | ✅ | ✅ | ✅ |
| voice | ✅ | ⚠️ | ✅ |
| automation | ✅ | ⚠️ | ✅ |
| text2streamware | ✅ | ✅ | ✅ |
| video | ✅ | ✅ | ✅ |

✅ Complete  
⚠️ Requires hardware  

## 🚀 CI/CD Integration

### GitHub Actions
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest tests/ -v --cov=streamware
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

### GitLab CI
```yaml
test:
  script:
    - pip install -r requirements.txt
    - pytest tests/ -v --cov=streamware
  coverage: '/TOTAL.*\s+(\d+%)$/'
```

## 📊 Current Test Results

```bash
# Run all tests
make test

# Expected output:
# tests/test_streamware.py ..................... 21 passed
# tests/test_communication.py ................. 20 passed
# tests/test_llm_components.py ................ 30 passed
# 
# =========== 71 passed in 2.50s ===========
```

---

**Comprehensive testing for reliable AI-powered automation! 🧪✨**
