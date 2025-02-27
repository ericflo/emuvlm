"""
Base emulator interface for EmuVLM.
"""
from abc import ABC, abstractmethod
from PIL import Image
from typing import Optional, List, Tuple, Dict, Any

class EmulatorBase(ABC):
    """
    Abstract base class for all emulator implementations.
    
    Any new emulator must implement these methods to be compatible
    with the EmuVLM framework.
    """
    
    @abstractmethod
    def __init__(self, rom_path: str):
        """
        Initialize the emulator with a ROM file.
        
        Args:
            rom_path: Path to the ROM file
        """
        pass
    
    @abstractmethod
    def get_frame(self) -> Image.Image:
        """
        Get the current frame from the emulator.
        
        Returns:
            PIL Image of the current screen
        """
        pass
    
    @abstractmethod
    def send_input(self, action: str) -> None:
        """
        Send an input action to the emulator.
        
        Args:
            action: Action name (e.g., "A", "Up", "Start")
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """
        Close the emulator and clean up resources.
        """
        pass