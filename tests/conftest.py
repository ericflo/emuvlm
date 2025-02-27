"""
Pytest configuration for the emuvlm test suite.
"""
import os
import pytest
from pathlib import Path
from PIL import Image


@pytest.fixture
def test_data_dir():
    """Return the path to the test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture
def sample_frame():
    """Return a sample game frame for testing."""
    # Create a simple colored frame for testing
    return Image.new('RGB', (160, 144), color='black')


@pytest.fixture
def mock_model_response():
    """Mock response from the LLM model API."""
    return {
        "choices": [
            {
                "message": {
                    "content": "A"
                }
            }
        ]
    }