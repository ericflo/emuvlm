"""
Tests for the command line interface.
"""
import pytest
import sys
from unittest.mock import patch, MagicMock

from emuvlm import cli


class TestCLI:
    """Tests for the CLI module."""
    
    @patch('emuvlm.play.main')
    def test_main(self, mock_play_main):
        """Test the main CLI entry point."""
        cli.main()
        mock_play_main.assert_called_once()
    
    @patch('emuvlm.demo_game.main')
    @patch('importlib.util.find_spec')
    def test_demo(self, mock_find_spec, mock_demo_main):
        """Test the demo command."""
        # Mock that the module exists
        mock_spec = MagicMock()
        mock_find_spec.return_value = mock_spec
        
        cli.demo()
        mock_demo_main.assert_called_once()
    
    @patch('emuvlm.monitor.main')
    def test_monitor(self, mock_monitor_main):
        """Test the monitor command."""
        cli.monitor()
        mock_monitor_main.assert_called_once()
    
    @patch('emuvlm.test_emulators.main')
    def test_test_emulators(self, mock_test_emulators_main):
        """Test the test-emulators command."""
        cli.test_emulators()
        mock_test_emulators_main.assert_called_once()
    
    @patch('emuvlm.test_model.main')
    def test_test_model(self, mock_test_model_main):
        """Test the test-model command."""
        cli.test_model()
        mock_test_model_main.assert_called_once()
    
    @patch('subprocess.run')
    @patch('os.chmod')
    @patch('os.path.exists', return_value=True)
    @patch('os.path.dirname', return_value='/fake/path')
    @patch('os.access', return_value=False)
    def test_start_vllm_server(self, mock_access, mock_dirname, mock_exists, mock_chmod, mock_run):
        """Test the vLLM server start command."""
        # Set up the expected path
        expected_script_path = '/fake/path/start_vllm_server.sh'
        
        cli.start_vllm_server()
        
        # Check that permissions were set
        mock_chmod.assert_called_once_with(expected_script_path, 0o755)
        
        # Check that the script was run
        mock_run.assert_called_once_with([expected_script_path], check=True)