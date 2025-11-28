# Streamware Docker Image
# Complete environment with all dependencies for testing

FROM python:3.11-slim

LABEL maintainer="Softreck <info@softreck.com>"
LABEL description="Streamware - Modern Python stream processing framework"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Build tools
    gcc g++ make cmake \
    # Network tools
    curl wget netcat-openbsd \
    # Video processing
    ffmpeg libavcodec-dev libavformat-dev libswscale-dev \
    libopencv-dev python3-opencv \
    # PostgreSQL client
    libpq-dev postgresql-client \
    # Other utilities
    git vim less \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
COPY pyproject.toml .
COPY setup.py .
COPY README.md .

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    # Core dependencies
    pip install -r requirements.txt && \
    # All optional dependencies
    pip install \
    # CurLLM
    ollama playwright beautifulsoup4 lxml \
    # Message brokers
    kafka-python pika \
    # Databases
    psycopg2-binary sqlalchemy \
    # Multimedia
    opencv-python av numpy pillow \
    # Communication
    python-telegram-bot twilio slack-sdk discord.py vonage plivo \
    # Additional tools
    Jinja2 PyYAML jsonpath-ng \
    # Testing
    pytest pytest-asyncio pytest-cov pytest-mock \
    httpx aiohttp \
    # Development
    ipython black flake8

# Install Playwright browsers (for web automation)
RUN playwright install chromium && \
    playwright install-deps chromium

# Copy application code
COPY streamware/ ./streamware/
COPY examples/ ./examples/
COPY docs/ ./docs/
COPY tests/ ./tests/

# Install streamware in development mode
RUN pip install -e .

# Create directories for data
RUN mkdir -p /data /logs /tmp/streamware

# Copy Docker-specific files
COPY docker/ ./docker/

# Expose common ports
EXPOSE 8080 8000 9092 5432 1935

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import streamware; print('OK')" || exit 1

# Default command
CMD ["bash"]
