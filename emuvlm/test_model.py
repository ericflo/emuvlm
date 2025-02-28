#!/usr/bin/env python3
"""
Test script for the LLM agent.
"""
import argparse
import logging
import sys
import os
import json
import time
from pathlib import Path
from PIL import Image

from emuvlm.model.agent import LLMAgent

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("emuvlm.test_model")

def test_agent_with_image(agent, image_path):
    """
    Test the LLM agent with a specific image file.
    
    Args:
        agent: Initialized LLMAgent instance
        image_path: Path to the image file to test with
    """
    logger.info(f"Testing agent with image: {image_path}")
    
    # Verify image path exists
    assert os.path.exists(image_path), f"Image file not found: {image_path}"
    
    # Load the image
    image = Image.open(image_path)
    logger.info(f"Image size: {image.size}")
    
    # Record start time
    start_time = time.time()
    
    # Ask the agent to decide an action
    try:
        action_text = agent.decide_action(image)
        elapsed_time = time.time() - start_time
        
        logger.info(f"Agent response: '{action_text}' (took {elapsed_time:.2f}s)")
        
        # Try to parse the action
        parsed_action = agent.parse_action(action_text)
        logger.info(f"Parsed action: {parsed_action}")
        
        # Verify we got a response
        assert action_text is not None, "Agent returned None for action_text"
        
        # We don't need to store the result anywhere for pytest
        # Pytest just needs the assertions to pass
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"Error during model test: {e}")
        
        # Fail the test with an assertion
        assert False, f"Model test failed with error: {e}"

def main():
    """Main entry point for the model test script."""
    parser = argparse.ArgumentParser(description='Test the LLM agent')
    parser.add_argument('--image', type=str, required=True, help='Path to the test image file')
    parser.add_argument('--api-url', type=str, default='http://localhost:8000', help='URL of the model API')
    parser.add_argument('--output', type=str, default='output/test_output/model_test_results.json', help='Path to save results')
    args = parser.parse_args()
    
    # Validate image file
    image_path = args.image
    if not os.path.exists(image_path):
        logger.error(f"Image file not found: {image_path}")
        return 1
    
    # Create output directory if needed
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # Initialize the LLM agent
    try:
        model_config = {
            'api_url': args.api_url,
            'temperature': 0.2,
            'max_tokens': 100,
            'enable_cache': False  # Disable caching for tests
        }
        
        # Create a list of typical game actions
        valid_actions = ['Up', 'Down', 'Left', 'Right', 'A', 'B', 'Start', 'Select']
        
        logger.info(f"Initializing LLM agent with API at {args.api_url}")
        agent = LLMAgent(model_config, valid_actions)
        
        # Run the test
        try:
            # Just call the test function directly
            test_agent_with_image(agent, image_path)
            
            # If we get here, the test passed
            logger.info("Test completed successfully")
            
            # Create a simple result dictionary for CLI output
            result = {
                "image_path": image_path,
                "success": True,
                "message": "Test passed"
            }
            
            # Save the result if requested
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
                
            logger.info(f"Test results saved to {args.output}")
            return 0
        except AssertionError as e:
            logger.error(f"Test failed with assertion: {e}")
            return 1
        
    except Exception as e:
        logger.error(f"Error during test setup: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())