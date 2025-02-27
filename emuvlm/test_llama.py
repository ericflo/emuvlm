"""
Test script for the llama.cpp integration on macOS.
This allows testing the LLaVA model with llama.cpp for game playing.
"""

import os
import sys
import argparse
import logging
import yaml
import time
import json
import re
from pathlib import Path
from PIL import Image

# Import directly since this file is already in the emuvlm package

from emuvlm.model.agent import LLMAgent
from emuvlm.model.llama_cpp import server as llama_cpp_server

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config

# Global agent variable for accessing from main()
_agent = None

def test_llama(config_path: str, model_path: str, test_image: str, actions: list = None, port: int = 8000, 
             start_server: bool = True, test_loading_detection: bool = False):
    """
    Test the llama.cpp integration with a single image.
    
    Args:
        config_path: Path to config.yaml
        model_path: Path to GGUF model file
        test_image: Path to test image file
        actions: Optional list of valid actions
        port: Port to use for the API server
        start_server: Whether to start the server before testing
        test_loading_detection: Whether to test the loading screen detection
    """
    global _agent
    
    # Load config
    config = load_config(config_path)
    
    # Override model settings for testing
    config['model']['backend'] = 'llama.cpp'
    config['model']['model_path'] = model_path
    config['model']['api_url'] = f"http://localhost:{port}"
    config['model']['autostart_server'] = start_server
    
    # Set valid actions
    if actions is None:
        actions = ["Up", "Down", "Left", "Right", "A", "B", "Start", "Select"]
    
    # Create agent - this will auto-start the server if needed
    logger.info(f"Creating LLMAgent with llama.cpp backend at {config['model']['api_url']}")
    
    # Add "None" option to actions for testing
    if "None" not in actions:
        actions.append("None")
    logger.info(f"Valid actions including None: {', '.join(actions)}")
    
    _agent = LLMAgent(config['model'], actions, use_summary=False)
    
    # For any test, override the system prompt to be more specific
    if "controller_test" in test_image.lower():
        system_msg = f"""You are an AI playing a turn-based video game.
Analyze the game screen and decide the best action to take next.
You can choose from these actions: {', '.join(actions)}.

I'm showing you an image of a controller layout. Read any instructions on the screen 
and select the button that is highlighted or mentioned in the instructions.

You MUST respond ONLY with a JSON object in this EXACT format, with no other text:
{{
  "action": "Up",
  "reasoning": "I'm choosing Up because the Up directional button is highlighted in yellow, and the text says 'Press UP to move character'."
}}

Where "action" is EXACTLY one of: {', '.join(actions)}"""
        
        # Apply the custom system message
        _agent.custom_system_message = system_msg
        logger.info("Using custom system message for controller test")
    
    # Pokemon-specific testing
    elif "pokemon" in test_image.lower():
        system_msg = f"""You are an AI playing a Pokémon game (Pokémon Red, Blue, or Yellow).
Analyze the game screen and decide the best action to take next.
You can choose from these actions: {', '.join(actions)}.

IMPORTANT INSTRUCTION ABOUT POKÉMON GAMEPLAY:
- Press A to advance through dialog text and make selections in menus
- Use Up/Down to navigate menus, and Left/Right to change pages sometimes
- Press B to cancel or go back
- Press Start to open the game menu
- In battles, choose Attack, Pokémon, Item, or Run using directional keys and A to select

IMPORTANT INSTRUCTION ABOUT "NONE":
- If you see a loading screen, choose "None"
- If text is still appearing (being typed out), choose "None"
- If an animation is playing, choose "None"
- Only press buttons when it's clearly required by the game state

POKÉMON-SPECIFIC EXAMPLES:
1. If you see a battle menu with options like "FIGHT", "PKMN", "ITEM", "RUN", navigate with directional buttons and select with A
2. If you see dialog text that has finished appearing, press A to continue
3. If you see dialog text still being typed out, choose "None" and wait
4. If you're in the overworld, use directional buttons to navigate
5. If you see a menu, use Up/Down to navigate and A to select

You MUST respond ONLY with a JSON object in this EXACT format, with no other text:
{{
  "action": "A",
  "reasoning": "I'm pressing A to select the attack option in this Pokémon battle. The battle menu is open and my cursor is on the attack option."
}}

or

{{
  "action": "None",
  "reasoning": "I'm choosing to do nothing because the text is still appearing on screen and I should wait until it's finished."
}}

Where "action" is EXACTLY one of: {', '.join(actions)}"""
        
        # Apply the custom system message
        _agent.custom_system_message = system_msg
        logger.info("Using custom system message for Pokemon test")
    
    # Special handling for do-nothing tests
    elif "do_nothing" in test_image.lower() or "none" in test_image.lower() or "loading" in test_image.lower():
        system_msg = f"""You are an AI playing a turn-based video game.
Analyze the game screen and decide the best action to take next.
You can choose from these actions: {', '.join(actions)}.

I am showing you a game screen with text on it. READ THE TEXT VERY CAREFULLY.

CRITICAL INSTRUCTION: This is a loading screen that tells you NOT to press any buttons.
When you see a loading screen, warning, or text that tells you to wait,
you MUST choose "None" to indicate you should do nothing.

The screen has text that reads:
- "LOADING SCREEN - DO NOT PRESS BUTTONS"
- "LOADING..."
- "Wait for loading to complete"

When you see ANY of these texts, the ONLY correct action is "None".

You MUST respond ONLY with a JSON object in this EXACT format, with no other text:
{{
  "action": "None",
  "reasoning": "I'm choosing to do nothing because the screen shows 'LOADING SCREEN - DO NOT PRESS BUTTONS' and tells me to wait for loading to complete."
}}

Where "action" is EXACTLY one of: {', '.join(actions)}"""
        
        # Increase temperature for more diverse responses
        config['model']['temperature'] = 0.7
        
        # Apply the custom system message
        _agent.custom_system_message = system_msg
        logger.info("Using custom system message for do-nothing test")
    
    # Load test image
    image = Image.open(test_image)
    
    # Test loading screen detection if requested
    if test_loading_detection:
        logger.info("Testing loading screen detection...")
        is_loading = _agent._is_loading_screen(image)
        logger.info(f"Loading screen detection result: {is_loading}")
        
        # Get more detailed image statistics
        gray = image.convert('L')
        pixels = list(gray.getdata())
        unique_colors = len(set(pixels))
        logger.info(f"Image statistics: {unique_colors} unique colors in grayscale")
        
        # If detected as loading screen, return None without asking the model
        if is_loading:
            logger.info("Loading screen detected automatically, returning None action")
            return None
    
    # Get action recommendation
    logger.info(f"Sending test image to model: {test_image}")
    start_time = time.time()
    
    action = _agent.decide_action(image)
    
    elapsed_time = time.time() - start_time
    logger.info(f"Model response time: {elapsed_time:.2f} seconds")
    logger.info(f"Model recommended action: {action}")
    
    return action

def main():
    """Main entry point for testing llama.cpp integration."""
    parser = argparse.ArgumentParser(description="Test llama.cpp integration")
    parser.add_argument("--config", type=str, default="config.yaml", help="Path to config file")
    parser.add_argument("--model", type=str, required=True, help="Path to GGUF model file")
    parser.add_argument("--image", type=str, help="Path to test image file")
    parser.add_argument("--actions", type=str, default=None, help="Comma-separated list of valid actions")
    parser.add_argument("--server", action="store_true", help="Start a standalone server for testing")
    parser.add_argument("--port", type=int, default=8000, help="Port for the server (default: 8000)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind the server to")
    parser.add_argument("--no-autostart", action="store_true", help="Don't automatically start the server")
    parser.add_argument("--test-loading", action="store_true", help="Test the loading screen detection logic")
    
    args = parser.parse_args()
    
    # Verify model file exists
    if not os.path.exists(args.model):
        logger.error(f"Model file not found: {args.model}")
        sys.exit(1)
        
    # Process actions
    action_list = None
    if args.actions:
        action_list = [a.strip() for a in args.actions.split(",")]
    
    # If server flag is set, just start a standalone server
    if args.server:
        print(f"Starting llama.cpp server with model: {args.model}")
        try:
            llama_cpp_server.start_server(
                model_path=args.model,
                host=args.host,
                port=args.port,
                n_gpu_layers=-1,
                n_ctx=2048,
                verbose=True,
                multimodal=True  # Enable multimodal support for LLaVA
            )
            
            print(f"Server running at http://{args.host}:{args.port}")
            print("API endpoints available:")
            print(f"  - http://{args.host}:{args.port}/v1/chat/completions")
            print(f"  - http://{args.host}:{args.port}/v1/models")
            print("Press Ctrl+C to stop...")
            # Keep the server running until interrupted
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping server...")
        except Exception as e:
            print(f"Error starting server: {e}")
            sys.exit(1)
        finally:
            llama_cpp_server.stop_server()
            
    else:
        # For image mode, we need an image file
        if not args.image:
            # Try to use a default test image if available
            test_images = [
                "output/test_images/controller_test.png",
                "output/test_images/pokemon_battle.png"
            ]
            
            for img in test_images:
                if os.path.exists(img):
                    args.image = img
                    break
            
            if not args.image:
                logger.error("No image file specified and no default test images found")
                sys.exit(1)
                
        # Verify image file exists
        if not os.path.exists(args.image):
            logger.error(f"Image file not found: {args.image}")
            sys.exit(1)
        
        # Run test with image
        try:
            action = test_llama(
                args.config, 
                args.model, 
                args.image, 
                action_list, 
                port=args.port,
                start_server=not args.no_autostart,
                test_loading_detection=args.test_loading
            )
            # Try to get the original JSON response before parsing
            raw_response = None
            if hasattr(_agent, '_last_raw_response'):
                raw_response = _agent._last_raw_response
            
            # If action is empty, let's indicate that the default fallback worked
            if not action or action.strip() == "":
                print(f"\nModel returned empty response, defaulting to 'Up'")
            else:
                print(f"\nFinal result: Model recommends action '{action}'")
                
                # Always print the raw response for debugging
                print("\nRaw response:")
                
                # Clean up the raw response to make it more readable
                clean_response = raw_response
                if raw_response:
                    # Remove the control sequences that might be present
                    clean_response = re.sub(r'<\|.*?\|>', '', raw_response)
                    # Truncate if too long
                    if len(clean_response) > 500:
                        clean_response = clean_response[:500] + "... [truncated]"
                
                print(clean_response)
                
                # If we have a JSON response, print it nicely
                if raw_response and raw_response.strip().startswith('{') and raw_response.strip().endswith('}'):
                    try:
                        json_response = json.loads(raw_response)
                        print("\nJSON Response:")
                        print(json.dumps(json_response, indent=2))
                        
                        # Show reasoning if available
                        if 'reasoning' in json_response:
                            print(f"\nModel reasoning: {json_response['reasoning']}")
                    except json.JSONDecodeError:
                        print("Failed to parse as JSON")
        except Exception as e:
            print(f"Error during testing: {e}")
            raise
        finally:
            # Always make sure to clean up
            llama_cpp_server.stop_server()

if __name__ == "__main__":
    main()