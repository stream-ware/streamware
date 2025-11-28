# Publishing Streamware to PyPI

Guide for publishing Streamware packages to PyPI.

## 🔧 Prerequisites

### 1. Install Build Tools

```bash
# Option 1: Make target
make setup-publish

# Option 2: Manual install
pip install build twine wheel
```

### 2. PyPI Account Setup

1. Create account on [PyPI](https://pypi.org/account/register/)
2. Create account on [TestPyPI](https://test.pypi.org/account/register/)
3. Configure API tokens

### 3. Configure API Tokens

Create `~/.pypirc`:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR_API_TOKEN_HERE

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-YOUR_TEST_API_TOKEN_HERE
```

**Security:** Set permissions:
```bash
chmod 600 ~/.pypirc
```

## 📦 Publishing Process

### Step 1: Update Version

Edit `streamware/__init__.py`:

```python
__version__ = "0.1.1"  # Update version
```

Edit `pyproject.toml`:

```toml
[project]
name = "streamware"
version = "0.1.1"  # Same version
```

### Step 2: Update Changelog

Add to `CHANGELOG.md`:

```markdown
## [0.1.1] - 2024-01-XX

### Added
- New features

### Changed
- Updates

### Fixed
- Bug fixes
```

### Step 3: Commit Changes

```bash
git add .
git commit -m "Release version 0.1.1"
git tag -a v0.1.1 -m "Version 0.1.1"
```

### Step 4: Test Build

```bash
# Clean and build
make build

# Check dist/ directory
ls -lh dist/
# Should see:
# - streamware-0.1.1.tar.gz
# - streamware-0.1.1-py3-none-any.whl
```

### Step 5: Publish to TestPyPI (Optional)

```bash
# Publish to TestPyPI first
make publish-test

# Test installation
pip install --index-url https://test.pypi.org/simple/ streamware==0.1.1
```

### Step 6: Publish to PyPI

```bash
# Final publish
make publish

# Verify on PyPI
open https://pypi.org/project/streamware/
```

### Step 7: Push to GitHub

```bash
git push origin main
git push origin v0.1.1
```

## 🚀 Quick Publish (After Setup)

```bash
# 1. Update version in code
# 2. Update CHANGELOG.md
# 3. Commit and tag
git add .
git commit -m "Release v0.1.1"
git tag v0.1.1

# 4. Build and publish
make publish

# 5. Push
git push && git push --tags
```

## 🧪 Testing Published Package

```bash
# Create clean environment
python -m venv test-env
source test-env/bin/activate

# Install from PyPI
pip install streamware

# Test
python -c "from streamware import flow; print('OK')"

# Test CLI
streamware --version
sq --help

# Cleanup
deactivate
rm -rf test-env
```

## 📋 Pre-release Checklist

- [ ] All tests passing (`make test`)
- [ ] Version updated in `__init__.py` and `pyproject.toml`
- [ ] CHANGELOG.md updated
- [ ] README.md accurate
- [ ] Documentation up to date
- [ ] Examples working
- [ ] Docker images tested
- [ ] Git committed and tagged

## 🔄 Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (1.0.0): Incompatible API changes
- **MINOR** (0.1.0): New functionality, backwards compatible
- **PATCH** (0.0.1): Bug fixes, backwards compatible

Examples:
- `0.1.0` → `0.1.1`: Bug fix
- `0.1.1` → `0.2.0`: New feature
- `0.2.0` → `1.0.0`: Breaking changes

## 🐛 Troubleshooting

### Error: "No module named build"

```bash
# In venv
pip install build twine wheel

# Or use make
make setup-publish
```

### Error: "Invalid credentials"

```bash
# Check ~/.pypirc exists
ls -la ~/.pypirc

# Verify token is correct
# Generate new token at https://pypi.org/manage/account/token/
```

### Error: "File already exists"

```bash
# Version already published
# Bump version number and try again
```

### Error: "Externally managed environment"

```bash
# Use venv
python -m venv venv
source venv/bin/activate
pip install build twine wheel
```

## 📊 Post-Publish Tasks

1. **GitHub Release:**
   ```bash
   # Create release on GitHub
   gh release create v0.1.1 --notes "Release notes"
   ```

2. **Update Documentation:**
   ```bash
   # Update docs if needed
   make docs
   ```

3. **Announce:**
   - Twitter/X
   - Reddit (r/Python)
   - Dev.to blog post
   - Company blog

4. **Monitor:**
   - PyPI downloads: https://pypistats.org/packages/streamware
   - GitHub stars/issues
   - User feedback

## 🔐 Security

### Protect API Tokens

```bash
# Never commit tokens
echo ".pypirc" >> .gitignore

# Use environment variables for CI/CD
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-...
```

### Verify Package

```bash
# Check uploaded package
twine check dist/*

# Verify signatures
gpg --verify dist/streamware-0.1.1.tar.gz.asc
```

## 🤖 Automated Publishing (GitHub Actions)

Create `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install build twine
      
      - name: Build package
        run: python -m build
      
      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: twine upload dist/*
```

## 📚 Resources

- [Python Packaging Guide](https://packaging.python.org/)
- [PyPI Help](https://pypi.org/help/)
- [Twine Documentation](https://twine.readthedocs.io/)
- [Semantic Versioning](https://semver.org/)

---

**Next:** After successful publish, update [README.md](README.md) with installation instructions!
