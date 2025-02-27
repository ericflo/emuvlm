#!/usr/bin/env python3
"""
Main entry script for LLM-powered turn-based game player.
"""
import argparse
import time
import logging
import yaml
from pathlib import Path

from emulators.pyboy_emulator import PyBoyEmulator
from emulators.mgba_emulator import MGBAEmulator
from model.agent import LLMAgent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_config(config_path):
    """Load game configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def main():
    parser = argparse.ArgumentParser(description='LLM-powered turn-based game player')
    parser.add_argument('--game', type=str, required=True, help='Game key from config or path to ROM')
    parser.add_argument('--summary', type=str, choices=['on', 'off'], default='off', 
                      help='Enable or disable game state summarization')
    parser.add_argument('--config', type=str, default='config.yaml', help='Path to configuration file')
    parser.add_argument('--max-turns', type=int, default=0, help='Maximum number of turns (0 for unlimited)')
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Determine which game to play
    if args.game in config['games']:
        game_config = config['games'][args.game]
    else:
        # Assume args.game is a direct path to ROM
        rom_path = args.game
        ext = Path(rom_path).suffix.lower()
        if ext in ['.gb', '.gbc']:
            emulator_type = "pyboy"
        elif ext in ['.gba']:
            emulator_type = "mgba"
        else:
            raise ValueError(f"Unsupported ROM type: {ext}")
        
        # Create minimal game config
        game_config = {
            'rom': rom_path,
            'emulator': emulator_type,
            'actions': ['Up', 'Down', 'Left', 'Right', 'A', 'B', 'Start', 'Select'],
            'action_delay': 1.0
        }
    
    # Initialize emulator based on type
    if game_config['emulator'].lower() == 'pyboy':
        emulator = PyBoyEmulator(game_config['rom'])
    elif game_config['emulator'].lower() == 'mgba':
        emulator = MGBAEmulator(game_config['rom'])
    else:
        raise ValueError(f"Unsupported emulator: {game_config['emulator']}")
    
    # Initialize LLM agent
    use_summary = args.summary.lower() == 'on'
    agent = LLMAgent(
        model_config=config.get('model', {}),
        valid_actions=game_config['actions'],
        use_summary=use_summary
    )
    
    # Main game loop
    turn_count = 0
    try:
        logger.info(f"Starting game loop for {args.game}")
        while args.max_turns == 0 or turn_count < args.max_turns:
            # Capture current frame
            frame = emulator.get_frame()
            
            # Ask LLM for next action
            action_text = agent.decide_action(frame)
            logger.info(f"Model suggests: {action_text}")
            
            # Parse action and execute
            action = agent.parse_action(action_text)
            if action:
                logger.info(f"Executing: {action}")
                emulator.send_input(action)
                
                # Wait for action to complete
                delay = game_config.get('action_delay', 1.0)
                time.sleep(delay)
            else:
                logger.warning(f"Could not parse action: {action_text}")
            
            turn_count += 1
    except KeyboardInterrupt:
        logger.info("Game loop interrupted by user")
    finally:
        # Clean up
        emulator.close()
        logger.info(f"Game ended after {turn_count} turns")

if __name__ == "__main__":
    main()