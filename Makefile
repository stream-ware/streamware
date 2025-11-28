# Streamware Makefile

.PHONY: help install dev test clean build publish docs

help:
	@echo "Streamware - Modern Python stream processing framework"
	@echo ""
	@echo "Available targets:"
	@echo "  install    - Install streamware and dependencies"
	@echo "  dev        - Install in development mode with all extras"
	@echo "  test       - Run tests"
	@echo "  clean      - Clean build artifacts"
	@echo "  build      - Build distribution packages"
	@echo "  publish    - Publish to PyPI"
	@echo "  docs       - Build documentation"

install:
	pip install -e .

dev:
	pip install -e ".[all]"
	pre-commit install

test:
	pytest tests/ -v --cov=streamware --cov-report=term-missing

clean:
	rm -rf build/ dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean
	python -m build

publish-test: build
	python -m twine upload --repository testpypi dist/*

publish: build
	python -m twine upload dist/*

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
