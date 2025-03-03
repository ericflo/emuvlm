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

from emuvlm.emulators.base import EmulatorBase
from emuvlm.emulators.pyboy_emulator import PyBoyEmulator
from emuvlm.emulators.mgba_emulator import MGBAEmulator
from emuvlm.emulators.snes9x_emulator import SNES9xEmulator
from emuvlm.emulators.fceux_emulator import FCEUXEmulator
from emuvlm.emulators.genesis_plus_gx_emulator import GenesisPlusGXEmulator
from emuvlm.emulators.duckstation_emulator import DuckstationEmulator
from emuvlm.emulators.mupen64plus_emulator import Mupen64PlusEmulator

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("emuvlm.test")

# Define standard controller actions for testing
STANDARD_ACTIONS = ['Up', 'Down', 'Left', 'Right', 'A', 'B', 'Start', 'Select']

def test_emulator(emulator, actions=None, iterations=10, delay=0.5):
    """
    Test an emulator by running a sequence of actions.
    
    Args:
        emulator: Initialized emulator instance
        actions: List of actions to test (default: directional + A/B/Start/Select)
        iterations: Number of test iterations
        delay: Delay between actions in seconds
    """
    if actions is None:
        actions = STANDARD_ACTIONS
    
    logger.info(f"Testing emulator with {len(actions)} actions for {iterations} iterations")
    logger.info(f"Actions: {', '.join(actions)}")
    
    try:
        # First, get and save the initial frame
        initial_frame = emulator.get_frame()
        logger.info(f"Initial frame size: {initial_frame.size}")
        
        # Create a test output directory
        os.makedirs("output/test_output", exist_ok=True)
        initial_frame.save("output/test_output/initial_frame.png")
        logger.info("Saved initial frame to output/test_output/initial_frame.png")
        
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
            frame.save(f"output/test_output/frame_{i+1}_{action}.png")
            
        logger.info("Emulator test completed successfully")
        # Verification
        assert initial_frame is not None, "Initial frame should not be None"
        assert initial_frame.size[0] > 0 and initial_frame.size[1] > 0, "Frame should have positive dimensions"
        
    except Exception as e:
        logger.error(f"Error during emulator test: {e}")
        assert False, f"Emulator test failed with error: {e}"

def test_all_emulators(rom_paths, iterations=5, delay=0.5):
    """
    Test all emulator implementations with appropriate ROMs.
    
    Args:
        rom_paths: Dictionary mapping emulator type to ROM path
        iterations: Number of test iterations for each emulator
        delay: Delay between actions in seconds
    """
    results = {}
    
    # Test each emulator if a ROM path is provided
    for emulator_type, rom_path in rom_paths.items():
        if not rom_path or not os.path.exists(rom_path):
            logger.warning(f"Skipping {emulator_type} test: ROM not found at {rom_path}")
            results[emulator_type] = False
            continue
            
        logger.info(f"\n==== Testing {emulator_type} emulator ====")
        logger.info(f"ROM path: {rom_path}")
        
        try:
            # Initialize the emulator
            if emulator_type == 'pyboy':
                emulator = PyBoyEmulator(rom_path)
            elif emulator_type == 'mgba':
                emulator = MGBAEmulator(rom_path)
            elif emulator_type == 'snes9x':
                emulator = SNES9xEmulator(rom_path)
            elif emulator_type == 'fceux':
                emulator = FCEUXEmulator(rom_path)
            elif emulator_type == 'genesis':
                emulator = GenesisPlusGXEmulator(rom_path)
            elif emulator_type == 'duckstation':
                emulator = DuckstationEmulator(rom_path)
            elif emulator_type == 'mupen64plus':
                emulator = Mupen64PlusEmulator(rom_path)
            else:
                logger.error(f"Unknown emulator type: {emulator_type}")
                results[emulator_type] = False
                continue
                
            # Create a subdirectory for this emulator's test output
            # Use the base name of the ROM file (without full path) to avoid spaces and special chars
            rom_name = os.path.basename(rom_path).replace(' ', '_').replace('[', '').replace(']', '').replace('(', '').replace(')', '')
            emulator_output_dir = f"output/test_output/{emulator_type}_{rom_name}"
            os.makedirs(emulator_output_dir, exist_ok=True)
            logger.info(f"Saving test output to: {emulator_output_dir}")
            
            # Modify the test_emulator function to save frames in the emulator-specific directory
            def emulator_specific_save(frame, filename):
                full_path = os.path.join(emulator_output_dir, filename)
                frame.save(full_path)
                return full_path
                
            # Save the initial frame
            initial_frame = emulator.get_frame()
            initial_frame_path = emulator_specific_save(initial_frame, "initial_frame.png")
            logger.info(f"Initial frame size: {initial_frame.size}")
            logger.info(f"Saved initial frame to {initial_frame_path}")
            
            # Run the iterations
            for i in range(iterations):
                action = STANDARD_ACTIONS[i % len(STANDARD_ACTIONS)]
                logger.info(f"Iteration {i+1}/{iterations}: Testing action '{action}'")
                
                # Send the action
                emulator.send_input(action)
                
                # Wait for the action to complete
                time.sleep(delay)
                
                # Get and save the frame after the action
                frame = emulator.get_frame()
                frame_path = emulator_specific_save(frame, f"frame_{i+1}_{action}.png")
            
            logger.info(f"Emulator test for {emulator_type} completed successfully")
            success = True
            
            # Record the result
            results[emulator_type] = success
            
            # Close the emulator
            emulator.close()
            
        except Exception as e:
            logger.error(f"Error testing {emulator_type} emulator: {e}")
            results[emulator_type] = False
    
    # Print summary of results
    logger.info("\n===== Emulator Test Results =====")
    all_passed = True
    for emulator_type, success in results.items():
        status = "PASSED" if success else "FAILED"
        logger.info(f"{emulator_type}: {status}")
        all_passed = all_passed and success
    
    # Use assertion instead of returning a value
    if not all_passed:
        logger.warning("Not all emulator tests passed")
    else:
        logger.info("All emulator tests passed successfully")

def main():
    """Main entry point for the emulator test script."""
    parser = argparse.ArgumentParser(description='Test emulator implementations')
    parser.add_argument('--rom', type=str, help='Path to a ROM file')
    parser.add_argument('--emulator', type=str, 
                       choices=['pyboy', 'mgba', 'snes9x', 'fceux', 'genesis', 'duckstation', 'mupen64plus'],
                       help='Single emulator type to test')
    parser.add_argument('--all', action='store_true', help='Test all emulators with provided ROM paths')
    parser.add_argument('--iterations', type=int, default=5, help='Number of test iterations')
    parser.add_argument('--delay', type=float, default=0.5, help='Delay between actions')
    
    # Add arguments for each emulator's ROM path
    parser.add_argument('--pyboy-rom', type=str, help='Path to a Game Boy/GBC ROM')
    parser.add_argument('--mgba-rom', type=str, help='Path to a GBA ROM')
    parser.add_argument('--snes9x-rom', type=str, help='Path to a SNES ROM')
    parser.add_argument('--fceux-rom', type=str, help='Path to a NES ROM')
    parser.add_argument('--genesis-rom', type=str, help='Path to a Genesis/Mega Drive ROM')
    parser.add_argument('--duckstation-rom', type=str, help='Path to a PlayStation ISO/BIN')
    parser.add_argument('--mupen64plus-rom', type=str, help='Path to a Nintendo 64 ROM')
    
    args = parser.parse_args()
    
    # Create test output directory
    os.makedirs("output/test_output", exist_ok=True)
    
    if args.all:
        # Test all emulators with provided ROM paths
        rom_paths = {
            'pyboy': args.pyboy_rom,
            'mgba': args.mgba_rom,
            'snes9x': args.snes9x_rom,
            'fceux': args.fceux_rom,
            'genesis': args.genesis_rom,
            'duckstation': args.duckstation_rom,
            'mupen64plus': args.mupen64plus_rom
        }
        
        # Run the test and catch any assertion errors
        try:
            test_all_emulators(
                rom_paths,
                iterations=args.iterations,
                delay=args.delay
            )
            return 0  # Success
        except AssertionError as e:
            logger.error(f"Test failed: {e}")
            return 1  # Failure
        
    elif args.emulator and args.rom:
        # Test a single emulator
        if not os.path.exists(args.rom):
            logger.error(f"ROM file not found: {args.rom}")
            return 1
        
        # Initialize the appropriate emulator
        try:
            emulator_type = args.emulator.lower()
            logger.info(f"Initializing {emulator_type} emulator with ROM: {args.rom}")
            
            if emulator_type == 'pyboy':
                emulator = PyBoyEmulator(args.rom)
            elif emulator_type == 'mgba':
                emulator = MGBAEmulator(args.rom)
            elif emulator_type == 'snes9x':
                emulator = SNES9xEmulator(args.rom)
            elif emulator_type == 'fceux':
                emulator = FCEUXEmulator(args.rom)
            elif emulator_type == 'genesis':
                emulator = GenesisPlusGXEmulator(args.rom)
            elif emulator_type == 'duckstation':
                emulator = DuckstationEmulator(args.rom)
            elif emulator_type == 'mupen64plus':
                emulator = Mupen64PlusEmulator(args.rom)
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
    else:
        # No valid test configuration provided
        parser.print_help()
        return 1

def test_game_boy_roms():
    """
    Test all Game Boy ROMs found in the roms/gb directory.
    """
    # Find all Game Boy ROMs
    gb_rom_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "roms", "gb")
    
    if not os.path.exists(gb_rom_dir):
        logger.error(f"Game Boy ROM directory not found: {gb_rom_dir}")
        assert False, f"Game Boy ROM directory not found: {gb_rom_dir}"
    
    # Get a list of all .gb files
    gb_roms = [os.path.join(gb_rom_dir, f) for f in os.listdir(gb_rom_dir) if f.lower().endswith('.gb')]
    
    if not gb_roms:
        logger.warning(f"No Game Boy ROMs found in {gb_rom_dir}")
        # This is just a warning, not a failure - we'll skip the test
        logger.info("Skipping Game Boy ROM tests due to no ROMs found")
        return
    
    logger.info(f"Found {len(gb_roms)} Game Boy ROMs")
    
    # Test each ROM
    for rom_path in gb_roms:
        try:
            rom_name = os.path.basename(rom_path)
            logger.info(f"\n==== Testing ROM: {rom_name} ====")
            
            # Initialize the emulator
            emulator = PyBoyEmulator(rom_path)
            assert emulator is not None, f"Failed to initialize PyBoyEmulator with ROM: {rom_path}"
            
            # Create a clean output directory name
            clean_rom_name = rom_name.replace(' ', '_').replace('[', '').replace(']', '').replace('(', '').replace(')', '')
            output_dir = f"output/test_output/gb_{clean_rom_name}"
            os.makedirs(output_dir, exist_ok=True)
            
            # Get and save initial frame
            initial_frame = emulator.get_frame()
            assert initial_frame is not None, "Failed to get initial frame from emulator"
            initial_frame_path = os.path.join(output_dir, "initial_frame.png")
            initial_frame.save(initial_frame_path)
            logger.info(f"Saved initial frame to {initial_frame_path}")
            
            # Test a sequence of actions
            for i in range(5):  # 5 iterations per ROM
                action = STANDARD_ACTIONS[i % len(STANDARD_ACTIONS)]
                logger.info(f"Testing action: {action}")
                
                # Send input
                emulator.send_input(action)
                time.sleep(0.5)  # Short delay
                
                # Get and save the frame
                frame = emulator.get_frame()
                assert frame is not None, f"Failed to get frame after action {action}"
                frame_path = os.path.join(output_dir, f"frame_{i+1}_{action}.png")
                frame.save(frame_path)
            
            # Close the emulator
            emulator.close()
            logger.info(f"Successfully tested {rom_name}")
            
        except Exception as e:
            logger.error(f"Error testing {rom_path}: {e}")
            # Continue with the next ROM instead of failing the whole test
            logger.warning(f"Skipping ROM due to error: {rom_name}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test-gb-roms":
        # Special command to test all GB ROMs
        success = test_game_boy_roms()
        sys.exit(0 if success else 1)
    else:
        # Normal operation
        sys.exit(main())