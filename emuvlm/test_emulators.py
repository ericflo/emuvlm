#!/usr/bin/env python3
"""
Test script for emulator implementations.
"""
import argparse
import logging
import time
import sys
import os
from pathlib import Path
from PIL import Image

from emuvlm.emulators.pyboy_emulator import PyBoyEmulator
from emuvlm.emulators.mgba_emulator import MGBAEmulator

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("emuvlm.test")

def test_emulator(emulator, actions=None, iterations=10, delay=0.5):
    """
    Test an emulator by running a sequence of actions.
    
    Args:
        emulator: Initialized emulator instance
        actions: List of actions to test (default: directional + A/B)
        iterations: Number of test iterations
        delay: Delay between actions in seconds
    """
    if actions is None:
        actions = ['Up', 'Down', 'Left', 'Right', 'A', 'B']
    
    logger.info(f"Testing emulator with {len(actions)} actions for {iterations} iterations")
    logger.info(f"Actions: {', '.join(actions)}")
    
    try:
        # First, get and save the initial frame
        initial_frame = emulator.get_frame()
        logger.info(f"Initial frame size: {initial_frame.size}")
        
        # Create a test output directory
        os.makedirs("test_output", exist_ok=True)
        initial_frame.save("test_output/initial_frame.png")
        logger.info("Saved initial frame to test_output/initial_frame.png")
        
        # Run the test iterations
        for i in range(iterations):
            action = actions[i % len(actions)]
            logger.info(f"Iteration {i+1}/{iterations}: Testing action '{action}'")
            
            # Send the action
            emulator.send_input(action)
            
            # Wait for the action to complete
            time.sleep(delay)
            
            # Get and save the frame after the action
            frame = emulator.get_frame()
            frame.save(f"test_output/frame_{i+1}_{action}.png")
            
        logger.info("Emulator test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error during emulator test: {e}")
        return False

def main():
    """Main entry point for the emulator test script."""
    parser = argparse.ArgumentParser(description='Test emulator implementations')
    parser.add_argument('--rom', type=str, required=True, help='Path to the ROM file')
    parser.add_argument('--emulator', type=str, choices=['pyboy', 'mgba'], required=True, help='Emulator type')
    parser.add_argument('--iterations', type=int, default=10, help='Number of test iterations')
    parser.add_argument('--delay', type=float, default=0.5, help='Delay between actions')
    args = parser.parse_args()
    
    # Validate ROM file
    rom_path = args.rom
    if not os.path.exists(rom_path):
        logger.error(f"ROM file not found: {rom_path}")
        return 1
    
    # Initialize the appropriate emulator
    try:
        if args.emulator.lower() == 'pyboy':
            logger.info(f"Initializing PyBoy emulator with ROM: {rom_path}")
            emulator = PyBoyEmulator(rom_path)
        elif args.emulator.lower() == 'mgba':
            logger.info(f"Initializing mGBA emulator with ROM: {rom_path}")
            emulator = MGBAEmulator(rom_path)
        else:
            logger.error(f"Unsupported emulator type: {args.emulator}")
            return 1
        
        # Run the test
        success = test_emulator(
            emulator, 
            iterations=args.iterations,
            delay=args.delay
        )
        
        # Close the emulator
        emulator.close()
        
        return 0 if success else 1
        
    except Exception as e:
        logger.error(f"Error during test: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())