#!/usr/bin/env python3
"""
Tool for testing the vision-language model with game screenshots.
Useful for prompt engineering and model evaluation.
"""
import argparse
import base64
import io
import json
import logging
import os
import requests
import time
from pathlib import Path
from PIL import Image
from typing import Dict, List, Any, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_image(image_path: str) -> Image.Image:
    """Load an image from disk."""
    return Image.open(image_path)

def encode_image(image: Image.Image) -> str:
    """Convert PIL image to base64 string."""
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def construct_prompt(image_data: str, 
                    valid_actions: List[str], 
                    system_message: Optional[str] = None,
                    user_message: Optional[str] = None) -> Dict[str, Any]:
    """
    Construct a prompt for the model with the given image and messages.
    
    Args:
        image_data: Base64-encoded image
        valid_actions: List of valid actions
        system_message: Custom system message (if None, a default is used)
        user_message: Custom user message (if None, a default is used)
        
    Returns:
        Dict with the complete prompt for the API
    """
    # Format action list for the prompt
    action_list = ", ".join(valid_actions)
    
    # Use default system message if none provided
    if system_message is None:
        system_message = f"""You are an AI playing a turn-based video game.
Analyze the game screen and decide the best action to take next.
You can only choose from these actions: {action_list}.
Respond with just the name of the action (e.g., "A" or "Up") without explanation."""

    # Use default user message if none provided
    if user_message is None:
        user_message = "What action should I take in this game? Choose one of the available actions."
    
    # Construct the full prompt according to vLLM's expected format for Qwen2.5-VL
    messages = [
        {"role": "system", "content": system_message},
        {
            "role": "user", 
            "content": [
                {"type": "image", "image": f"data:image/png;base64,{image_data}"},
                {"type": "text", "text": user_message}
            ]
        }
    ]
    
    return {
        "messages": messages,
        "max_tokens": 100,
        "temperature": 0.2,  # Lower temperature for more focused responses
    }

def query_model(prompt: Dict[str, Any], api_url: str = "http://localhost:8000") -> str:
    """
    Send prompt to the model API and get the response.
    
    Args:
        prompt: Complete prompt for the API
        api_url: URL of the vLLM server
        
    Returns:
        Model's text response
    """
    try:
        # Call vLLM API with OpenAI-compatible endpoint
        response = requests.post(
            f"{api_url}/v1/chat/completions",
            json=prompt,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"API error: {response.status_code} - {response.text}")
            return f"Error: {response.status_code}"
        
        result = response.json()
        # Extract the text from the API response
        try:
            text_response = result["choices"][0]["message"]["content"]
            return text_response.strip()
        except (KeyError, IndexError) as e:
            logger.error(f"Failed to parse API response: {e}")
            return f"Error parsing response: {e}"
            
    except requests.RequestException as e:
        logger.error(f"Request to model API failed: {e}")
        return f"Error: {e}"

def test_model_on_image(image_path: str, 
                       valid_actions: List[str],
                       system_message: Optional[str] = None,
                       user_message: Optional[str] = None,
                       api_url: str = "http://localhost:8000") -> str:
    """
    Test the model on a single image file.
    
    Args:
        image_path: Path to the image file
        valid_actions: List of valid actions
        system_message: Custom system message
        user_message: Custom user message
        api_url: URL of the vLLM server
        
    Returns:
        Model's response
    """
    # Load and encode the image
    image = load_image(image_path)
    image_data = encode_image(image)
    
    # Construct the prompt
    prompt = construct_prompt(
        image_data=image_data,
        valid_actions=valid_actions,
        system_message=system_message,
        user_message=user_message
    )
    
    # Query the model
    logger.info(f"Querying model with image: {image_path}")
    start_time = time.time()
    response = query_model(prompt, api_url)
    elapsed = time.time() - start_time
    
    logger.info(f"Model responded in {elapsed:.2f} seconds: '{response}'")
    return response

def batch_test_directory(directory: str,
                        valid_actions: List[str],
                        system_message: Optional[str] = None,
                        user_message: Optional[str] = None,
                        api_url: str = "http://localhost:8000") -> Dict[str, str]:
    """
    Test the model on all images in a directory.
    
    Args:
        directory: Directory containing image files
        valid_actions: List of valid actions
        system_message: Custom system message
        user_message: Custom user message
        api_url: URL of the vLLM server
        
    Returns:
        Dict mapping filenames to model responses
    """
    results = {}
    
    # Find all image files in the directory
    image_files = []
    for ext in ['.png', '.jpg', '.jpeg']:
        image_files.extend(Path(directory).glob(f'*{ext}'))
    
    # Sort by filename
    image_files.sort()
    
    if not image_files:
        logger.warning(f"No image files found in {directory}")
        return results
    
    logger.info(f"Testing model on {len(image_files)} images from {directory}")
    
    # Process each image
    for img_path in image_files:
        filename = img_path.name
        response = test_model_on_image(
            str(img_path),
            valid_actions,
            system_message,
            user_message,
            api_url
        )
        results[filename] = response
    
    return results

def main():
    parser = argparse.ArgumentParser(description='Test VLM model on game screenshots')
    parser.add_argument('--image', type=str, help='Path to a single image file')
    parser.add_argument('--directory', type=str, help='Directory of images to test')
    parser.add_argument('--actions', type=str, default="Up,Down,Left,Right,A,B,Start,Select",
                      help='Comma-separated list of valid actions')
    parser.add_argument('--system-message', type=str, help='Custom system message')
    parser.add_argument('--user-message', type=str, help='Custom user message')
    parser.add_argument('--api-url', type=str, default="http://localhost:8000", 
                      help='URL of the vLLM server')
    parser.add_argument('--output', type=str, help='Path to save results as JSON')
    
    args = parser.parse_args()
    
    if not args.image and not args.directory:
        parser.error("Either --image or --directory must be specified")
    
    # Parse valid actions
    valid_actions = [a.strip() for a in args.actions.split(',')]
    
    results = {}
    
    # Test single image or directory
    if args.image:
        response = test_model_on_image(
            args.image,
            valid_actions,
            args.system_message,
            args.user_message,
            args.api_url
        )
        results[os.path.basename(args.image)] = response
    
    if args.directory:
        results = batch_test_directory(
            args.directory,
            valid_actions,
            args.system_message,
            args.user_message,
            args.api_url
        )
    
    # Save results if output path provided
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {args.output}")
    
    # Print summary
    logger.info("\nResults Summary:")
    for filename, response in results.items():
        logger.info(f"{filename}: {response}")

if __name__ == "__main__":
    main()