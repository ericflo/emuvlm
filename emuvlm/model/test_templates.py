"""
Test the template rendering system.
"""
import os
from jinja2 import Environment, FileSystemLoader
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_system_prompt_template():
    """Test rendering the system prompt template."""
    # Get the templates directory path
    templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
    
    # Setup Jinja environment
    jinja_env = Environment(loader=FileSystemLoader(templates_dir))
    
    # Load the system prompt template
    template = jinja_env.get_template("system_prompt.j2")
    
    # Test data for template
    test_data = {
        "action_list": "A, B, Up, Down, Left, Right, Start, Select",
        "valid_actions_with_none": "A, B, Up, Down, Left, Right, Start, Select, None",
        "game_specific_instructions": "This is a test game. Press A to test.",
        "custom_instructions": "These are some custom instructions for testing.",
        "backend": "llama.cpp",
        "summary": "The player has moved to the next level."
    }
    
    # Render the template
    rendered = template.render(**test_data)
    
    # Print the rendered template
    logger.info("Rendered system prompt template:")
    logger.info(rendered)
    
    # Verify the template contains key elements
    assert "AVAILABLE ACTIONS:" in rendered
    assert "You can choose from these actions:" in rendered
    assert "CRITICAL GUIDANCE FOR \"NONE\" ACTION:" in rendered
    assert "RESPONSE FORMAT:" in rendered
    assert "game_summary" in rendered
    
    # Test with vLLM backend
    test_data["backend"] = "vllm"
    rendered_vllm = template.render(**test_data)
    
    logger.info("\nRendered vLLM system prompt template:")
    logger.info(rendered_vllm)
    
    # Verify the vLLM template contains key elements
    assert "AVAILABLE ACTIONS:" in rendered_vllm
    assert "You can choose from these actions:" in rendered_vllm
    assert "CRITICAL GUIDANCE FOR \"NONE\" ACTION:" in rendered_vllm
    assert "RESPONSE FORMAT:" in rendered_vllm
    assert "game_summary" in rendered_vllm

def test_reasoning_prompt_template():
    """Test rendering the reasoning prompt template."""
    # Get the templates directory path
    templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
    
    # Setup Jinja environment
    jinja_env = Environment(loader=FileSystemLoader(templates_dir))
    
    # Load the reasoning prompt template
    template = jinja_env.get_template("reasoning_prompt.j2")
    
    # Test with different game types
    game_types = ["pokemon", "zelda", "final_fantasy", "rpg", "action", "unknown_game"]
    
    for game_type in game_types:
        # Render the template
        rendered = template.render(game_type=game_type)
        
        # Print the rendered template
        logger.info(f"\nRendered reasoning prompt for {game_type}:")
        if rendered.strip():
            logger.info(rendered)
            
            # Verify each game type has appropriate content
            if game_type == "pokemon":
                assert "BATTLE ANALYSIS" in rendered
                assert "MENU NAVIGATION" in rendered
                assert "DIALOGUE INTERPRETATION" in rendered
            elif game_type in ["zelda", "action"]:
                assert "SPATIAL AWARENESS" in rendered
                assert "COMBAT ASSESSMENT" in rendered
                assert "PUZZLE ELEMENTS" in rendered
            elif game_type in ["rpg", "final_fantasy"]:
                assert "CHARACTER ASSESSMENT" in rendered
                assert "BATTLE TACTICS" in rendered
                assert "EXPLORATION OBJECTIVES" in rendered
            elif game_type == "unknown_game":
                assert "VISUAL SCENE ASSESSMENT" in rendered
                assert "INTERACTIVE ELEMENTS" in rendered
                assert "GAME STATE ANALYSIS" in rendered
        else:
            logger.info(f"No specific reasoning prompt for {game_type}")
            # Should not happen with our current set of templates
            assert False, f"Missing template for game type: {game_type}"

def main():
    """Main entry point for the emuvlm-test-templates command."""
    # Run the tests
    test_system_prompt_template()
    test_reasoning_prompt_template()
    
    logger.info("\nAll template tests completed successfully!")
    return 0  # Returning 0 is standard for CLI tools to indicate success

if __name__ == "__main__":
    main()