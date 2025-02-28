"""
Tests for the emulator implementations.
"""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from emuvlm.emulators.base import EmulatorBase
from emuvlm.emulators.pyboy_emulator import PyBoyEmulator
from emuvlm.emulators.mgba_emulator import MGBAEmulator
from emuvlm.emulators.gamegear_emulator import GameGearEmulator


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
    def test_initialization(self, mock_pyboy):
        """Test PyBoyEmulator initialization."""
        # Setup the mock
        mock_instance = MagicMock()
        mock_pyboy.return_value = mock_instance
        
        # Create emulator instance
        rom_path = "test_rom.gb"
        emulator = PyBoyEmulator(rom_path)
        
        # Assertions
        mock_pyboy.assert_called_once()
        assert emulator.emulator is mock_instance
        assert "Up" in emulator.input_mapping
        assert "A" in emulator.input_mapping
    
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
        assert mock_instance.tick.called
        assert mock_instance.screen_image.called
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
    
    @patch('emuvlm.emulators.mgba_emulator.subprocess')
    @patch('emuvlm.emulators.mgba_emulator.requests')
    def test_initialization(self, mock_requests, mock_subprocess):
        """Test MGBAEmulator initialization."""
        # Setup the mocks
        mock_process = MagicMock()
        mock_subprocess.Popen.return_value = mock_process
        
        # Mock the API connection check
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_requests.get.return_value = mock_response
        
        # Create emulator instance
        rom_path = "test_rom.gba"
        emulator = MGBAEmulator(rom_path)
        
        # Assertions
        assert mock_subprocess.Popen.called
        assert mock_requests.get.called
        assert "Up" in emulator.input_mapping
        assert "A" in emulator.input_mapping


class TestGameGearEmulator:
    """Tests for the Game Gear emulator wrapper."""
    
    @patch('emuvlm.emulators.gamegear_emulator.PyBoy')
    def test_initialization(self, mock_pyboy):
        """Test GameGearEmulator initialization."""
        # Setup the mock
        mock_instance = MagicMock()
        mock_pyboy.return_value = mock_instance
        
        # Create emulator instance
        rom_path = "test_rom.gg"
        emulator = GameGearEmulator(rom_path)
        
        # Assertions
        mock_pyboy.assert_called_once()
        assert emulator.emulator is mock_instance
        assert "Up" in emulator.input_mapping
        assert "A" in emulator.input_mapping
        assert "B" in emulator.input_mapping
        assert "Start" in emulator.input_mapping
    
    @patch('emuvlm.emulators.gamegear_emulator.PyBoy')
    def test_get_frame(self, mock_pyboy):
        """Test getting a frame from GameGearEmulator."""
        # Setup the mock
        mock_instance = MagicMock()
        mock_screen = MagicMock()
        mock_instance.screen_image.return_value = mock_screen
        mock_pyboy.return_value = mock_instance
        
        # Create emulator instance and get frame
        emulator = GameGearEmulator("test_rom.gg")
        frame = emulator.get_frame()
        
        # Assertions
        assert mock_instance.tick.called
        assert mock_instance.screen_image.called
        assert frame is mock_screen
    
    @patch('emuvlm.emulators.gamegear_emulator.PyBoy')
    def test_send_input(self, mock_pyboy):
        """Test sending input to GameGearEmulator."""
        # Setup the mock
        mock_instance = MagicMock()
        mock_pyboy.return_value = mock_instance
        
        # Create emulator instance and send input
        emulator = GameGearEmulator("test_rom.gg")
        emulator.send_input("A")
        
        # Check that the appropriate methods were called on the PyBoy instance
        assert mock_instance.send_input.called
    
    @patch('emuvlm.emulators.gamegear_emulator.PyBoy')
    def test_close(self, mock_pyboy):
        """Test closing the GameGearEmulator."""
        # Setup the mock
        mock_instance = MagicMock()
        mock_pyboy.return_value = mock_instance
        
        # Create emulator instance and close it
        emulator = GameGearEmulator("test_rom.gg")
        emulator.close()
        
        # Check that stop was called
        assert mock_instance.stop.called