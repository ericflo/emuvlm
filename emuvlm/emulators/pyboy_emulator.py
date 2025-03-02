"""
PyBoy emulator implementation for Game Boy and Game Boy Color games.
"""
import logging
import os
import numpy as np
from PIL import Image, ImageDraw
from pyboy import PyBoy
try:
    from pyboy.botsupport.constants import WindowEvent
except ImportError:
    from pyboy.utils import WindowEvent

from emuvlm.emulators.base import EmulatorBase
from emuvlm.utils.rom_loader import load_rom

logger = logging.getLogger(__name__)

class PyBoyEmulator(EmulatorBase):
    """
    Emulator implementation using PyBoy for Game Boy and Game Boy Color games.
    """
    
    def __init__(self, rom_path: str):
        """
        Initialize the PyBoy emulator.
        
        Args:
            rom_path: Path to the Game Boy ROM file or ZIP archive
        """
        logger.info(f"Initializing PyBoy emulator with ROM: {rom_path}")
        
        # Handle ROM loading (extract from ZIP if needed)
        actual_rom_path = load_rom(rom_path)
        logger.info(f"Using ROM file: {actual_rom_path}")
        
        # PyBoy instance initialization - use SDL2 instead of headless for better rendering
        # Use a classic Game Boy color palette (light green)
        gb_classic_palette = (0xE0F8D0, 0x88C070, 0x346856, 0x081820)
        
        # Check if this is a Zelda ROM based on filename
        is_zelda_rom = "zelda" in rom_path.lower() or "link" in rom_path.lower()
        
        # Special handling for Zelda ROMs
        if is_zelda_rom:
            logger.info("Detected Zelda ROM - using special initialization settings")
            # For Zelda ROMs, we'll use more conservative settings
            self.emulator = PyBoy(
                actual_rom_path,
                window_type="SDL2",      # Use SDL2 window for better compatibility
                game_wrapper=False,      # Disable game wrapper which might have issues with some ROMs
                debug=False,
                auto_boot=False,         # Don't skip boot for better initialization
                quiet=False,             # Show output for debugging
                color_palette=gb_classic_palette,  # Use classic Game Boy color palette
                use_color_filter=True    # Apply Game Boy color filter to make games more visible
            )
        else:
            # Standard initialization for other games
            self.emulator = PyBoy(
                actual_rom_path,
                window_type="SDL2",      # Use SDL2 window for better compatibility
                game_wrapper=True,       # Enable game wrapper for game-specific features
                debug=False,
                auto_boot=True,          # Skip the boot logo 
                quiet=False,             # Show output for debugging
                color_palette=gb_classic_palette,  # Use classic Game Boy color palette
                use_color_filter=True    # Apply Game Boy color filter to make games more visible
            )
        
        # Start the emulator
        self.emulator.set_emulation_speed(0)  # Run as fast as possible
        
        # Store rom type information for use in other methods
        self.is_zelda_rom = is_zelda_rom
        
        # Simple initialization - just boot the emulator without trying to navigate menus
        logger.info("Starting minimal game initialization sequence...")
        
        # Set up debugging directory for frames (just in case we want to save debug frames)
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        boot_frames_dir = os.path.join(base_dir, "output", "boot_frames")
        os.makedirs(boot_frames_dir, exist_ok=True)
        
        # Initial ticks to let the emulator boot and stabilize
        logger.info("Performing minimal initialization ticks...")
        for i in range(60):
            self.emulator.tick()
        
        # Save a single boot frame for debugging
        boot_frame = self.emulator.screen_image()
        boot_frame.save(os.path.join(boot_frames_dir, "boot_frame.png"))
        logger.info("Game minimally initialized")
        
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
        # Tick the emulator to ensure we have a rendered frame
        # This is critical to ensure the screen is updated
        for _ in range(10):  # More ticks to ensure game state advances
            self.emulator.tick()
        
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
    
    # Removed _initialize_zelda_game method as it's no longer needed with simplified boot process

    def close(self) -> None:
        """
        Close the emulator and clean up resources.
        """
        if hasattr(self, 'emulator') and self.emulator:
            logger.info("Stopping PyBoy emulator")
            self.emulator.stop()
            logger.info("PyBoy emulator stopped")