"""
Tests for the emulator implementations.
"""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from emuvlm.emulators.base import EmulatorBase
from emuvlm.emulators.pyboy_emulator import PyBoyEmulator
from emuvlm.emulators.mgba_emulator import MGBAEmulator


class TestBaseEmulator:
    """Tests for the base emulator class."""
    
    def test_abstract_methods(self):
        """Test that EmulatorBase requires implementation of abstract methods."""
        with pytest.raises(TypeError):
            EmulatorBase("dummy_rom.gbc")
    
    def test_valid_input(self):
        """Test validation of input actions."""
        # Create a concrete subclass for testing
        class TestEmulator(EmulatorBase):
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
    @patch('emuvlm.emulators.pyboy_emulator.load_rom')
    def test_initialization(self, mock_load_rom, mock_pyboy):
        """Test PyBoyEmulator initialization."""
        # Setup the mocks
        mock_instance = MagicMock()
        mock_pyboy.return_value = mock_instance
        mock_load_rom.return_value = "loaded_test_rom.gb"
        
        # Create emulator instance
        rom_path = "test_rom.gb"
        emulator = PyBoyEmulator(rom_path)
        
        # Assertions
        mock_load_rom.assert_called_once_with(rom_path)
        mock_pyboy.assert_called_once()
        assert emulator.emulator is mock_instance
        assert "Up" in emulator.input_mapping
        assert "A" in emulator.input_mapping
    
    @patch('emuvlm.emulators.pyboy_emulator.PyBoy')
    @patch('emuvlm.emulators.pyboy_emulator.load_rom')
    def test_get_frame(self, mock_load_rom, mock_pyboy):
        """Test getting a frame from PyBoyEmulator."""
        # Setup the mocks
        mock_instance = MagicMock()
        mock_screen = MagicMock()
        mock_instance.screen_image.return_value = mock_screen
        mock_pyboy.return_value = mock_instance
        mock_load_rom.return_value = "loaded_test_rom.gb"
        
        # Create emulator instance and get frame
        emulator = PyBoyEmulator("test_rom.gb")
        frame = emulator.get_frame()
        
        # Assertions
        assert mock_instance.tick.called
        assert mock_instance.screen_image.called
        assert frame is mock_screen
    
    @patch('emuvlm.emulators.pyboy_emulator.PyBoy')
    @patch('emuvlm.emulators.pyboy_emulator.load_rom')
    def test_send_input(self, mock_load_rom, mock_pyboy):
        """Test sending input to PyBoyEmulator."""
        # Setup the mocks
        mock_instance = MagicMock()
        mock_pyboy.return_value = mock_instance
        mock_load_rom.return_value = "loaded_test_rom.gb"
        
        # Create emulator instance and send input
        emulator = PyBoyEmulator("test_rom.gb")
        emulator.send_input("A")
        
        # Check that the appropriate methods were called on the PyBoy instance
        assert mock_instance.send_input.called


class TestMGBAEmulator:
    """Tests for the mGBA emulator wrapper."""
    
    @patch('emuvlm.emulators.mgba_emulator.subprocess')
    @patch('emuvlm.emulators.mgba_emulator.requests')
    @patch('emuvlm.emulators.mgba_emulator.load_rom')
    def test_initialization(self, mock_load_rom, mock_requests, mock_subprocess):
        """Test MGBAEmulator initialization."""
        # Setup the mocks
        mock_process = MagicMock()
        mock_subprocess.Popen.return_value = mock_process
        mock_load_rom.return_value = "loaded_test_rom.gba"
        
        # Mock the API connection check
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_requests.get.return_value = mock_response
        
        # Create emulator instance
        rom_path = "test_rom.gba"
        emulator = MGBAEmulator(rom_path)
        
        # Assertions
        mock_load_rom.assert_called_once_with(rom_path)
        assert mock_subprocess.Popen.called
        assert mock_requests.get.called
        assert "Up" in emulator.input_mapping
        assert "A" in emulator.input_mapping


