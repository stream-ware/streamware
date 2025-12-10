"""
Pytest configuration for Streamware tests.

This conftest ensures that tests don't modify the .env file.
"""

import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def mock_config_save():
    """Prevent tests from modifying .env file."""
    with patch('streamware.config.config.save'):
        yield
