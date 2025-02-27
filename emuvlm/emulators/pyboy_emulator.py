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
                rom_path,
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
                rom_path,
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
        
        # Special game initialization for Zelda vs other games
        if is_zelda_rom:
            logger.info("Starting Zelda-specific initialization sequence...")
            self._initialize_zelda_game()
        else:
            # Standard initialization sequence for other games
            logger.info("Starting game initialization sequence...")
        
        # Game Boot Phase: Set up debugging directory for frames
        boot_frames_dir = "output/boot_frames"
        os.makedirs(boot_frames_dir, exist_ok=True)
        
        # Initial Advance - Wait for ROM to load and initialize
        logger.info("Phase 1: Initial boot...")
        for i in range(120):
            self.emulator.tick()
            if i % 60 == 0:  # Save a debug frame every second
                frame = self.emulator.screen_image()
                frame.save(os.path.join(boot_frames_dir, f"phase1_frame_{i}.png"))
        
        # Actively navigate from title to gameplay through a series of known patterns:
        
        # Pattern 1: Press START repeatedly to get past title screens
        logger.info("Phase 2: Title screen navigation - START button...")
        for i in range(8):
            # Press START
            self.emulator.send_input(WindowEvent.PRESS_BUTTON_START)
            for _ in range(5): 
                self.emulator.tick()
            self.emulator.send_input(WindowEvent.RELEASE_BUTTON_START)
            
            # Wait and check
            for _ in range(30):
                self.emulator.tick()
                
            # Save a debug frame
            if i % 2 == 0:
                frame = self.emulator.screen_image()
                frame.save(os.path.join(boot_frames_dir, f"phase2_start_{i}.png"))
        
        # Pattern 2: A button navigation (for most menu confirmations)
        logger.info("Phase 3: Menu navigation - A button...")
        for i in range(15):
            # Press A
            self.emulator.send_input(WindowEvent.PRESS_BUTTON_A)
            for _ in range(5):
                self.emulator.tick()
            self.emulator.send_input(WindowEvent.RELEASE_BUTTON_A)
            
            # Wait for menu transitions
            for _ in range(20):
                self.emulator.tick()
                
            # Every few tries, save a frame
            if i % 3 == 0:
                frame = self.emulator.screen_image()
                frame.save(os.path.join(boot_frames_dir, f"phase3_a_{i}.png"))
        
        # Pattern 3: Try a standard RPG "New Game" selection pattern
        # (Usually Down to select "New Game" + A to confirm)
        logger.info("Phase 4: RPG New Game selection...")
        
        # Press Down to navigate to "New Game" option
        for _ in range(2):
            self.emulator.send_input(WindowEvent.PRESS_ARROW_DOWN)
            for _ in range(5):
                self.emulator.tick()
            self.emulator.send_input(WindowEvent.RELEASE_ARROW_DOWN)
            for _ in range(10):
                self.emulator.tick()
        
        # Press A to select "New Game"
        for _ in range(3):
            self.emulator.send_input(WindowEvent.PRESS_BUTTON_A)
            for _ in range(5):
                self.emulator.tick()
            self.emulator.send_input(WindowEvent.RELEASE_BUTTON_A)
            for _ in range(20):
                self.emulator.tick()
        
        # Save this critical point
        frame = self.emulator.screen_image()
        frame.save(os.path.join(boot_frames_dir, "phase4_new_game.png"))
        
        # Pattern, 4: For Pokémon Games - handle Professor Oak intro
        logger.info("Phase 5: Pokémon-specific sequence...")
        
        # Press A several times to get through the intro dialogue
        for i in range(15):
            self.emulator.send_input(WindowEvent.PRESS_BUTTON_A)
            for _ in range(3):
                self.emulator.tick()
            self.emulator.send_input(WindowEvent.RELEASE_BUTTON_A)
            
            # Longer wait for text animations
            for _ in range(25):
                self.emulator.tick()
                
            # Save occasionally
            if i % 5 == 0:
                frame = self.emulator.screen_image()
                frame.save(os.path.join(boot_frames_dir, f"phase5_pokemon_{i}.png"))
        
        # Pattern 5: Final advance to let animations complete
        logger.info("Phase 6: Final settling...")
        for i in range(120):
            self.emulator.tick()
            if i % 60 == 0:
                frame = self.emulator.screen_image()
                frame.save(os.path.join(boot_frames_dir, f"phase6_final_{i}.png"))
        
        # Save the final boot frame
        final_frame = self.emulator.screen_image()
        final_frame.save(os.path.join(boot_frames_dir, "final_boot_frame.png"))
        logger.info("Game initialization sequence completed")
        
        # Try to detect if we're still at a title screen
        # If so, try one more START + A sequence
        img_array = np.array(final_frame)
        unique_colors = np.unique(img_array.reshape(-1, 3), axis=0)
        
        if len(unique_colors) < 15:  # Still might be at title
            logger.info("Still might be at title screen, trying final keypresses...")
            
            # Press START
            self.emulator.send_input(WindowEvent.PRESS_BUTTON_START)
            for _ in range(10): 
                self.emulator.tick()
            self.emulator.send_input(WindowEvent.RELEASE_BUTTON_START)
            
            # Wait
            for _ in range(30):
                self.emulator.tick()
                
            # Press A multiple times
            for _ in range(10):
                self.emulator.send_input(WindowEvent.PRESS_BUTTON_A)
                for _ in range(5):
                    self.emulator.tick()
                self.emulator.send_input(WindowEvent.RELEASE_BUTTON_A)
                for _ in range(15):
                    self.emulator.tick()
        
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
        
        # Check if the image has some visible content beyond just background
        # We'll look for variation in pixel values rather than just counting non-white pixels
        import numpy as np
        img_array = np.array(screen)
        
        # Count how many unique colors are in the image
        # For a blank or nearly blank image, there will be very few unique colors
        # Flatten the array to 1D and then find unique values
        unique_colors = np.unique(img_array.reshape(-1, 3), axis=0)
        num_unique_colors = len(unique_colors)
        
        # Calculate color variation - standard deviation across the image
        # Low variation indicates a mostly uniform image (likely blank)
        color_std = np.std(img_array)
        
        # If there are few unique colors and low variation, mark the frame as potentially blank
        if num_unique_colors < 10 or color_std < 10:
            # Create a new image with a red border to indicate potentially blank frame
            from PIL import ImageDraw
            draw = ImageDraw.Draw(screen)
            draw.rectangle([(0, 0), (screen.width-1, screen.height-1)], outline="red", width=3)
            # Add debug info to the log
            logger.warning(f"Potentially blank frame detected: {num_unique_colors} unique colors, std: {color_std:.2f}")
        
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
    
    def _initialize_zelda_game(self) -> None:
        """
        Special initialization sequence for Zelda games.
        This uses different keypresses and timing than the standard sequence.
        """
        # Set up debugging directory for frames
        boot_frames_dir = "output/boot_frames/zelda"
        os.makedirs(boot_frames_dir, exist_ok=True)
        
        # Phase 1: Initial boot - just advance for a while to let the boot logo finish
        for i in range(200):  # Longer initial wait for boot sequence
            self.emulator.tick()
            if i % 60 == 0:
                frame = self.emulator.screen_image()
                frame.save(os.path.join(boot_frames_dir, f"zelda_boot_{i}.png"))
        
        # Phase 2: Press START on title screen
        logger.info("Zelda phase 2: Title screen navigation...")
        for i in range(5):
            # Press START button
            self.emulator.send_input(WindowEvent.PRESS_BUTTON_START)
            for _ in range(10):  # Hold button longer 
                self.emulator.tick()
            self.emulator.send_input(WindowEvent.RELEASE_BUTTON_START)
            
            # Wait longer between presses
            for _ in range(60):
                self.emulator.tick()
                
            # Save debug frame
            frame = self.emulator.screen_image()
            frame.save(os.path.join(boot_frames_dir, f"zelda_title_{i}.png"))
        
        # Phase 3: Menu navigation - more conservative
        logger.info("Zelda phase 3: Initial menu navigation...")
        for i in range(3):
            # Try different keypress combinations
            key_sequences = [
                # Down then A (for selecting file in Zelda)
                (WindowEvent.PRESS_ARROW_DOWN, WindowEvent.RELEASE_ARROW_DOWN, 30),
                (WindowEvent.PRESS_BUTTON_A, WindowEvent.RELEASE_BUTTON_A, 30),
                
                # Just A (for confirming)
                (WindowEvent.PRESS_BUTTON_A, WindowEvent.RELEASE_BUTTON_A, 30),
                
                # B (for back/cancel if needed)
                (WindowEvent.PRESS_BUTTON_B, WindowEvent.RELEASE_BUTTON_B, 30)
            ]
            
            for press, release, wait in key_sequences:
                self.emulator.send_input(press)
                for _ in range(5):
                    self.emulator.tick()
                self.emulator.send_input(release)
                
                # Wait between keypresses
                for _ in range(wait):
                    self.emulator.tick()
                    
            # Save debug frame
            frame = self.emulator.screen_image()
            frame.save(os.path.join(boot_frames_dir, f"zelda_menu_{i}.png"))
        
        # Phase 4: Final advance - long wait to allow game to initialize
        logger.info("Zelda phase 4: Final initialization...")
        for i in range(180):
            self.emulator.tick()
            if i % 60 == 0:
                frame = self.emulator.screen_image()
                frame.save(os.path.join(boot_frames_dir, f"zelda_final_{i}.png"))
        
        # Save the final initialization frame
        final_frame = self.emulator.screen_image()
        final_frame.save(os.path.join(boot_frames_dir, "zelda_final_frame.png"))
        logger.info("Zelda initialization sequence completed")

    def close(self) -> None:
        """
        Close the emulator and clean up resources.
        """
        if hasattr(self, 'emulator') and self.emulator:
            logger.info("Stopping PyBoy emulator")
            self.emulator.stop()
            logger.info("PyBoy emulator stopped")