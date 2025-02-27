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
from pathlib import Path
from PIL import Image

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

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

def test_llama(config_path: str, model_path: str, test_image: str, actions: list = None, port: int = 8000, start_server: bool = True):
    """
    Test the llama.cpp integration with a single image.
    
    Args:
        config_path: Path to config.yaml
        model_path: Path to GGUF model file
        test_image: Path to test image file
        actions: Optional list of valid actions
        port: Port to use for the API server
        start_server: Whether to start the server before testing
    """
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
    agent = LLMAgent(config['model'], actions, use_summary=False)
    
    # Load test image
    image = Image.open(test_image)
    
    # Get action recommendation
    logger.info(f"Sending test image to model: {test_image}")
    start_time = time.time()
    
    action = agent.decide_action(image)
    
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
                start_server=not args.no_autostart
            )
            # Try to get the original JSON response before parsing
            raw_response = None
            if hasattr(agent, '_last_raw_response'):
                raw_response = agent._last_raw_response
            
            # If action is empty, let's indicate that the default fallback worked
            if not action or action.strip() == "":
                print(f"\nModel returned empty response, defaulting to 'Up'")
            else:
                print(f"\nFinal result: Model recommends action '{action}'")
                
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
                        pass  # Not valid JSON
        except Exception as e:
            print(f"Error during testing: {e}")
            raise
        finally:
            # Always make sure to clean up
            llama_cpp_server.stop_server()

if __name__ == "__main__":
    main()