"""
Pytest configuration for the emuvlm test suite.
Configure fixtures for tests in both tests/ directory and emuvlm/ module test files.
"""
import os
import pytest
import tempfile
import shutil
from pathlib import Path
from PIL import Image
from unittest.mock import MagicMock
from emuvlm.model.agent import LLMAgent
from emuvlm.emulators.pyboy_emulator import PyBoyEmulator


@pytest.fixture
def emulator():
    """Return a mock emulator for testing."""
    mock_emulator = MagicMock()
    mock_emulator.get_frame.return_value = Image.new('RGB', (160, 144), color='black')
    return mock_emulator


@pytest.fixture
def rom_paths():
    """Return a dictionary of mock ROM paths for testing."""
    return {
        'pyboy': 'roms/gb/test_rom.gb',
        'mgba': 'roms/gba/test_rom.gba',
        'snes9x': 'roms/snes/test_rom.sfc',
        'fceux': 'roms/nes/test_rom.nes',
        'genesis': 'roms/genesis/test_rom.md',
    }


@pytest.fixture
def config_path():
    """Return a path to a temporary config file for testing."""
    temp_dir = tempfile.mkdtemp()
    config_file = os.path.join(temp_dir, 'config.yaml')
    
    with open(config_file, 'w') as f:
        f.write("""
model:
  api_url: http://localhost:8000
  temperature: 0.2
  max_tokens: 100
games:
  test:
    emulator: pyboy
    rom: roms/test_rom.gb
    actions: [Up, Down, Left, Right, A, B, Start, Select]
""")
    
    yield config_file
    shutil.rmtree(temp_dir)


@pytest.fixture
def model_path():
    """Return a mock model path for testing."""
    return 'models/test_model.gguf'


@pytest.fixture
def test_image():
    """Return a path to a test image for model testing."""
    temp_dir = tempfile.mkdtemp()
    image_path = os.path.join(temp_dir, 'test_image.png')
    
    # Create a simple test image
    img = Image.new('RGB', (160, 144), color='black')
    img.save(image_path)
    
    yield image_path
    shutil.rmtree(temp_dir)


@pytest.fixture
def agent():
    """Return a mock LLM agent for testing."""
    model_config = {
        'api_url': 'http://localhost:8000',
        'temperature': 0.2,
        'max_tokens': 100
    }
    valid_actions = ['Up', 'Down', 'Left', 'Right', 'A', 'B', 'Start', 'Select']
    
    # Create a mock agent that doesn't try to connect to a server
    agent = MagicMock(spec=LLMAgent)
    agent.model_config = model_config
    agent.valid_actions = valid_actions
    agent.decide_action.return_value = 'A'
    
    return agent


@pytest.fixture
def image_path():
    """Return a path to a test image."""
    temp_dir = tempfile.mkdtemp()
    image_path = os.path.join(temp_dir, 'test_image.png')
    
    # Create a simple test image
    img = Image.new('RGB', (160, 144), color='black')
    img.save(image_path)
    
    yield image_path
    shutil.rmtree(temp_dir)


@pytest.fixture
def command_name():
    """Return a test command name for CLI testing."""
    return "emuvlm-test"


@pytest.fixture
def entry_point():
    """Return a test entry point for CLI testing."""
    return "emuvlm.cli:main"