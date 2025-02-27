#!/usr/bin/env python3
"""
Test script for emulator interfaces.
This can be used to verify that the emulator connections work correctly.
"""
import argparse
import logging
import os
import time
from pathlib import Path

from emulators.pyboy_emulator import PyBoyEmulator
from emulators.mgba_emulator import MGBAEmulator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_emulator(emulator_type, rom_path, button_sequence, delay=1.0):
    """Test an emulator by capturing frames and sending inputs."""
    logger.info(f"Testing {emulator_type} emulator with ROM: {rom_path}")

    # Create output directory for test images
    os.makedirs("test_output", exist_ok=True)
    
    # Initialize the appropriate emulator
    if emulator_type.lower() == 'pyboy':
        emulator = PyBoyEmulator(rom_path)
    elif emulator_type.lower() == 'mgba':
        emulator = MGBAEmulator(rom_path)
    else:
        raise ValueError(f"Unsupported emulator type: {emulator_type}")
    
    try:
        # Capture initial frame
        logger.info("Capturing initial frame...")
        frame = emulator.get_frame()
        initial_frame_path = os.path.join("test_output", "initial_frame.png")
        frame.save(initial_frame_path)
        logger.info(f"Initial frame saved to {initial_frame_path}")
        
        # Send a sequence of button presses
        for i, button in enumerate(button_sequence):
            logger.info(f"Pressing button: {button}")
            emulator.send_input(button)
            
            # Wait for the action to take effect
            time.sleep(delay)
            
            # Capture frame after action
            frame = emulator.get_frame()
            frame_path = os.path.join("test_output", f"frame_after_{button}_{i}.png")
            frame.save(frame_path)
            logger.info(f"Frame after '{button}' saved to {frame_path}")
            
        logger.info("Test completed successfully")
        
    finally:
        # Clean up
        emulator.close()

def main():
    parser = argparse.ArgumentParser(description='Test emulator interfaces')
    parser.add_argument('--emulator', type=str, required=True, 
                        choices=['pyboy', 'mgba'], 
                        help='Emulator type to test')
    parser.add_argument('--rom', type=str, required=True, 
                        help='Path to the ROM file')
    parser.add_argument('--buttons', type=str, default='Start,A,B',
                        help='Comma-separated sequence of buttons to press (e.g., Start,A,B)')
    parser.add_argument('--delay', type=float, default=1.0,
                        help='Delay in seconds between button presses')
    
    args = parser.parse_args()
    
    # Parse button sequence
    button_sequence = [b.strip() for b in args.buttons.split(',')]
    
    test_emulator(args.emulator, args.rom, button_sequence, args.delay)

if __name__ == "__main__":
    main()