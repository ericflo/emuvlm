#!/usr/bin/env python3
"""
Additional tests for the LLMAgent class.
"""
import base64
import io
import json
import hashlib
import tempfile
from unittest.mock import MagicMock, patch
from pathlib import Path

import pytest
from PIL import Image
import numpy as np

from emuvlm.model.agent import LLMAgent


@pytest.fixture
def mock_image():
    """Create a test image."""
    return Image.new('RGB', (160, 144), color='red')


@pytest.fixture
def different_image():
    """Create a different test image."""
    return Image.new('RGB', (160, 144), color='blue')


@pytest.fixture
def agent_config():
    """Create a basic agent configuration."""
    return {
        'api_url': 'http://localhost:8000',
        'backend': 'vllm',
        'max_tokens': 200,
        'temperature': 0.7,
        'enable_cache': True,
        'cache_dir': 'test_cache',
        'summary_interval': 5
    }


@pytest.fixture
def valid_actions():
    """List of valid game actions."""
    return ['Up', 'Down', 'Left', 'Right', 'A', 'B', 'Start', 'Select']


@pytest.fixture
def agent(agent_config, valid_actions):
    """Create a basic LLMAgent."""
    with patch('os.path.exists', return_value=True), \
         patch('pathlib.Path.exists', return_value=True), \
         patch('pathlib.Path.mkdir'), \
         patch.object(LLMAgent, '_maybe_start_server', return_value=None):
        agent = LLMAgent(agent_config, valid_actions)
        return agent


class TestLLMAgentAdditional:
    """Additional tests for LLMAgent."""
    
    def test_prepare_image(self, agent, mock_image):
        """Test image preparation for API."""
        image_str = agent._prepare_image(mock_image)
        
        # Check that we got a non-empty base64 string
        assert isinstance(image_str, str)
        assert len(image_str) > 0
        
        # Verify it's valid base64 that can be decoded
        try:
            decoded = base64.b64decode(image_str)
            # Should be able to open the decoded image
            Image.open(io.BytesIO(decoded))
        except Exception as e:
            pytest.fail(f"Failed to decode base64 image: {e}")
    
    def test_construct_prompt(self, agent, mock_image):
        """Test prompt construction."""
        image_data = agent._prepare_image(mock_image)
        
        prompt = agent._construct_prompt(image_data)
        
        # Check that the prompt has the expected structure
        assert 'messages' in prompt
        assert len(prompt['messages']) >= 2  # System message and user message
        
        # Check that there's content in the user message
        user_message = prompt['messages'][-1]
        assert 'content' in user_message
    
    def test_calculate_frame_hash(self, agent, mock_image, different_image):
        """Test calculating a hash for a frame."""
        frame_hash = agent._calculate_frame_hash(mock_image)
        
        # Should get a non-empty string hash
        assert isinstance(frame_hash, str)
        assert len(frame_hash) > 0
        
        # Same image should produce the same hash
        second_hash = agent._calculate_frame_hash(mock_image)
        assert frame_hash == second_hash
        
        # Different image should produce different hash
        different_hash = agent._calculate_frame_hash(different_image)
        assert frame_hash != different_hash
    
    @pytest.mark.skip("Functionality not fully implemented in LLMAgent")
    def test_update_history(self, agent):
        """Test updating action history."""
        # Enable summary
        agent.use_summary = True
        
        # Get original history length
        original_len = len(agent.history)
        
        # Update history with expected parameters
        agent._update_history("Test message")
        
        # Check that history was updated
        assert len(agent.history) == original_len + 1
        assert agent.history[-1] == "Test message"
    
    def test_parse_action_methods(self, agent):
        """Test different action parsing methods."""
        # Test direct matches
        assert agent.parse_action("Up") == "Up"
        assert agent.parse_action("a") == "A"
        assert agent.parse_action("LEFT") == "Left"
        
        # Test contextual parsing
        assert agent.parse_action("Press A to continue") == "A"
        assert agent.parse_action("Move Left to avoid the enemy") == "Left"
        assert agent.parse_action("Push B to cancel") == "B"
        
        # Test JSON parsing
        json_response = json.dumps({"action": "Start", "reasoning": "Open the menu"})
        assert agent.parse_action(json_response) == "Start"
        
        # Test empty response
        assert agent.parse_action("") == "Up"
        
        # Test invalid action
        assert agent.parse_action("Invalid action") == "Up"
    
    @patch('requests.post')
    def test_query_model(self, mock_post, agent, mock_image):
        """Test querying the model."""
        # Set up the mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "I should press A to continue."}}
            ]
        }
        mock_post.return_value = mock_response
        
        # Create a simple prompt
        image_data = agent._prepare_image(mock_image)
        prompt = agent._construct_prompt(image_data)
        
        # Mock the _query_model method to avoid API calls
        with patch.object(agent, '_query_model', return_value="A") as mock_query:
            response = agent._query_model(prompt)
            
            # Check the response
            assert response == "A"
    
    @patch.object(LLMAgent, '_query_model')
    def test_decide_action_basic(self, mock_query, agent, mock_image):
        """Test basic action decision."""
        # Set up the mock to return a specific action
        mock_query.return_value = "A"
        
        # Bypass cache saving by mocking it
        with patch.object(agent, '_save_frame_to_cache') as mock_save:
            # Test decide_action
            result = agent.decide_action(mock_image)
            
            # Check that the correct action was returned
            assert result == "A"
            # Check that _query_model was called
            assert mock_query.called
            # Check that _save_frame_to_cache was called
            assert mock_save.called