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
import atexit
from pathlib import Path
from PIL import Image

from emuvlm.emulators.pyboy_emulator import PyBoyEmulator
from emuvlm.emulators.mgba_emulator import MGBAEmulator
from emuvlm.model.agent import LLMAgent
from emuvlm.utils.rom_loader import cleanup_rom_cache

# Initialize basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("emuvlm")

def setup_logging(config):
    """Configure logging based on config settings."""
    from emuvlm.constants import DEFAULT_LOG_FILE, DEFAULT_FRAMES_DIR
    
    log_config = config.get('logging', {})
    log_level = getattr(logging, log_config.get('level', 'INFO'))
    
    # Create logs directory
    log_file = log_config.get('log_file', DEFAULT_LOG_FILE)
    log_dir = os.path.dirname(log_file)
    os.makedirs(log_dir, exist_ok=True)
    
    # Create frames directory if frame saving is enabled
    if log_config.get('save_frames', False):
        frames_dir = log_config.get('frames_dir', DEFAULT_FRAMES_DIR)
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
    
    The timing system uses a hierarchical approach:
    1. Check for action-specific delay in timing.actions
    2. Check for action-type category delay in timing.categories
    3. Fall back to default action_delay
    
    Args:
        game_config: Game configuration from config file
        action: The action being executed
        
    Returns:
        float: Delay in seconds
    """
    from emuvlm.constants import ACTION_CATEGORIES, DEFAULT_ACTION_DELAYS
    
    # Get timing config if available
    timing = game_config.get('timing', {})
    
    # Default to the general action_delay
    default_delay = game_config.get('action_delay', 1.0)
    
    # Handle None action
    if action is None:
        return timing.get('categories', {}).get('wait', 0.2)
        
    # First check if there's a specific delay defined for this exact action
    action_delays = timing.get('actions', {})
    if action_delays and action in action_delays:
        return action_delays[action]
    
    # Then check for category-based delays
    categories = timing.get('categories', {})
    
    # Map actions to categories
    category = 'default'
    for cat_name, actions in ACTION_CATEGORIES.items():
        if action in actions:
            category = cat_name
            break
    
    # Get delay from game config categories, or default category delays, or default delay
    return categories.get(category, DEFAULT_ACTION_DELAYS.get(category, default_delay))

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
    from emuvlm.constants import VALID_MODEL_TYPES
    parser.add_argument("--model-type", choices=VALID_MODEL_TYPES, default="llava", 
                      help=f"Vision language model type ({', '.join(VALID_MODEL_TYPES)}). Default: llava")
    parser.add_argument('--session-save-interval', type=int, default=None,
                      help='Override auto-save interval from config')
    
    # Add model provider and configuration arguments
    parser.add_argument('--provider', type=str, default=None,
                      help='Model provider (local, openai, anthropic, mistral, custom)')
    parser.add_argument('--model-name', type=str, default=None,
                      help='Model name for the selected provider (e.g., gpt-4o, claude-3-haiku-20240307)')
    parser.add_argument('--api-url', type=str, default=None,
                      help='API URL for the model provider')
    parser.add_argument('--temperature', type=float, default=None,
                      help='Model temperature (0.0 to 1.0)')
    parser.add_argument('--max-tokens', type=int, default=None,
                      help='Maximum tokens for model response')
    
    args = parser.parse_args()
    
    # Load configuration with better path handling
    if os.path.isabs(args.config):
        config_path = args.config
    else:
        # First check if the path is relative to current working directory
        cwd_path = os.path.join(os.getcwd(), args.config)
        if os.path.exists(cwd_path):
            config_path = cwd_path
        else:
            # Then try relative to the script location (package directory)
            package_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), args.config)
            if os.path.exists(package_path):
                config_path = package_path
            else:
                # Finally, fall back to the default config in the package
                config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
                logger.info(f"Using default config at: {config_path}")
    
    config = load_config(config_path)
    
    # Setup logging
    setup_logging(config)
    
    # Session configuration
    from emuvlm.constants import DEFAULT_SESSION_DIR, DEFAULT_AUTO_SAVE_INTERVAL
    
    session_config = config.get('sessions', {})
    enable_session_save = session_config.get('enable_save', False)
    session_save_dir = session_config.get('save_dir', DEFAULT_SESSION_DIR)
    auto_save_interval = args.session_save_interval or session_config.get('auto_save_interval', DEFAULT_AUTO_SAVE_INTERVAL)
    
    # Resume from session if provided
    session_data = None
    starting_turn = 0
    if args.session:
        session_data, _ = load_session(args.session)
        starting_turn = session_data.get('turn_count', 0)
        args.game = session_data.get('game', args.game)
        logger.info(f"Resuming {args.game} from turn {starting_turn}")
    
    # Import constants
    from emuvlm.constants import ROM_EXTENSIONS, DEFAULT_ACTIONS
    
    # Determine which game to play
    if args.game in config['games']:
        game_config = config['games'][args.game]
        game_name = args.game
    else:
        # Assume args.game is a direct path to ROM
        rom_path = args.game
        ext = Path(rom_path).suffix.lower()
        
        # Determine emulator type from file extension
        if ext in ROM_EXTENSIONS:
            emulator_type = ROM_EXTENSIONS[ext]
        else:
            raise ValueError(f"Unsupported ROM type: {ext}")
        
        # Create minimal game config
        game_config = {
            'rom': rom_path,
            'emulator': emulator_type,
            'actions': DEFAULT_ACTIONS,
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
    elif emulator_type == 'gamegear':
        from emuvlm.emulators.gamegear_emulator import GameGearEmulator
        emulator = GameGearEmulator(game_config['rom'])
    else:
        raise ValueError(f"Unsupported emulator: {game_config['emulator']}")
    
    # Initialize LLM agent
    use_summary = args.summary.lower() == 'on'
    
    # Update model config for caching and enable autostart (only for local provider)
    model_config = config.get('model', {}).copy()
    model_config['enable_cache'] = args.cache.lower() == 'on'
    model_config['autostart_server'] = model_config.get('provider', 'local') == 'local'
    
    # Process model type first as it may affect model_name
    if args.model_type is not None:
        from emuvlm.constants import MODEL_PATHS, VALID_MODEL_TYPES
        
        # Validate model type
        if args.model_type not in VALID_MODEL_TYPES:
            logger.warning(f"Unknown model type: {args.model_type}. Valid types are: {', '.join(VALID_MODEL_TYPES)}")
            logger.warning(f"Defaulting to 'llava'")
            args.model_type = "llava"
            
        model_config['model_type'] = args.model_type
        logger.info(f"Using model type from command line: {args.model_type}")
        
        # If model_name is not explicitly provided, update model_path based on model_type
        if not args.model_name and model_config.get('provider', 'local') == 'local':
            # Update model_path if the selected model_type has a defined path
            if args.model_type in MODEL_PATHS:
                # Convert to absolute path if needed
                model_path = MODEL_PATHS[args.model_type]
                if not os.path.isabs(model_path):
                    model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), model_path)
                
                model_config['model_path'] = model_path
                logger.info(f"Using model path based on model type: {model_path}")
    
    # Apply command-line model configuration overrides
    if args.provider:
        model_config['provider'] = args.provider
        logger.info(f"Using provider from command line: {args.provider}")
        
        # Import default API URLs
        from emuvlm.constants import DEFAULT_API_URLS
        
        # Set default API URLs based on provider if not specified
        if not args.api_url and args.provider in DEFAULT_API_URLS:
            model_config['api_url'] = DEFAULT_API_URLS[args.provider]
            logger.info(f"Setting default {args.provider.capitalize()} API URL: {model_config['api_url']}")
        
        # Import API key environment variable names
        from emuvlm.constants import API_KEY_ENV_VARS
        
        # For OpenAI, Anthropic, and Mistral, read API key from environment variable if not in config
        if args.provider in API_KEY_ENV_VARS and not model_config.get('api_key'):
            env_var_name = API_KEY_ENV_VARS.get(args.provider)
            api_key = os.environ.get(env_var_name)
            if api_key:
                model_config['api_key'] = api_key
                logger.info(f"Using API key from environment variable {env_var_name}")
            else:
                logger.warning(f"No API key provided in config or environment variable {env_var_name}")
    
    if args.model_name:
        model_config['model_name'] = args.model_name
        logger.info(f"Using model name from command line: {args.model_name}")
    
    if args.api_url:
        model_config['api_url'] = args.api_url
        logger.info(f"Using API URL from command line: {args.api_url}")
    
    if args.temperature is not None:
        model_config['temperature'] = args.temperature
        logger.info(f"Using temperature from command line: {args.temperature}")
    
    if args.max_tokens is not None:
        model_config['max_tokens'] = args.max_tokens
        logger.info(f"Using max tokens from command line: {args.max_tokens}")
    
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
                logger.info("Model chose to do nothing")
                
                # Wait a short delay to allow the game to progress
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
        
        # Clean up extracted ROM files
        cleanup_rom_cache()

# Register cleanup for extracted ROM files even if the program is terminated
atexit.register(cleanup_rom_cache)

if __name__ == "__main__":
    main()