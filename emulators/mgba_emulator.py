"""
mGBA emulator interface for Game Boy Advance games.
Uses the mGBA-http server to control the emulator via HTTP.
"""
import logging
import os
import time
import tempfile
import requests
from PIL import Image
from typing import Dict, Optional

from .base import GameEmulator

logger = logging.getLogger(__name__)

class MGBAEmulator(GameEmulator):
    """
    Implementation of GameEmulator for mGBA using mGBA-http.
    
    mGBA-http is a web API wrapper around mGBA that allows control
    via HTTP requests. The mGBA emulator and mGBA-http server must
    be running separately before using this class.
    """
    
    def __init__(self, rom_path: str, api_url: str = "http://localhost:5000"):
        """
        Connect to a running mGBA-http server.
        
        Args:
            rom_path: Path to the GBA ROM file
            api_url: URL of the mGBA-http server
        """
        self.rom_path = rom_path
        self.api_url = api_url.rstrip('/')
        
        # Check if ROM file exists
        if not os.path.exists(rom_path):
            raise FileNotFoundError(f"ROM file not found: {rom_path}")
        
        # Check if mGBA-http server is running
        try:
            response = requests.get(f"{self.api_url}/core/framecount")
            if response.status_code != 200:
                raise ConnectionError(f"Server returned status: {response.status_code}")
            logger.info(f"Connected to mGBA-http server at {api_url}")
        except requests.RequestException as e:
            logger.error(f"Failed to connect to mGBA-http server: {e}")
            logger.error("""
                Make sure mGBA and mGBA-http are running:
                1. Start mGBA and load your ROM
                2. In mGBA, load the mGBASocketServer.lua script via Tools > Scripting
                3. Start mGBA-http from the command line
                4. Access http://localhost:5000/index.html to verify it's running
            """)
            raise
            
        # Map of button names to mGBA button names
        self.button_map = {
            "A": "a",
            "B": "b",
            "Up": "up",
            "Down": "down",
            "Left": "left", 
            "Right": "right",
            "Start": "start",
            "Select": "select",
            "L": "l",
            "R": "r"
        }
        
        # Create temp directory for screenshots if needed
        self.temp_dir = tempfile.mkdtemp(prefix="mgba_screenshots_")
        logger.info(f"mGBA emulator interface initialized for ROM: {rom_path}")
    
    def get_frame(self) -> Image.Image:
        """
        Capture the current screen from mGBA.
        
        Returns:
            PIL.Image: The current game frame
        """
        # Use a unique filename for each screenshot
        screenshot_path = os.path.join(self.temp_dir, f"screenshot_{time.time():.6f}.png")
        
        # Request screenshot through mGBA-http
        try:
            response = requests.post(
                f"{self.api_url}/core/screenshot",
                json={"path": screenshot_path}
            )
            
            if response.status_code != 200:
                logger.error(f"Screenshot request failed: {response.text}")
                raise RuntimeError(f"Failed to capture screenshot, status: {response.status_code}")
                
            # Open the saved screenshot
            image = Image.open(screenshot_path)
            
            # Clean up the file
            try:
                os.remove(screenshot_path)
            except OSError:
                pass  # Ignore errors during cleanup
                
            return image
        except requests.RequestException as e:
            logger.error(f"Error capturing frame from mGBA: {e}")
            # Return a simple black image as fallback
            return Image.new('RGB', (240, 160), color='black')
    
    def send_input(self, action: str) -> bool:
        """
        Send an input action to mGBA.
        
        Args:
            action: String representing the action (e.g., "A", "Up", etc.)
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Normalize action (case-insensitive lookup)
        action = action.capitalize()
        
        # Map to mGBA button if necessary
        mgba_button = self.button_map.get(action)
        if not mgba_button:
            logger.warning(f"Unknown button: {action}")
            return False
            
        # Press and release the button (quick tap)
        try:
            # Press button
            press_response = requests.post(
                f"{self.api_url}/gamepad/press",
                params={"button": mgba_button}
            )
            
            if press_response.status_code != 200:
                logger.error(f"Button press failed: {press_response.text}")
                return False
                
            # Small delay to ensure button press registers
            time.sleep(0.05)
            
            # Release button
            release_response = requests.post(
                f"{self.api_url}/gamepad/release",
                params={"button": mgba_button}
            )
            
            if release_response.status_code != 200:
                logger.error(f"Button release failed: {release_response.text}")
                return False
                
            return True
        except requests.RequestException as e:
            logger.error(f"Error sending input to mGBA: {e}")
            return False
    
    def close(self) -> None:
        """
        Clean up resources. Does not close mGBA itself as it
        runs in a separate process controlled by the user.
        """
        # Clean up temp directory
        try:
            for filename in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            os.rmdir(self.temp_dir)
        except Exception as e:
            logger.warning(f"Error cleaning up temp directory: {e}")
        
        logger.info("mGBA emulator interface closed")