# Streamware Makefile

.PHONY: help install dev test clean build publish docs setup-publish \
        env-detect env-setup env-ollama env-llama env-start env-stop \
        env-download env-benchmark usb-prepare usb-build iso-build

# Autodetection
HAS_AMD_GPU := $(shell [ -e /dev/kfd ] && echo 1 || echo 0)
HAS_ROCM := $(shell command -v rocm-smi >/dev/null 2>&1 && echo 1 || echo 0)
HAS_PODMAN := $(shell command -v podman >/dev/null 2>&1 && echo 1 || echo 0)
HAS_DOCKER := $(shell command -v docker >/dev/null 2>&1 && echo 1 || echo 0)
ENV_DIR := environments

help:
	@echo "Streamware - Modern Python stream processing framework"
	@echo ""
	@echo "Available targets:"
	@echo "  install       - Install streamware and dependencies"
	@echo "  dev           - Install in development mode with all extras"
	@echo "  test          - Run tests"
	@echo "  clean         - Clean build artifacts"
	@echo "  setup-publish - Install build tools (build, twine)"
	@echo "  build         - Build distribution packages"
	@echo "  publish-test  - Publish to TestPyPI"
	@echo "  publish       - Publish to PyPI"
	@echo "  docs          - Build documentation"
	@echo "  docker-build  - Build Docker image"
	@echo "  docker-run    - Run Docker container"
	@echo "  dev-all       - Start all Docker services"
	@echo ""
	@echo "LLM Environment targets (UM790 Pro / AMD 780M):"
	@echo "  env-detect    - Detect GPU and container runtime"
	@echo "  env-setup     - Setup ROCm on host (requires sudo)"
	@echo "  env-download  - Download models for offline use"
	@echo "  env-ollama    - Start Ollama + Open-WebUI"
	@echo "  env-llama     - Start llama.cpp server"
	@echo "  env-start     - Auto-detect and start best environment"
	@echo "  env-stop      - Stop all LLM services"
	@echo "  env-benchmark - Run llama.cpp benchmark"
	@echo "  usb-prepare   - Prepare offline USB resources"
	@echo "  usb-build     - Build bootable USB (requires sudo)"
	@echo "  iso-build     - Build bootable ISO for Balena Etcher"

install:
	pip install -e .

dev:
	pip install -e ".[all]"
	pip install build twine wheel
	pre-commit install || true

setup-publish:
	@echo "Installing build tools..."
	pip install build twine wheel
	@echo "✓ Build tools installed"

test:
	pytest tests/ -v --cov=streamware --cov-report=term-missing

test-docker:
	./test_docker_install.sh

clean:
	rm -rf build/ dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

version-bump:
	@echo "Bumping patch version in pyproject.toml..."
	@python3 -c "import re,sys; p='pyproject.toml'; s=open(p,'r',encoding='utf-8').read(); m=re.search(r'(?m)^version\\s*=\\s*\"(\\d+)\\.(\\d+)\\.(\\d+)\"', s);\
	import sys as _s;\
	[(_s.stderr.write('Could not find version in pyproject.toml\n'), _s.exit(1)) for _ in []] if m else (_s.stderr.write('Could not find version in pyproject.toml\n') or _s.exit(1));\
	a,b,c=map(int,m.groups()); new=f'{a}.{b}.{c+1}'; s=re.sub(r'(?m)^version\\s*=\\s*\".*?\"', f'version = \"{new}\"', s, 1); open(p,'w',encoding='utf-8').write(s); print(new)"

build: clean
	python3 -m build

publish-test: version-bump build
	python3 -m twine upload --repository testpypi dist/*

publish: version-bump build
	python3 -m twine upload dist/*

docs:
	# Placeholder for documentation build
	@echo "Documentation build not yet configured"

lint:
	flake8 streamware/
	mypy streamware/
	black --check streamware/

format:
	black streamware/
	isort streamware/

run-example:
	python examples.py

# Docker targets
docker-build:
	docker build -t streamware:latest .

docker-run:
	docker run -it --rm streamware:latest

# Development shortcuts
dev-kafka:
	docker-compose up -d zookeeper kafka

dev-rabbitmq:
	docker-compose up -d rabbitmq

dev-postgres:
	docker-compose up -d postgres

dev-all:
	docker-compose up -d

# =============================================================================
# LLM Environment targets (UM790 Pro / AMD Radeon 780M)
# =============================================================================

env-detect:
	@echo "=========================================="
	@echo "LLM Environment Detection"
	@echo "=========================================="
	@echo ""
	@echo "Hardware:"
ifeq ($(HAS_AMD_GPU),1)
	@echo "  ✓ AMD GPU detected (/dev/kfd)"
else
	@echo "  ✗ AMD GPU not found"
endif
ifeq ($(HAS_ROCM),1)
	@echo "  ✓ ROCm installed"
	@rocm-smi --showproductname 2>/dev/null || echo "    (unable to query GPU)"
else
	@echo "  ✗ ROCm not installed"
endif
	@echo ""
	@echo "Container Runtime:"
ifeq ($(HAS_PODMAN),1)
	@echo "  ✓ Podman available"
else
	@echo "  ✗ Podman not found"
endif
ifeq ($(HAS_DOCKER),1)
	@echo "  ✓ Docker available"
else
	@echo "  ✗ Docker not found"
endif
	@echo ""
	@echo "Environments:"
	@[ -d $(ENV_DIR)/ollama-webui ] && echo "  ✓ ollama-webui" || echo "  ✗ ollama-webui"
	@[ -d $(ENV_DIR)/llama-cpp-rocm ] && echo "  ✓ llama-cpp-rocm" || echo "  ✗ llama-cpp-rocm"
	@echo ""
ifeq ($(HAS_AMD_GPU),1)
ifeq ($(HAS_ROCM),1)
	@echo "Status: Ready for GPU acceleration"
else
	@echo "Status: Run 'make env-setup' to install ROCm"
endif
else
	@echo "Status: CPU-only mode (no AMD GPU)"
endif

env-setup:
	@echo "Setting up ROCm for AMD GPU..."
	@[ -f $(ENV_DIR)/ollama-webui/setup-host.sh ] && sudo $(ENV_DIR)/ollama-webui/setup-host.sh || echo "Setup script not found"

env-download:
	@echo "Downloading models for offline use..."
	@echo ""
	@echo "[1/2] Ollama models..."
	@[ -f $(ENV_DIR)/ollama-webui/download-models.sh ] && cd $(ENV_DIR)/ollama-webui && ./download-models.sh
	@echo ""
	@echo "[2/2] GGUF models for llama.cpp..."
	@[ -f $(ENV_DIR)/llama-cpp-rocm/download-models.sh ] && cd $(ENV_DIR)/llama-cpp-rocm && ./download-models.sh

env-ollama:
	@echo "Starting Ollama + Open-WebUI..."
	@cd $(ENV_DIR)/ollama-webui && ./start.sh
	@echo ""
	@echo "Open: http://localhost:3000"

env-llama:
	@echo "Starting llama.cpp server..."
	@cd $(ENV_DIR)/llama-cpp-rocm && ./start.sh
	@echo ""
	@echo "API: http://localhost:8080"

env-start: env-detect
	@echo ""
	@echo "Auto-starting best available environment..."
ifeq ($(HAS_AMD_GPU),1)
	@if [ -d $(ENV_DIR)/ollama-webui/models ] && [ "$$(ls -A $(ENV_DIR)/ollama-webui/models 2>/dev/null)" ]; then \
		echo "Starting Ollama (models found)..."; \
		cd $(ENV_DIR)/ollama-webui && ./start.sh; \
	elif [ -d $(ENV_DIR)/llama-cpp-rocm/models ] && [ "$$(ls -A $(ENV_DIR)/llama-cpp-rocm/models 2>/dev/null)" ]; then \
		echo "Starting llama.cpp (models found)..."; \
		cd $(ENV_DIR)/llama-cpp-rocm && ./start.sh; \
	else \
		echo "No models found. Run 'make env-download' first."; \
		exit 1; \
	fi
else
	@echo "No AMD GPU detected. Starting Ollama in CPU mode..."
	@cd $(ENV_DIR)/ollama-webui && ./start.sh
endif
	@echo ""
	@echo "Environment started. Open http://localhost:3000"

env-stop:
	@echo "Stopping all LLM services..."
	@cd $(ENV_DIR)/ollama-webui && ./stop.sh 2>/dev/null || true
	@cd $(ENV_DIR)/llama-cpp-rocm && ./stop.sh 2>/dev/null || true
	@echo "All services stopped."

env-benchmark:
	@echo "Running llama.cpp benchmark..."
	@cd $(ENV_DIR)/llama-cpp-rocm && ./benchmark.sh

usb-prepare:
	@echo "Preparing offline USB resources..."
	@cd $(ENV_DIR)/usb-builder && ./prepare-offline.sh

usb-build:
	@echo "Building bootable USB..."
	@echo "Usage: sudo make usb-build USB=/dev/sdX"
	@[ -n "$(USB)" ] && cd $(ENV_DIR)/usb-builder && sudo ./build-usb.sh $(USB) || echo "Specify USB device: make usb-build USB=/dev/sdX"

iso-build:
	@echo "Building bootable ISO for Balena Etcher..."
	@echo "Output: $(ENV_DIR)/usb-builder/output/llm-station-um790pro.iso"
	@cd $(ENV_DIR)/usb-builder && sudo ./build-iso.sh
