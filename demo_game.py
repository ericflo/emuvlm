#!/usr/bin/env python3
"""
Demo script that plays a game with a predefined sequence of actions.
Useful for testing emulator interfaces and verifying setup.
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

# Demo sequences for different games
DEMO_SEQUENCES = {
    "pokemon_red": [
        "Start",      # Start game
        "A", "A",     # Skip intro
        "Down",       # Move to "NEW GAME"
        "A",          # Select "NEW GAME"
        "A", "A",     # Skip through dialog
        "Down", "A",  # Select character name
        "A", "A", "A" # Confirm name
    ],
    "pokemon_emerald": [
        "Start",      # Start game
        "A", "A",     # Skip intro
        "Down",       # Move to "NEW GAME"
        "A",          # Select "NEW GAME"
        "A", "A",     # Skip through dialog
        "Down", "A",  # Navigate menus
        "A", "A", "A" # Confirm selections
    ],
    # Add more game sequences as needed
}

def demo_game(rom_path, sequence=None, delay=1.0, output_dir="demo_output"):
    """
    Play a game with a predefined sequence of actions.
    
    Args:
        rom_path: Path to the game ROM
        sequence: List of button actions to perform
        delay: Delay between actions in seconds
        output_dir: Directory to save screenshots
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Determine emulator type from file extension
    ext = Path(rom_path).suffix.lower()
    if ext in ['.gb', '.gbc']:
        logger.info(f"Using PyBoy emulator for {rom_path}")
        emulator = PyBoyEmulator(rom_path)
    elif ext in ['.gba']:
        logger.info(f"Using mGBA emulator for {rom_path}")
        emulator = MGBAEmulator(rom_path)
    else:
        raise ValueError(f"Unsupported ROM type: {ext}")
    
    # If no sequence provided, try to use a predefined one based on filename
    if not sequence:
        rom_name = Path(rom_path).stem.lower()
        for game_name, game_sequence in DEMO_SEQUENCES.items():
            if game_name in rom_name:
                sequence = game_sequence
                logger.info(f"Using predefined sequence for {game_name}")
                break
    
    # If still no sequence, use a default one
    if not sequence:
        sequence = ["Start", "A", "B", "Up", "Down", "Left", "Right"]
        logger.info("Using default button sequence")
    
    try:
        # Capture initial frame
        initial_frame = emulator.get_frame()
        initial_frame_path = os.path.join(output_dir, "00_initial.png")
        initial_frame.save(initial_frame_path)
        logger.info(f"Initial frame saved to {initial_frame_path}")
        
        # Execute the sequence
        for i, action in enumerate(sequence, 1):
            logger.info(f"Action {i}/{len(sequence)}: {action}")
            
            # Send the input
            success = emulator.send_input(action)
            if not success:
                logger.warning(f"Failed to send action: {action}")
                continue
            
            # Wait for the action to take effect
            time.sleep(delay)
            
            # Capture the frame after the action
            frame = emulator.get_frame()
            frame_path = os.path.join(output_dir, f"{i:02d}_{action}.png")
            frame.save(frame_path)
            logger.info(f"Frame saved to {frame_path}")
        
        logger.info("Demo completed successfully")
        
    finally:
        # Clean up
        emulator.close()
        logger.info("Emulator closed")

def main():
    parser = argparse.ArgumentParser(description='Demo script for game emulator interfaces')
    parser.add_argument('--rom', type=str, required=True, 
                        help='Path to the ROM file')
    parser.add_argument('--sequence', type=str, 
                        help='Comma-separated list of actions (e.g., "Start,A,B,Up")')
    parser.add_argument('--delay', type=float, default=1.0,
                        help='Delay in seconds between actions')
    parser.add_argument('--output-dir', type=str, default='demo_output',
                        help='Directory to save screenshots')
    
    args = parser.parse_args()
    
    # Parse sequence if provided
    sequence = None
    if args.sequence:
        sequence = [button.strip() for button in args.sequence.split(',')]
    
    demo_game(args.rom, sequence, args.delay, args.output_dir)

if __name__ == "__main__":
    main()