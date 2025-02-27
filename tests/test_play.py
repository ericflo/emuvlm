"""
Tests for the main game playing functionality.
"""
import pytest
import os
import yaml
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path

from emuvlm.play import (
    load_config, 
    setup_logging, 
    determine_delay, 
    save_session, 
    load_session
)


class TestPlayModule:
    """Tests for the play module functions."""
    
    def test_load_config(self):
        """Test loading configuration from YAML."""
        mock_config = """
        model:
          api_url: http://localhost:8000
          temperature: 0.2
        games:
          pokemon:
            rom: roms/pokemon.gbc
            emulator: pyboy
            actions: [Up, Down, Left, Right, A, B, Start, Select]
        """
        
        with patch("builtins.open", mock_open(read_data=mock_config)):
            config = load_config("config.yaml")
            
            assert "model" in config
            assert config["model"]["api_url"] == "http://localhost:8000"
            assert "games" in config
            assert "pokemon" in config["games"]
            assert config["games"]["pokemon"]["rom"] == "roms/pokemon.gbc"
    
    def test_determine_delay(self):
        """Test the delay determination logic."""
        # Basic game config
        game_config = {
            "action_delay": 1.0
        }
        
        # Default delay
        assert determine_delay(game_config, "A") == 1.0
        
        # With timing configuration
        game_config["timing"] = {
            "menu_nav_delay": 0.5,
            "battle_anim_delay": 2.0,
            "text_scroll_delay": 0.3
        }
        
        # Test different actions
        assert determine_delay(game_config, "Up") == 0.5
        assert determine_delay(game_config, "Down") == 0.5
        assert determine_delay(game_config, "A") == 2.0
        assert determine_delay(game_config, "B") == 0.3
        assert determine_delay(game_config, "Start") == 1.0  # Uses default
    
    @patch("os.makedirs")
    def test_save_session(self, mock_makedirs):
        """Test saving a game session."""
        session_dir = "sessions"
        game_name = "pokemon"
        turn_count = 10
        
        # Mock agent
        mock_agent = MagicMock()
        mock_agent.summary = "Player has started the game and chosen Bulbasaur."
        
        # Mock frame
        mock_frame = MagicMock()
        
        with patch("builtins.open", mock_open()) as mock_file, \
             patch("json.dump") as mock_json_dump, \
             patch("PIL.Image.Image.save") as mock_save:
             
            session_file = save_session(session_dir, game_name, turn_count, mock_agent, mock_frame)
            
            # Check that directories were created
            mock_makedirs.assert_called_once_with(session_dir, exist_ok=True)
            
            # Check that JSON was saved
            assert mock_json_dump.called
            args, _ = mock_json_dump.call_args
            session_data = args[0]
            assert session_data["game"] == game_name
            assert session_data["turn_count"] == turn_count
            assert "summary" in session_data
            
            # Check that the frame was saved
            assert mock_save.called
    
    def test_load_session(self):
        """Test loading a game session."""
        # Mock session data
        mock_session_data = {
            "game": "pokemon",
            "turn_count": 10,
            "timestamp": "20250227_123456",
            "summary": "Player has started the game and chosen Bulbasaur."
        }
        
        with patch("builtins.open", mock_open()) as mock_file, \
             patch("json.load", return_value=mock_session_data) as mock_json_load, \
             patch("os.path.exists", return_value=True), \
             patch("PIL.Image.open") as mock_image_open:
             
            session_data, last_frame = load_session("sessions/pokemon.session")
            
            # Check that JSON was loaded
            assert mock_json_load.called
            assert session_data == mock_session_data
            
            # Check that the frame was loaded
            assert mock_image_open.called