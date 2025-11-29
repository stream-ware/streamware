# Streamware 0.2.0 - Refactoring & Architecture

**Version:** 0.2.0  
**Date:** November 2025  
**Status:** Beta

## 📋 Menu
- [Overview](#overview)
- [New Components](#new-components)
- [Architecture Changes](#architecture-changes)
- [Breaking Changes](#breaking-changes)
- [Migration Guide](#migration-guide)
- [Future Plans](#future-plans)

---

## 🎯 Overview

Streamware 0.2.0 introduces major improvements focused on:
- **Auto-installation** - Dependencies install on-the-fly
- **Template system** - Quick project scaffolding
- **Registry** - Centralized resource management
- **Standardization** - Unified patterns across components

## 🆕 New Components

### 1. Setup Component (`setup.py`)
**Purpose:** Auto-install dependencies and manage environments

**Features:**
- ✅ Check installed dependencies
- ✅ Install Python packages on-the-fly
- ✅ Install system packages (apt, brew)
- ✅ Setup Ollama and pull models
- ✅ Docker environment setup
- ✅ Component-specific dependency resolution

**Usage:**
```bash
# Check dependencies
sq setup check --packages opencv-python,numpy

# Install Python packages
sq setup install --packages ultralytics

# Install all deps for component
sq setup all --component video

# Setup Ollama
sq setup ollama --model qwen2.5:14b
```

**API:**
```python
from streamware.components.setup import auto_install, check_deps

# Auto-install all deps for video component
auto_install("video")

# Check if packages are installed
result = check_deps(["opencv-python", "numpy"])
```

### 2. Template Component (`template.py`)
**Purpose:** Generate projects from templates

**Templates:**
- `video-captioning` - RTSP + YOLO + LLM + Web
- `text2streamware` - Natural language to commands
- `api-pipeline` - HTTP + Transform + Database
- `monitoring` - Health checks + Alerts

**Usage:**
```bash
# List templates
sq template list

# Generate project
sq template generate --name video-captioning --output ./my-project

# Template info
sq template info --name video-captioning
```

**API:**
```python
from streamware.components.template import generate_project

# Generate project
generate_project("video-captioning", output="./my-project")
```

### 3. Registry Component (`registry.py`)
**Purpose:** Centralized resource registry

**Resources:**
- Components - Definitions and metadata
- Models - AI model configurations
- Templates - Project templates
- Pipelines - Reusable flows
- Configs - Configuration presets

**Usage:**
```bash
# List components
sq registry list --type component

# Lookup model
sq registry lookup --type model --name qwen2.5:14b

# Register custom resource
sq registry register --type pipeline --name my-pipeline
```

**API:**
```python
from streamware.components.registry import lookup_component, list_models

# Lookup component
comp = lookup_component("video")

# List models
models = list_models()
```

## 🏗️ Architecture Changes

### Before (0.1.0)
```
streamware/
├── components/
│   ├── http.py
│   ├── ssh.py
│   └── llm.py
└── quick_cli.py
```

Manual dependency installation, no templates, scattered configuration.

### After (0.2.0)
```
streamware/
├── components/
│   ├── http.py
│   ├── ssh.py
│   ├── llm.py
│   ├── setup.py      ← NEW: Auto-install
│   ├── template.py   ← NEW: Project generation
│   └── registry.py   ← NEW: Resource registry
├── quick_cli.py       ← Enhanced with new commands
└── .streamware/
    └── registry.json  ← NEW: Local registry
```

### Component Standardization

All components now follow consistent patterns:

```python
"""
Component Name

Description of what it does.

# Menu:
- [Usage](#usage)
- [Examples](#examples)
- [API](#api)
"""

from __future__ import annotations
from ..core import Component, register

@register("scheme")
class MyComponent(Component):
    """
    Component description
    
    Operations:
    - operation1: Description
    - operation2: Description
    
    URI Examples:
        scheme://operation1?param=value
        scheme://operation2?param=value
    """
    
    input_mime = "*/*"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        # Initialize
    
    def process(self, data: Any) -> Any:
        # Process logic
        pass

# Quick helpers
def quick_function(args):
    """Quick helper"""
    from ..core import flow
    return flow(uri).run()
```

### Dependency Management

Components now declare dependencies in registry:

```python
COMPONENT_DEPS = {
    "video": {
        "python": ["opencv-python", "numpy", "ultralytics"],
        "system": {
            "apt": ["ffmpeg", "libopencv-dev"],
            "brew": ["opencv", "ffmpeg"],
        },
        "ollama": ["llama3.2:latest"]
    }
}
```

Auto-installation happens transparently:

```python
# Before (0.1.0) - Manual
pip install opencv-python ultralytics
apt-get install ffmpeg
ollama pull llama3.2

# After (0.2.0) - Automatic
sq setup all --component video
# or
from streamware.components.setup import auto_install
auto_install("video")
```

## 🔄 Breaking Changes

### 1. Version Bump
- **Old:** 0.1.0
- **New:** 0.2.0

### 2. License Classifier
- **Removed:** Deprecated `License :: OSI Approved :: Apache Software License`
- **Reason:** Setuptools deprecation warning
- **Impact:** None - license still Apache-2.0 in `license = {text = "Apache-2.0"}`

### 3. Development Status
- **Old:** Alpha (3)
- **New:** Beta (4)
- **Reason:** Feature completeness and stability

### 4. Component Registration

No breaking changes to existing components, but new best practices:

```python
# Old (still works)
@register("myscheme")
class MyComponent(Component):
    pass

# New (recommended)
@register("myscheme")
@register("myalias")  # Multiple schemes
class MyComponent(Component):
    """With detailed docstring"""
    pass
```

## 📖 Migration Guide

### From 0.1.0 to 0.2.0

#### 1. Update Installation

```bash
# Uninstall old version
pip uninstall streamware

# Install new version
pip install streamware==0.2.0
```

#### 2. Use Auto-Install

Replace manual installation:

```bash
# Before
pip install opencv-python ultralytics
apt-get install ffmpeg

# After
sq setup all --component video
```

#### 3. Use Templates

Instead of copying examples:

```bash
# Before
cp -r examples/video-captioning my-project

# After
sq template generate --name video-captioning --output my-project
```

#### 4. Use Registry

Instead of hardcoded configs:

```bash
# Before
# Manual configuration

# After
sq registry lookup --type model --name qwen2.5:14b
```

## 🚀 New Quick Start

### 1. Install Streamware
```bash
pip install streamware==0.2.0
```

### 2. Generate Project
```bash
sq template generate --name video-captioning --output my-project
cd my-project
```

### 3. Auto-Install Dependencies
```bash
sq setup all --component video
```

### 4. Run
```bash
python video_captioning_complete.py
```

## 🔮 Future Plans

### Version 0.3.0 (Planned)
- **Plugin System** - External component loading
- **Cloud Registry** - Share components globally
- **Visual Builder** - GUI for pipeline creation
- **Performance** - Async/await throughout
- **Testing** - 90%+ code coverage

### Version 0.4.0 (Planned)
- **Kubernetes Operators** - Native K8s integration
- **Monitoring** - Built-in metrics and tracing
- **Security** - RBAC and secrets management
- **Multi-tenancy** - Resource isolation

### Version 1.0.0 (Goal)
- **Production Ready** - Battle-tested
- **Documentation** - Complete API docs
- **Examples** - 100+ real-world examples
- **Community** - Active contributors

## 📊 Component Matrix

| Component | Status | Auto-Install | Template | Registry |
|-----------|--------|--------------|----------|----------|
| **http** | ✅ Stable | ✅ | - | ✅ |
| **file** | ✅ Stable | ✅ | - | ✅ |
| **ssh** | ✅ Stable | ✅ | - | ✅ |
| **postgres** | ✅ Stable | ✅ | - | ✅ |
| **kafka** | ✅ Stable | ✅ | - | ✅ |
| **llm** | ✅ Beta | ✅ | - | ✅ |
| **video** | ✅ Beta | ✅ | ✅ | ✅ |
| **text2streamware** | ✅ Beta | ✅ | ✅ | ✅ |
| **deploy** | ✅ Beta | ✅ | - | ✅ |
| **setup** | 🆕 New | N/A | - | ✅ |
| **template** | 🆕 New | N/A | N/A | ✅ |
| **registry** | 🆕 New | N/A | - | N/A |

## 🎯 Suggested Components for Next Release

### 1. **Monitoring Component**
Health checks, metrics, alerts

```bash
sq monitor health --url http://api.com --interval 60 --alert slack
```

### 2. **Cache Component**
Redis, Memcached integration

```bash
sq cache set key value --ttl 3600
sq cache get key
```

### 3. **Queue Component**
Unified queue interface (Kafka, RabbitMQ, SQS)

```bash
sq queue push job-queue '{"task":"process"}' --provider rabbitmq
```

### 4. **Workflow Component**
Multi-step workflow orchestration

```bash
sq workflow run deployment.yaml --parallel
```

### 5. **Secret Component**
Secrets management (Vault, AWS Secrets Manager)

```bash
sq secret get DB_PASSWORD --provider vault
```

## 💡 Simplification Opportunities

### 1. Unified CLI Structure
```bash
# Current (multiple patterns)
sq deploy k8s --apply --file deployment.yaml
sq setup all --component video
sq template generate --name video-captioning

# Proposed (consistent)
sq deploy apply k8s deployment.yaml
sq setup install video
sq template create video-captioning
```

### 2. Smart Defaults
```bash
# Current (verbose)
sq deploy k8s --apply --file deployment.yaml --namespace production

# Proposed (smart defaults)
sq deploy deployment.yaml
# Detects: K8s manifest, applies to default namespace
```

### 3. Component Aliases
```bash
# Current
sq text2streamware://convert?prompt=upload file

# Proposed
sq ai "upload file"  # Auto-detects best component
```

### 4. Pipeline Chaining
```bash
# Current (multiple commands)
sq get api.com/data --json > data.json
sq file data.json --transform --save output.csv
sq postgres "INSERT INTO table ..."

# Proposed (chaining)
sq get api.com/data | sq transform json2csv | sq postgres insert table
```

## 📝 Documentation Structure

Each component should have:

1. **Inline Menu** (top of file)
```python
"""
# Menu:
- [Overview](#overview)
- [Installation](#installation)
- [Usage](#usage)
- [Examples](#examples)
- [API Reference](#api-reference)
"""
```

2. **URI Examples** in docstring
3. **Quick helpers** at end of file
4. **Separate markdown docs** in `docs/`

---

**Questions? Issues?**
- GitHub: https://github.com/softreck/streamware
- Email: info@softreck.com

**Happy Streaming! 🚀**
