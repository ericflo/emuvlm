"""
Command-line interface for EmuVLM.
"""
import argparse
import os
import logging
import importlib
import sys
import subprocess

logger = logging.getLogger(__name__)

def main():
    """Main entry point for the emuvlm command."""
    from emuvlm.play import main as play_main
    play_main()

def demo():
    """Entry point for the emuvlm-demo command."""
    # Import here to avoid circular imports
    demo_spec = importlib.util.find_spec("emuvlm.demo_game")
    if demo_spec is None:
        print("Demo module not found. Make sure the package is installed correctly.")
        sys.exit(1)
    
    from emuvlm.demo_game import main as demo_main
    demo_main()

def monitor():
    """Entry point for the emuvlm-monitor command."""
    # Import here to avoid circular imports
    from emuvlm.monitor import main as monitor_main
    monitor_main()

def test_emulators():
    """Entry point for the emuvlm-test-emulators command."""
    # Import here to avoid circular imports
    from emuvlm.test_emulators import main as test_emulators_main
    test_emulators_main()

def test_model():
    """Entry point for the emuvlm-test-model command."""
    # Import here to avoid circular imports
    from emuvlm.test_model import main as test_model_main
    test_model_main()

def start_vllm_server():
    """Entry point for the emuvlm-vllm-server command."""
    # Get the path to the start_vllm_server.sh script
    script_path = os.path.join(os.path.dirname(__file__), "start_vllm_server.sh")
    
    # Make sure the script exists and is executable
    if not os.path.exists(script_path):
        print(f"vLLM server script not found at {script_path}")
        sys.exit(1)
    
    # Make the script executable if it's not already
    if not os.access(script_path, os.X_OK):
        os.chmod(script_path, 0o755)
    
    # Execute the script
    subprocess.run([script_path], check=True)

if __name__ == "__main__":
    main()