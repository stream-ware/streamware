# Build Commands - Streamware 0.2.0

## 📋 Menu
- [Clean Build](#clean-build)
- [Development](#development)
- [Testing](#testing)
- [Publishing](#publishing)
- [Quick Commands](#quick-commands)

---

## 🧹 Clean Build

```bash
# Clean all build artifacts
make clean

# Deep clean (including venv)
rm -rf build/ dist/ *.egg-info venv/
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

## 🔨 Development

### Setup Development Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
make dev

# Or manually:
pip install -e ".[dev]"
```

### Build Package

```bash
# Clean and build
make clean build

# Or manually:
rm -rf build/ dist/ *.egg-info
python3 -m build
```

### Install Build Tools

```bash
# Setup publishing tools
make setup-publish

# Or manually:
pip install build twine wheel
```

## 🧪 Testing

```bash
# Run all tests
make test

# Run with coverage
pytest --cov=streamware --cov-report=term-missing

# Run specific test
pytest tests/test_components.py

# Run examples
python examples/deploy_examples.py
python examples/llm_examples.py
bash examples/quick_start_example.sh
```

## 📦 Publishing

### Version Bump

Version already bumped to **0.2.0** in:
- ✅ `streamware/__init__.py`
- ✅ `pyproject.toml`
- ✅ `CHANGELOG.md`

### Build and Publish

```bash
# 1. Clean previous builds
make clean

# 2. Build distribution
make build

# 3. Check built files
ls -lh dist/
# Should see:
#   streamware-0.2.0-py3-none-any.whl
#   streamware-0.2.0.tar.gz

# 4. Publish to PyPI
make publish

# Or manually:
python3 -m twine upload dist/*
```

### Test PyPI (Optional)

```bash
# Upload to test PyPI first
python3 -m twine upload --repository testpypi dist/*

# Install from test PyPI
pip install --index-url https://test.pypi.org/simple/ streamware==0.2.0

# Test installation
sq --version
python -c "import streamware; print(streamware.__version__)"
```

## ⚡ Quick Commands

### One-Liner Build

```bash
make clean && make build
```

### One-Liner Publish

```bash
make clean && make build && make publish
```

### Complete Development Cycle

```bash
# Setup
make dev

# Test
make test

# Build
make clean build

# Publish
make publish
```

## 🔍 Verify Installation

After publishing:

```bash
# Wait a few minutes for PyPI to update, then:

# Install from PyPI
pip install streamware==0.2.0

# Verify version
python -c "import streamware; print(streamware.__version__)"
# Should output: 0.2.0

# Test CLI
sq --version

# Test components
sq registry list --type component
sq template list
sq setup check --packages requests
```

## 🐛 Troubleshooting

### Error: "File already exists"

```bash
# Version 0.2.0 already published, increment version:
# 1. Edit streamware/__init__.py: __version__ = "0.2.1"
# 2. Edit pyproject.toml: version = "0.2.1"
# 3. Update CHANGELOG.md with new version
# 4. Rebuild and publish
make clean build publish
```

### Error: "No module named build"

```bash
# Install build tools
make setup-publish
# Or:
pip install build twine wheel
```

### Error: "Permission denied"

```bash
# Make sure you're authenticated to PyPI
# 1. Create ~/.pypirc with API token:
cat > ~/.pypirc << EOF
[pypi]
username = __token__
password = pypi-your-token-here
EOF

# 2. Set permissions
chmod 600 ~/.pypirc

# 3. Try publishing again
make publish
```

### Deprecation Warning: License Classifier

```bash
# Already fixed in version 0.2.0!
# Removed deprecated "License :: OSI Approved" classifier
# License still Apache-2.0 via: license = {text = "Apache-2.0"}
```

## 📊 Build Checklist

Before publishing, verify:

- [x] Version bumped (0.1.0 → 0.2.0)
- [x] CHANGELOG.md updated
- [x] Tests passing
- [x] License classifier removed
- [x] Development status updated (Alpha → Beta)
- [x] Documentation updated
- [x] Examples working
- [x] Components registered
- [x] Build tools installed

## 🚀 Post-Publish

After successful publish:

```bash
# 1. Tag release in git
git tag v0.2.0
git push origin v0.2.0

# 2. Create GitHub release
# Go to: https://github.com/softreck/streamware/releases
# Create release from tag v0.2.0
# Add changelog from CHANGELOG.md

# 3. Update documentation
# Ensure all docs reference 0.2.0

# 4. Announce
# - GitHub Discussions
# - Twitter/X
# - Email list
```

## 📝 Version History

| Version | Date | Status | Changes |
|---------|------|--------|---------|
| 0.1.0 | 2024-01-20 | Alpha | Initial release |
| 0.2.0 | 2025-11-28 | Beta | +8 components, auto-install, templates, registry |

## 🎯 Next Version (0.3.0)

Planned features:
- Plugin system
- Cloud registry
- Visual builder
- Performance improvements
- Enhanced testing

---

**Current Version: 0.2.0 (Beta)**  
**Ready to publish! 🚀**

```bash
make clean && make build && make publish
```
