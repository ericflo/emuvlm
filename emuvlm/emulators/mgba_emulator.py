"""
mGBA emulator implementation for Game Boy Advance games.
"""
import logging
import subprocess
import time
import os
import atexit
from PIL import Image, ImageGrab
import tempfile
import requests
from typing import Dict, Any, Optional, Tuple

from emuvlm.emulators.base import EmulatorBase
from emuvlm.utils.rom_loader import load_rom

logger = logging.getLogger(__name__)

class MGBAEmulator(EmulatorBase):
    """
    Emulator implementation using mGBA for Game Boy Advance games.
    
    This implementation uses the mGBA HTTP API for controlling the emulator.
    """
    
    def __init__(self, rom_path: str, api_port: int = 27015):
        """
        Initialize the mGBA emulator.
        
        Args:
            rom_path: Path to the Game Boy Advance ROM file or ZIP archive
            api_port: Port for the mGBA HTTP API
        """
        logger.info(f"Initializing mGBA emulator with ROM: {rom_path}")
        
        # Handle ROM loading (extract from ZIP if needed)
        actual_rom_path = load_rom(rom_path)
        logger.info(f"Using ROM file: {actual_rom_path}")
        
        self.rom_path = actual_rom_path
        self.api_port = api_port
        self.api_url = f"http://localhost:{self.api_port}"
        self.mgba_process = None
        
        # Start mGBA process with HTTP API enabled
        self._start_mgba()
        
        # Register cleanup function to ensure emulator is closed
        atexit.register(self.close)
        
        # Wait for the emulator to initialize
        time.sleep(1)
        
        # Test the API connection
        self._check_api_connection()
        
        # Define input mapping
        self.input_mapping = {
            "A": "a",
            "B": "b",
            "L": "l",
            "R": "r",
            "Up": "up",
            "Down": "down",
            "Left": "left",
            "Right": "right",
            "Start": "start",
            "Select": "select"
        }
        
        logger.info("mGBA emulator initialized successfully")
    
    def _start_mgba(self) -> None:
        """
        Start the mGBA process with HTTP API enabled.
        """
        cmd = [
            "mgba",
            "-P",  # Enable the HTTP API
            str(self.api_port),
            self.rom_path
        ]
        
        try:
            # Start mGBA process
            self.mgba_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            logger.info(f"Started mGBA process with PID {self.mgba_process.pid}")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.error(f"Failed to start mGBA: {e}")
            raise RuntimeError(f"Failed to start mGBA: {e}")
    
    def _check_api_connection(self) -> bool:
        """
        Check if the mGBA API is responding.
        
        Returns:
            bool: True if connection is successful
        """
        try:
            response = requests.get(f"{self.api_url}/status", timeout=5)
            if response.status_code == 200:
                logger.info("Successfully connected to mGBA HTTP API")
                return True
            else:
                logger.warning(f"mGBA API returned status code {response.status_code}")
                return False
        except requests.RequestException as e:
            logger.error(f"Failed to connect to mGBA API: {e}")
            return False
    
    def get_frame(self) -> Image.Image:
        """
        Get the current frame from the emulator.
        
        Returns:
            PIL Image of the current screen
        """
        try:
            # Request a screenshot from the API
            response = requests.get(f"{self.api_url}/screenshot", timeout=5)
            
            if response.status_code == 200:
                # Load the image from response content
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                    temp_file.write(response.content)
                    temp_path = temp_file.name
                
                # Open the image and remove the temp file
                img = Image.open(temp_path)
                os.unlink(temp_path)
                
                return img
            else:
                logger.error(f"Failed to get screenshot: {response.status_code}")
                # Return a black screen as fallback
                return Image.new('RGB', (240, 160), (0, 0, 0))
                
        except requests.RequestException as e:
            logger.error(f"Error getting frame from mGBA: {e}")
            # Return a black screen as fallback
            return Image.new('RGB', (240, 160), (0, 0, 0))
    
    def send_input(self, action: str) -> None:
        """
        Send an input action to the emulator.
        
        Args:
            action: Action name (e.g., "A", "Up", "Start")
        """
        if action in self.input_mapping:
            mgba_key = self.input_mapping[action]
            
            try:
                # Press the key
                press_url = f"{self.api_url}/input/keyDown?key={mgba_key}"
                requests.post(press_url, timeout=1)
                
                # Small delay to register the press
                time.sleep(0.05)
                
                # Release the key
                release_url = f"{self.api_url}/input/keyUp?key={mgba_key}"
                requests.post(release_url, timeout=1)
                
                logger.debug(f"Sent input action: {action}")
            except requests.RequestException as e:
                logger.error(f"Failed to send input to mGBA: {e}")
        else:
            logger.warning(f"Unsupported action for mGBA: {action}")
    
    def close(self) -> None:
        """
        Close the emulator and clean up resources.
        """
        if hasattr(self, 'mgba_process') and self.mgba_process:
            logger.info("Stopping mGBA emulator")
            
            try:
                # First try to exit gracefully through the API
                requests.post(f"{self.api_url}/exit", timeout=1)
                time.sleep(0.5)  # Give it a moment to close
            except:
                pass  # API might already be down, continue to forced termination
            
            # If process is still running, terminate it
            if self.mgba_process.poll() is None:
                self.mgba_process.terminate()
                try:
                    self.mgba_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    # If termination times out, kill the process
                    self.mgba_process.kill()
            
            logger.info("mGBA emulator stopped")
            
            # Unregister the atexit handler
            try:
                atexit.unregister(self.close)
            except:
                pass  # Ignore if already unregistered