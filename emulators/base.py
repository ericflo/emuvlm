"""
Base emulator interface that all emulator implementations should inherit from.
"""
from abc import ABC, abstractmethod
from PIL import Image
from typing import Optional, List

class GameEmulator(ABC):
    """
    Abstract base class for game emulators.
    
    All emulator implementations should inherit from this class
    to ensure a consistent interface for the main control loop.
    """
    
    @abstractmethod
    def get_frame(self) -> Image.Image:
        """
        Capture current frame from the emulator.
        
        Returns:
            PIL.Image: The current frame as a PIL Image
        """
        pass
    
    @abstractmethod
    def send_input(self, action: str) -> bool:
        """
        Send an input action to the emulator.
        
        Args:
            action: String representing the action (e.g., "A", "Up", etc.)
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """
        Clean up resources and close the emulator connection.
        """
        pass