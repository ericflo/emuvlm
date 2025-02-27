"""
Tests for the emulator implementations.
"""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from emuvlm.emulators.base import BaseEmulator
from emuvlm.emulators.pyboy_emulator import PyBoyEmulator
from emuvlm.emulators.mgba_emulator import MGBAEmulator


class TestBaseEmulator:
    """Tests for the base emulator class."""
    
    def test_abstract_methods(self):
        """Test that BaseEmulator requires implementation of abstract methods."""
        with pytest.raises(TypeError):
            BaseEmulator("dummy_rom.gbc")
    
    def test_valid_input(self):
        """Test validation of input actions."""
        # Create a concrete subclass for testing
        class TestEmulator(BaseEmulator):
            def __init__(self, rom_path):
                self.rom_path = rom_path
                self.valid_inputs = ["Up", "Down", "Left", "Right", "A", "B"]
            
            def get_frame(self):
                pass
                
            def send_input(self, action):
                pass
                
            def close(self):
                pass
        
        emulator = TestEmulator("dummy_rom.gbc")
        assert hasattr(emulator, "valid_inputs")
        assert "Up" in emulator.valid_inputs
        assert "Select" not in emulator.valid_inputs


class TestPyBoyEmulator:
    """Tests for the PyBoy emulator wrapper."""
    
    @patch('emuvlm.emulators.pyboy_emulator.PyBoy')
    def test_initialization(self, mock_pyboy):
        """Test PyBoyEmulator initialization."""
        # Setup the mock
        mock_instance = MagicMock()
        mock_pyboy.return_value = mock_instance
        
        # Create emulator instance
        rom_path = "test_rom.gb"
        emulator = PyBoyEmulator(rom_path)
        
        # Assertions
        mock_pyboy.assert_called_once_with(rom_path)
        assert emulator.emulator is mock_instance
        assert "Up" in emulator.valid_inputs
        assert "A" in emulator.valid_inputs
    
    @patch('emuvlm.emulators.pyboy_emulator.PyBoy')
    def test_get_frame(self, mock_pyboy):
        """Test getting a frame from PyBoyEmulator."""
        # Setup the mock
        mock_instance = MagicMock()
        mock_screen = MagicMock()
        mock_instance.screen_image.return_value = mock_screen
        mock_pyboy.return_value = mock_instance
        
        # Create emulator instance and get frame
        emulator = PyBoyEmulator("test_rom.gb")
        frame = emulator.get_frame()
        
        # Assertions
        mock_instance.tick.assert_called_once()
        mock_instance.screen_image.assert_called_once()
        assert frame is mock_screen
    
    @patch('emuvlm.emulators.pyboy_emulator.PyBoy')
    def test_send_input(self, mock_pyboy):
        """Test sending input to PyBoyEmulator."""
        # Setup the mock
        mock_instance = MagicMock()
        mock_pyboy.return_value = mock_instance
        
        # Create emulator instance and send input
        emulator = PyBoyEmulator("test_rom.gb")
        emulator.send_input("A")
        
        # Check that the appropriate methods were called on the PyBoy instance
        assert mock_instance.send_input.called


class TestMGBAEmulator:
    """Tests for the mGBA emulator wrapper."""
    
    @patch('emuvlm.emulators.mgba_emulator.mgba')
    @patch('emuvlm.emulators.mgba_emulator.core')
    def test_initialization(self, mock_core, mock_mgba):
        """Test MGBAEmulator initialization."""
        # Setup the mocks
        mock_core_instance = MagicMock()
        mock_core.Core.return_value = mock_core_instance
        
        # Create emulator instance
        rom_path = "test_rom.gba"
        emulator = MGBAEmulator(rom_path)
        
        # Assertions
        assert mock_core.Core.called
        assert mock_core_instance.load_file.called_with(rom_path)
        assert emulator.core is mock_core_instance
        assert "Up" in emulator.valid_inputs
        assert "A" in emulator.valid_inputs