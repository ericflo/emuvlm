#!/usr/bin/env python3
"""
Main entry script for LLM-powered turn-based game player.
"""
import argparse
import time
import logging
import yaml
import os
import json
import datetime
import shutil
from pathlib import Path
from PIL import Image

from emuvlm.emulators.pyboy_emulator import PyBoyEmulator
from emuvlm.emulators.mgba_emulator import MGBAEmulator
from emuvlm.model.agent import LLMAgent

# Initialize basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("emuvlm")

def setup_logging(config):
    """Configure logging based on config settings."""
    log_config = config.get('logging', {})
    log_level = getattr(logging, log_config.get('level', 'INFO'))
    
    # Create logs directory
    log_file = log_config.get('log_file', 'output/logs/emuvlm.log')
    log_dir = os.path.dirname(log_file)
    os.makedirs(log_dir, exist_ok=True)
    
    # Create frames directory if frame saving is enabled
    if log_config.get('save_frames', False):
        frames_dir = log_config.get('frames_dir', 'output/logs/frames')
        os.makedirs(frames_dir, exist_ok=True)
    
    # Set up file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    
    logger.info(f"Logging configured with level {log_level}")
    logger.info(f"Log file: {log_file}")

def load_config(config_path):
    """Load game configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def save_session(session_dir, game_name, turn_count, agent, last_frame):
    """Save the current game session for later resumption."""
    # Create session directory if it doesn't exist
    os.makedirs(session_dir, exist_ok=True)
    
    # Timestamp for the session filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    session_file = os.path.join(session_dir, f"{game_name}_{timestamp}.session")
    
    # Create session data
    session_data = {
        "game": game_name,
        "turn_count": turn_count,
        "timestamp": timestamp,
        "summary": agent.summary if hasattr(agent, 'summary') else ""
    }
    
    # Save session data
    with open(session_file, 'w') as f:
        json.dump(session_data, f, indent=2)
    
    # Save the last frame if provided
    if last_frame:
        frame_file = session_file.replace('.session', '.png')
        last_frame.save(frame_file)
    
    logger.info(f"Session saved to {session_file}")
    return session_file

def load_session(session_file):
    """Load a previously saved game session."""
    with open(session_file, 'r') as f:
        session_data = json.load(f)
    
    # Load the frame if it exists
    frame_file = session_file.replace('.session', '.png')
    last_frame = None
    if os.path.exists(frame_file):
        last_frame = Image.open(frame_file)
    
    logger.info(f"Loaded session from {session_file}")
    return session_data, last_frame

def determine_delay(game_config, action):
    """
    Determine the appropriate delay for the given action and game context.
    
    Args:
        game_config: Game configuration from config file
        action: The action being executed
        
    Returns:
        float: Delay in seconds
    """
    # Get timing config if available
    timing = game_config.get('timing', {})
    
    # Default to the general action_delay
    delay = game_config.get('action_delay', 1.0)
    
    # Adjust based on action type
    if action in ['Up', 'Down', 'Left', 'Right']:
        # Navigation actions use menu_nav_delay
        delay = timing.get('menu_nav_delay', delay)
    elif action in ['A']:
        # A button could trigger battle animation
        delay = timing.get('battle_anim_delay', delay * 1.5)
    elif action in ['B']:
        # B button is often used to skip dialog
        delay = timing.get('text_scroll_delay', delay)
    
    return delay

def save_frame(frame, frame_dir, turn_count, action):
    """Save a frame to disk for debugging."""
    # Create filename with turn count and action
    filename = f"{turn_count:06d}_{action.replace(' ', '_')}.png"
    filepath = os.path.join(frame_dir, filename)
    
    # Save the frame
    frame.save(filepath)
    logger.debug(f"Saved frame: {filepath}")

def main():
    parser = argparse.ArgumentParser(description='LLM-powered turn-based game player')
    parser.add_argument('--game', type=str, required=True, help='Game key from config or path to ROM')
    parser.add_argument('--summary', type=str, choices=['on', 'off'], default='off', 
                      help='Enable or disable game state summarization')
    parser.add_argument('--config', type=str, default='config.yaml', help='Path to configuration file')
    parser.add_argument('--max-turns', type=int, default=0, help='Maximum number of turns (0 for unlimited)')
    parser.add_argument('--cache', type=str, choices=['on', 'off'], default='on',
                      help='Enable or disable frame caching')
    parser.add_argument('--session', type=str, default=None, 
                      help='Path to session file to resume a game')
    parser.add_argument('--session-save-interval', type=int, default=None,
                      help='Override auto-save interval from config')
    args = parser.parse_args()
    
    # Load configuration
    if os.path.isabs(args.config):
        config_path = args.config
    else:
        # If it's not an absolute path, try relative to current directory
        # and then fall back to the default in the package
        if os.path.exists(args.config):
            config_path = args.config
        else:
            config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    
    config = load_config(config_path)
    
    # Setup logging
    setup_logging(config)
    
    # Session configuration
    session_config = config.get('sessions', {})
    enable_session_save = session_config.get('enable_save', False)
    session_save_dir = session_config.get('save_dir', 'output/sessions')
    auto_save_interval = args.session_save_interval or session_config.get('auto_save_interval', 50)
    
    # Resume from session if provided
    session_data = None
    starting_turn = 0
    if args.session:
        session_data, _ = load_session(args.session)
        starting_turn = session_data.get('turn_count', 0)
        args.game = session_data.get('game', args.game)
        logger.info(f"Resuming {args.game} from turn {starting_turn}")
    
    # Determine which game to play
    if args.game in config['games']:
        game_config = config['games'][args.game]
        game_name = args.game
    else:
        # Assume args.game is a direct path to ROM
        rom_path = args.game
        ext = Path(rom_path).suffix.lower()
        if ext in ['.gb', '.gbc']:
            emulator_type = "pyboy"
        elif ext in ['.gba']:
            emulator_type = "mgba"
        elif ext in ['.nes']:
            emulator_type = "fceux"
        elif ext in ['.sfc', '.smc']:
            emulator_type = "snes9x"
        elif ext in ['.md', '.gen', '.smd']:
            emulator_type = "genesis_plus_gx"
        elif ext in ['.n64', '.z64', '.v64']:
            emulator_type = "mupen64plus"
        elif ext in ['.iso', '.bin', '.cue', '.img']:
            emulator_type = "duckstation"
        else:
            raise ValueError(f"Unsupported ROM type: {ext}")
        
        # Create minimal game config
        game_config = {
            'rom': rom_path,
            'emulator': emulator_type,
            'actions': ['Up', 'Down', 'Left', 'Right', 'A', 'B', 'Start', 'Select'],
            'action_delay': 1.0
        }
        game_name = os.path.basename(rom_path)
    
    # Initialize emulator based on type
    emulator_type = game_config['emulator'].lower()
    
    if emulator_type == 'pyboy':
        emulator = PyBoyEmulator(game_config['rom'])
    elif emulator_type == 'mgba':
        emulator = MGBAEmulator(game_config['rom'])
    elif emulator_type == 'fceux':
        from emuvlm.emulators.fceux_emulator import FCEUXEmulator
        emulator = FCEUXEmulator(game_config['rom'])
    elif emulator_type == 'snes9x':
        from emuvlm.emulators.snes9x_emulator import SNES9xEmulator
        emulator = SNES9xEmulator(game_config['rom'])
    elif emulator_type == 'genesis_plus_gx':
        from emuvlm.emulators.genesis_plus_gx_emulator import GenesisPlusGXEmulator
        emulator = GenesisPlusGXEmulator(game_config['rom'])
    elif emulator_type == 'mupen64plus':
        from emuvlm.emulators.mupen64plus_emulator import Mupen64PlusEmulator
        emulator = Mupen64PlusEmulator(game_config['rom'])
    elif emulator_type == 'duckstation':
        from emuvlm.emulators.duckstation_emulator import DuckstationEmulator
        emulator = DuckstationEmulator(game_config['rom'])
    else:
        raise ValueError(f"Unsupported emulator: {game_config['emulator']}")
    
    # Initialize LLM agent
    use_summary = args.summary.lower() == 'on'
    
    # Update model config for caching and enable autostart
    model_config = config.get('model', {}).copy()
    model_config['enable_cache'] = args.cache.lower() == 'on'
    model_config['autostart_server'] = True
    
    # Pass game-specific properties to model config
    if 'game_type' in game_config:
        model_config['game_type'] = game_config['game_type']
        logger.info(f"Using game-specific instructions for game type: {game_config['game_type']}")
        
    # Add prompt additions from game config
    if 'prompt_additions' in game_config:
        model_config['prompt_additions'] = game_config['prompt_additions']
        logger.info(f"Added {len(game_config['prompt_additions'])} game-specific prompt additions")
        
    # Add game settings if available
    if 'settings' in game_config:
        model_config['settings'] = game_config['settings']
        logger.info(f"Added game-specific settings to model configuration")
    
    agent = LLMAgent(
        model_config=model_config,
        valid_actions=game_config['actions'],
        use_summary=use_summary
    )
    
    # If resuming from a session, restore the summary
    if session_data and 'summary' in session_data and use_summary:
        agent.summary = session_data['summary']
        logger.info(f"Restored game summary from session")
    
    # Configure frame saving
    log_config = config.get('logging', {})
    save_frames = log_config.get('save_frames', False)
    frames_dir = log_config.get('frames_dir', 'output/logs/frames')
    
    # If we're saving frames, ensure the directory exists
    if save_frames:
        # Create a subdirectory for this specific game session
        # Clean the game name to avoid directory naming issues
        clean_game_name = game_name.replace(' ', '_').replace('[', '').replace(']', '').replace('(', '').replace(')', '')
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        session_frames_dir = os.path.join(frames_dir, f"{clean_game_name}_{timestamp}")
        os.makedirs(session_frames_dir, exist_ok=True)
        logger.info(f"Saving frames to {session_frames_dir}")
    
    # Main game loop
    turn_count = starting_turn
    last_frame = None
    consecutive_none_actions = 0
    max_none_actions = 5  # Maximum number of consecutive "do nothing" actions
    try:
        logger.info(f"Starting game loop for {game_name}")
        while args.max_turns == 0 or turn_count < args.max_turns:
            # Capture current frame
            frame = emulator.get_frame()
            last_frame = frame.copy()  # Save for session
            
            # Save frame if enabled
            if save_frames:
                save_frame(frame, session_frames_dir, turn_count, "input")
            
            # Ask LLM for next action
            action_text = agent.decide_action(frame)
            logger.info(f"Model suggests: {action_text}")
            
            # Parse action and execute
            action = agent.parse_action(action_text)
            if action:
                # A valid action was chosen
                logger.info(f"Executing: {action}")
                emulator.send_input(action)
                
                # Reset consecutive none action counter since we took a real action
                consecutive_none_actions = 0
                
                # Wait for action to complete with dynamic delay
                delay = determine_delay(game_config, action)
                logger.debug(f"Waiting {delay:.2f}s for action to complete")
                time.sleep(delay)
                
                # Save the frame after action if enabled
                if save_frames:
                    after_frame = emulator.get_frame()
                    save_frame(after_frame, session_frames_dir, turn_count, f"after_{action}")
            elif action is None:
                # Model explicitly chose to do nothing
                consecutive_none_actions += 1
                logger.info(f"Model chose to do nothing (count: {consecutive_none_actions})")
                
                # If we've been stuck doing nothing for too long, try a default action
                if consecutive_none_actions > max_none_actions:
                    # Try pressing A to get unstuck
                    fallback_action = "A"
                    logger.warning(f"Too many consecutive 'do nothing' actions. Trying fallback action: {fallback_action}")
                    emulator.send_input(fallback_action)
                    consecutive_none_actions = 0  # Reset counter
                    
                    # Wait for action to complete
                    delay = determine_delay(game_config, fallback_action)
                    time.sleep(delay)
                else:
                    # Still wait a short delay to allow the game to progress
                    delay = game_config.get('action_delay', 0.5) / 2  # Half the normal delay
                    logger.debug(f"Waiting {delay:.2f}s with no action")
                    time.sleep(delay)
                
                # Save the frame after the delay if enabled
                if save_frames:
                    after_frame = emulator.get_frame()
                    save_frame(after_frame, session_frames_dir, turn_count, "after_none")
            else:
                # Could not parse a valid action
                logger.warning(f"Could not parse action: {action_text}")
                # Reset consecutive none action counter since we attempted a real action
                consecutive_none_actions = 0
            
            # Increment turn counter
            turn_count += 1
            
            # Auto-save session if enabled
            if enable_session_save and turn_count % auto_save_interval == 0:
                save_session(session_save_dir, game_name, turn_count, agent, last_frame)
                
    except KeyboardInterrupt:
        logger.info("Game loop interrupted by user")
        
        # Save session on interrupt if enabled
        if enable_session_save:
            save_session(session_save_dir, game_name, turn_count, agent, last_frame)
    finally:
        # Clean up
        emulator.close()
        logger.info(f"Game ended after {turn_count} turns")

if __name__ == "__main__":
    main()