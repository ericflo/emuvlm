"""
PyBoy emulator implementation for Game Boy and Game Boy Color games.
"""
import logging
from PIL import Image
from pyboy import PyBoy
try:
    from pyboy.botsupport.constants import WindowEvent
except ImportError:
    from pyboy.utils import WindowEvent

from emuvlm.emulators.base import EmulatorBase

logger = logging.getLogger(__name__)

class PyBoyEmulator(EmulatorBase):
    """
    Emulator implementation using PyBoy for Game Boy and Game Boy Color games.
    """
    
    def __init__(self, rom_path: str):
        """
        Initialize the PyBoy emulator.
        
        Args:
            rom_path: Path to the Game Boy ROM file
        """
        logger.info(f"Initializing PyBoy emulator with ROM: {rom_path}")
        
        # PyBoy instance initialization
        self.emulator = PyBoy(
            rom_path,
            window_type="headless",  # Use headless mode for better performance
            game_wrapper=True,       # Enable game wrapper for game-specific features
            debug=False
        )
        
        # Start the emulator
        self.emulator.set_emulation_speed(0)  # Run as fast as possible
        
        # Define input mapping from action names to PyBoy events
        self.input_mapping = {
            "A": WindowEvent.PRESS_BUTTON_A,
            "B": WindowEvent.PRESS_BUTTON_B,
            "Up": WindowEvent.PRESS_ARROW_UP,
            "Down": WindowEvent.PRESS_ARROW_DOWN,
            "Left": WindowEvent.PRESS_ARROW_LEFT,
            "Right": WindowEvent.PRESS_ARROW_RIGHT,
            "Start": WindowEvent.PRESS_BUTTON_START,
            "Select": WindowEvent.PRESS_BUTTON_SELECT
        }
        
        # Corresponding release events
        self.release_mapping = {
            "A": WindowEvent.RELEASE_BUTTON_A,
            "B": WindowEvent.RELEASE_BUTTON_B,
            "Up": WindowEvent.RELEASE_ARROW_UP,
            "Down": WindowEvent.RELEASE_ARROW_DOWN,
            "Left": WindowEvent.RELEASE_ARROW_LEFT,
            "Right": WindowEvent.RELEASE_ARROW_RIGHT,
            "Start": WindowEvent.RELEASE_BUTTON_START,
            "Select": WindowEvent.RELEASE_BUTTON_SELECT
        }
        
        logger.info("PyBoy emulator initialized successfully")
    
    def get_frame(self) -> Image.Image:
        """
        Get the current frame from the emulator.
        
        Returns:
            PIL Image of the current screen
        """
        # Get the screen image from PyBoy
        screen = self.emulator.screen_image()
        
        # PyBoy returns a PIL Image already
        return screen
    
    def send_input(self, action: str) -> None:
        """
        Send an input action to the emulator.
        
        Args:
            action: Action name (e.g., "A", "Up", "Start")
        """
        if action in self.input_mapping:
            # Send the press event
            press_event = self.input_mapping[action]
            self.emulator.send_input(press_event)
            
            # Small tick to register the press
            self.emulator.tick()
            
            # Send the release event
            release_event = self.release_mapping[action]
            self.emulator.send_input(release_event)
            
            # Another tick to process the input
            self.emulator.tick()
            
            logger.debug(f"Sent input action: {action}")
        else:
            logger.warning(f"Unsupported action for PyBoy: {action}")
    
    def close(self) -> None:
        """
        Close the emulator and clean up resources.
        """
        if hasattr(self, 'emulator') and self.emulator:
            logger.info("Stopping PyBoy emulator")
            self.emulator.stop()
            logger.info("PyBoy emulator stopped")