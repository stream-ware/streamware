#!/usr/bin/env python
"""
Setup script for Streamware - backwards compatibility with pip < 21.3
"""

from setuptools import setup, find_packages

# Read the contents of README file
from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="streamware",
    version="0.1.0",
    description="Modern stream processing framework for Python with LLM integration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Softreck Team",
    author_email="team@softreck.com",
    url="https://github.com/softreck/streamware",
    project_urls={
        "Documentation": "https://streamware.readthedocs.io",
        "Source": "https://github.com/softreck/streamware",
        "Tracker": "https://github.com/softreck/streamware/issues",
    },
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "aiohttp>=3.9.0",
        "pydantic>=2.0.0",
        "rich>=13.0.0",
        "PyYAML>=6.0",
        "click>=8.1.0",
        "requests>=2.31.0",
        "jinja2>=3.1.0",
        "jsonpath-ng>=1.5.0",
    ],
    extras_require={
        "curllm": ["ollama", "playwright", "beautifulsoup4", "lxml"],
        "kafka": ["kafka-python>=2.0.0"],
        "rabbitmq": ["pika>=1.3.0"],
        "postgres": ["psycopg2-binary>=2.9.0", "sqlalchemy>=2.0.0"],
        "multimedia": ["opencv-python>=4.8.0", "av>=10.0.0", "numpy>=1.24.0"],
        "communication": [
            "python-telegram-bot>=20.0.0",
            "twilio>=8.0.0",
            "slack-sdk>=3.19.0",
            "discord.py>=2.3.0",
            "vonage>=3.3.0",
            "plivo>=4.38.0",
        ],
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "pre-commit>=3.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "streamware=streamware.cli:main",
            "stream-handler=streamware.handler:main",
            "sq=streamware.quick_cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Distributed Computing",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Communications :: Email",
        "Topic :: Communications :: Chat",
    ],
    keywords="stream processing, etl, pipeline, kafka, rabbitmq, llm, automation, communication",
)
