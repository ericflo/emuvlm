"""
PyBoy emulator interface for Game Boy / Game Boy Color games.
"""
import logging
import os
from PIL import Image
from typing import Dict, Optional

from .base import GameEmulator

logger = logging.getLogger(__name__)

class PyBoyEmulator(GameEmulator):
    """
    Implementation of GameEmulator for PyBoy.
    
    PyBoy is a Game Boy emulator written in Python that offers a Python API
    for direct control of Game Boy / Game Boy Color games.
    """
    
    def __init__(self, rom_path: str, headless: bool = False):
        """
        Initialize PyBoy emulator with the specified ROM.
        
        Args:
            rom_path: Path to the Game Boy ROM file
            headless: Whether to run without a visible window
        """
        # Import PyBoy here to delay the import until it's needed
        try:
            from pyboy import PyBoy
        except ImportError:
            logger.error("PyBoy is not installed. Install it with: pip install pyboy")
            raise
            
        # Check if ROM file exists
        if not os.path.exists(rom_path):
            raise FileNotFoundError(f"ROM file not found: {rom_path}")
            
        # Initialize PyBoy
        window_type = "headless" if headless else "SDL2"
        try:
            self.pyboy = PyBoy(rom_path, window_type=window_type)
            self.pyboy.set_emulation_speed(0)  # Run as fast as possible
        except Exception as e:
            logger.error(f"Failed to initialize PyBoy: {e}")
            # SDL2 issues on macOS might be common
            if "SDL2" in str(e) and window_type == "SDL2":
                logger.error("SDL2 error detected. Make sure SDL2 is installed (brew install sdl2)")
            raise
            
        # Map of button names to PyBoy button names
        self.button_map = {
            "A": "A",
            "B": "B",
            "Up": "UP",
            "Down": "DOWN",
            "Left": "LEFT", 
            "Right": "RIGHT",
            "Start": "START",
            "Select": "SELECT"
        }
        
        # Start the game
        self.pyboy.tick()
        logger.info(f"PyBoy emulator initialized with ROM: {rom_path}")
    
    def get_frame(self) -> Image.Image:
        """
        Capture the current screen from PyBoy.
        
        Returns:
            PIL.Image: The current game frame
        """
        return self.pyboy.screen_image()
    
    def send_input(self, action: str) -> bool:
        """
        Send an input action to PyBoy.
        
        Args:
            action: String representing the action (e.g., "A", "Up", etc.)
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Normalize action (case-insensitive lookup)
        action = action.capitalize()
        
        # Map to PyBoy button if necessary
        pyboy_button = self.button_map.get(action)
        if not pyboy_button:
            logger.warning(f"Unknown button: {action}")
            return False
            
        # Press and release the button (single press)
        try:
            self.pyboy.button(pyboy_button)
            self.pyboy.tick()  # Advance at least one frame to process input
            return True
        except Exception as e:
            logger.error(f"Error sending input to PyBoy: {e}")
            return False
    
    def close(self) -> None:
        """
        Clean up and close the PyBoy emulator.
        """
        if hasattr(self, 'pyboy'):
            self.pyboy.stop()
            logger.info("PyBoy emulator closed")