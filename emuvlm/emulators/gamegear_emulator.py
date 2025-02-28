"""
Game Gear emulator implementation using PyBoy interface.
"""
import logging
import os
import numpy as np
from PIL import Image, ImageDraw
import atexit

# Reuse PyBoy since both Game Gear and Game Boy are supported by the same backend
from pyboy import PyBoy
try:
    from pyboy.botsupport.constants import WindowEvent
except ImportError:
    from pyboy.utils import WindowEvent

from emuvlm.emulators.base import EmulatorBase

logger = logging.getLogger(__name__)

class GameGearEmulator(EmulatorBase):
    """
    Emulator implementation for Sega Game Gear using PyBoy backend.
    """
    
    def __init__(self, rom_path: str):
        """
        Initialize the Game Gear emulator.
        
        Args:
            rom_path: Path to the Game Gear ROM file
        """
        logger.info(f"Initializing Game Gear emulator with ROM: {rom_path}")
        
        # Use a Game Gear appropriate color palette
        gamegear_palette = (0xE0F8FC, 0x88C8F8, 0x3050F8, 0x181830)
        
        # Initialize PyBoy with appropriate Game Gear settings
        self.emulator = PyBoy(
            rom_path,
            window_type="SDL2",       # Use SDL2 window for better compatibility
            game_wrapper=False,       # Disable game wrapper which isn't optimized for Game Gear
            debug=False,
            auto_boot=True,           # Skip boot process
            quiet=False,              # Show output for debugging
            color_palette=gamegear_palette,  # Use Game Gear color palette
            use_color_filter=True     # Apply color filter to make games more visible
        )
        
        # Ensure emulator is closed on exit
        atexit.register(self.close)
        
        # Set emulation speed
        self.emulator.set_emulation_speed(0)  # Run as fast as possible
        
        # Initial boot sequence
        logger.info("Starting Game Gear initialization sequence...")
        
        # Set up debugging directory for frames
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        boot_frames_dir = os.path.join(base_dir, "output", "boot_frames")
        os.makedirs(boot_frames_dir, exist_ok=True)
        
        # Initial advance to allow the ROM to boot
        for i in range(120):
            self.emulator.tick()
            if i % 60 == 0:
                frame = self.emulator.screen_image()
                frame.save(os.path.join(boot_frames_dir, f"gamegear_init_{i}.png"))
        
        # Standard Game Gear boot sequence
        # Game Gear games typically require START to get past title screens
        for i in range(5):
            # Press START
            self.emulator.send_input(WindowEvent.PRESS_BUTTON_START)
            for _ in range(5): 
                self.emulator.tick()
            self.emulator.send_input(WindowEvent.RELEASE_BUTTON_START)
            
            # Wait and allow game to process
            for _ in range(30):
                self.emulator.tick()
        
        # Additional button sequence (commonly 1 or 2 for Game Gear)
        for i in range(10):
            # Press and release button 1 (A on PyBoy)
            self.emulator.send_input(WindowEvent.PRESS_BUTTON_A)
            for _ in range(5):
                self.emulator.tick()
            self.emulator.send_input(WindowEvent.RELEASE_BUTTON_A)
            
            # Wait
            for _ in range(15):
                self.emulator.tick()
        
        # Final advance to let animations complete
        for i in range(60):
            self.emulator.tick()
        
        # Save the final boot frame
        final_frame = self.emulator.screen_image()
        final_frame.save(os.path.join(boot_frames_dir, "gamegear_final_frame.png"))
        
        # Define input mapping from action names to PyBoy events
        # Game Gear buttons are:
        # - 1 & 2 (primary buttons, mapped to A & B)
        # - Start button
        # - D-pad (4 directions)
        self.input_mapping = {
            "A": WindowEvent.PRESS_BUTTON_A,       # Button 1 on Game Gear
            "B": WindowEvent.PRESS_BUTTON_B,       # Button 2 on Game Gear
            "Up": WindowEvent.PRESS_ARROW_UP,
            "Down": WindowEvent.PRESS_ARROW_DOWN,
            "Left": WindowEvent.PRESS_ARROW_LEFT,
            "Right": WindowEvent.PRESS_ARROW_RIGHT,
            "Start": WindowEvent.PRESS_BUTTON_START
        }
        
        # Corresponding release events
        self.release_mapping = {
            "A": WindowEvent.RELEASE_BUTTON_A,
            "B": WindowEvent.RELEASE_BUTTON_B,
            "Up": WindowEvent.RELEASE_ARROW_UP,
            "Down": WindowEvent.RELEASE_ARROW_DOWN,
            "Left": WindowEvent.RELEASE_ARROW_LEFT,
            "Right": WindowEvent.RELEASE_ARROW_RIGHT,
            "Start": WindowEvent.RELEASE_BUTTON_START
        }
        
        logger.info("Game Gear emulator initialized successfully")
    
    def get_frame(self) -> Image.Image:
        """
        Get the current frame from the emulator.
        
        Returns:
            PIL Image of the current screen
        """
        # Tick the emulator to ensure we have a rendered frame
        for _ in range(10):
            self.emulator.tick()
        
        # Get the screen image from PyBoy
        screen = self.emulator.screen_image()
        
        # Check if the image has some visible content
        img_array = np.array(screen)
        unique_colors = np.unique(img_array.reshape(-1, 3), axis=0)
        num_unique_colors = len(unique_colors)
        color_std = np.std(img_array)
        
        # If there are few unique colors and low variation, mark the frame as potentially blank
        if num_unique_colors < 10 or color_std < 10:
            # Create a new image with a blue border to indicate potentially blank Game Gear frame
            draw = ImageDraw.Draw(screen)
            draw.rectangle([(0, 0), (screen.width-1, screen.height-1)], outline="blue", width=3)
            logger.warning(f"Potentially blank Game Gear frame: {num_unique_colors} unique colors, std: {color_std:.2f}")
        
        # Return frame with Game Gear aspect ratio (typically 4:3)
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
            
            logger.debug(f"Sent Game Gear input action: {action}")
        else:
            logger.warning(f"Unsupported action for Game Gear: {action}")
    
    def close(self) -> None:
        """
        Close the emulator and clean up resources.
        """
        if hasattr(self, 'emulator') and self.emulator:
            logger.info("Stopping Game Gear emulator")
            self.emulator.stop()
            logger.info("Game Gear emulator stopped")