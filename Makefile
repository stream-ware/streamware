# Streamware Makefile

.PHONY: help install dev test clean build publish docs setup-publish

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
