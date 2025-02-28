"""
Tests for the LLM agent.
"""
import pytest
import json
import base64
import io
from unittest.mock import MagicMock, patch
from PIL import Image

from emuvlm.model.agent import LLMAgent


class TestLLMAgent:
    """Tests for the LLM agent."""
    
    def test_initialization(self):
        """Test agent initialization with various configurations."""
        # Basic initialization
        model_config = {
            "api_url": "http://localhost:8000",
            "temperature": 0.2,
            "max_tokens": 100
        }
        valid_actions = ["Up", "Down", "Left", "Right", "A", "B"]
        
        agent = LLMAgent(model_config, valid_actions)
        
        assert agent.api_url == "http://localhost:8000"
        assert agent.valid_actions == valid_actions
        assert agent.use_summary is False
        assert agent.enable_cache is True
        
        # With summary enabled
        agent = LLMAgent(model_config, valid_actions, use_summary=True)
        assert agent.use_summary is True
        assert agent.summary == ""
        
        # With cache disabled
        model_config["enable_cache"] = False
        agent = LLMAgent(model_config, valid_actions)
        assert agent.enable_cache is False
    
    def test_parse_action(self):
        """Test parsing of model responses into valid actions."""
        model_config = {"api_url": "http://localhost:8000"}
        valid_actions = ["Up", "Down", "Left", "Right", "A", "B", "Start", "Select"]
        agent = LLMAgent(model_config, valid_actions)
        
        # Direct matches
        assert agent.parse_action("Up") == "Up"
        assert agent.parse_action("a") == "A"  # Case insensitive
        assert agent.parse_action("LEFT") == "Left"  # Case insensitive
        
        # Contextual matches
        assert agent.parse_action("Press A to select") == "A"
        assert agent.parse_action("Go left to exit") == "Left"
        assert agent.parse_action("Move down to the next option") == "Down"
        assert agent.parse_action("Push B to cancel") == "B"
        
        # Invalid actions - should now return None instead of "Up"
        assert agent.parse_action("Invalid action") is None
        assert agent.parse_action("Jump") is None  # Not in valid_actions
    
    @patch('requests.post')
    def test_decide_action(self, mock_post, sample_frame):
        """Test the decision making process with API calls."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "A"
                    }
                }
            ]
        }
        mock_post.return_value = mock_response
        
        # Create agent
        model_config = {"api_url": "http://localhost:8000"}
        valid_actions = ["Up", "Down", "Left", "Right", "A", "B"]
        agent = LLMAgent(model_config, valid_actions)
        
        # Test decide_action
        result = agent.decide_action(sample_frame)
        assert result == "A"
        assert mock_post.called
        
        # Extract and verify the request payload
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        
        assert 'messages' in payload
        assert payload['temperature'] == 0.2  # Default value
        assert payload['max_tokens'] == 200  # Default value
    
    def test_frame_comparison(self, sample_frame):
        """Test that frame comparison logic works correctly."""
        model_config = {
            "api_url": "http://localhost:8000",
            "enable_cache": True
        }
        valid_actions = ["Up", "Down", "Left", "Right", "A", "B"]
        
        with patch.object(LLMAgent, '_query_model') as mock_query, \
             patch.object(LLMAgent, '_save_frame_to_cache') as mock_save:
            # Setup the mock to return a known response
            mock_query.return_value = "A"
            
            # Create agent with caching enabled
            agent = LLMAgent(model_config, valid_actions)
            
            # First call should query the model
            result1 = agent.decide_action(sample_frame)
            assert result1 == "A"
            assert mock_query.call_count == 1
            
            # Second call with same frame should still query the model
            # (since we removed the cached action feature)
            result2 = agent.decide_action(sample_frame)
            assert result2 == "A"
            assert mock_query.call_count == 2
            
            # Call with a different frame should query the model again
            different_frame = Image.new('RGB', (160, 144), color='white')
            result3 = agent.decide_action(different_frame)
            assert result3 == "A"
            assert mock_query.call_count == 3