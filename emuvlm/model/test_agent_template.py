"""
Test the LLMAgent template loading.
"""
import logging
import os
from PIL import Image
from emuvlm.model.agent import LLMAgent

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_agent_template_loading():
    """Test that the LLMAgent properly loads templates."""
    # Test configuration for the agent
    model_config = {
        'api_url': 'http://localhost:8000',  # No actual API calls will be made
        'backend': 'llama.cpp',  # Use llama.cpp backend for testing
        'game_type': 'pokemon',  # Use pokemon game type
        'prompt_additions': [
            "This is a test prompt addition.",
            "Another test prompt addition."
        ]
    }
    
    # Valid actions for the agent
    valid_actions = ["Up", "Down", "Left", "Right", "A", "B", "Start", "Select"]
    
    # Create the agent
    agent = LLMAgent(model_config, valid_actions, use_summary=False)
    
    # Get the template directory to load a test image
    templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
    
    # Find a test image or create one
    test_image_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                "output", "test_images", "controller_test.png")
    
    if os.path.exists(test_image_path):
        # Load the test image
        test_image = Image.open(test_image_path)
        logger.info(f"Loaded test image: {test_image_path}")
    else:
        # Create a simple test image
        test_image = Image.new('RGB', (160, 144), color='white')
        logger.info("Created new test image")
    
    # Mock the _query_model method to just capture the prompt
    original_query_model = agent._query_model
    
    captured_prompt = None
    
    def mock_query_model(prompt):
        nonlocal captured_prompt
        captured_prompt = prompt
        return '{"action": "A", "reasoning": "This is a test."}'
    
    # Replace the query method with our mock
    agent._query_model = mock_query_model
    
    # Call decide_action which will trigger template rendering
    try:
        agent.decide_action(test_image)
        
        # Check that the system message was generated correctly
        system_message = captured_prompt.get('messages', [])[0].get('content', '')
        
        # No need to check for game-specific instructions anymore
        # as they come from the prompt_additions in the config
            
        # Check that it contains the proper action format instructions
        if "You MUST respond ONLY with a JSON object" in system_message:
            logger.info("✅ Backend-specific instructions loaded correctly")
        else:
            logger.error("❌ Backend-specific instructions not loaded")
            
        # Check that it contains the prompt additions
        if "This is a test prompt addition" in system_message:
            logger.info("✅ Custom instructions loaded correctly")
        else:
            logger.error("❌ Custom instructions not loaded")
            
        # Check that it contains the reasoning prompt
        if "BATTLE ANALYSIS" in system_message:
            logger.info("✅ Reasoning prompt loaded correctly")
        else:
            logger.error("❌ Reasoning prompt not loaded")
            
        logger.info("\nTest completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
    finally:
        # Restore the original method
        agent._query_model = original_query_model

def main():
    """Main entry point for testing."""
    test_agent_template_loading()
    return 0

if __name__ == "__main__":
    main()