#!/bin/bash
# Setup script for EmuVLM on Windows WSL with Qwen2.5-VL-3B-Instruct-AWQ

set -e  # Exit on error

echo "=== EmuVLM WSL Setup Script ==="
echo "This script will set up EmuVLM for Windows WSL with Qwen2.5-VL-3B-Instruct-AWQ"

# 1. Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# 2. Activate virtual environment
source venv/bin/activate

# 3. Install EmuVLM with development dependencies
echo "Installing EmuVLM with development dependencies..."
pip install -e ".[dev]"

# 4. Install SDL dependencies for PyBoy
echo "Installing SDL dependencies for PyBoy..."
sudo apt-get update
sudo apt-get install -y libsdl2-dev libsdl2-ttf-dev

# 5. Install vLLM
echo "Installing vLLM..."
pip install vllm

# 6. Make vLLM server script executable
chmod +x emuvlm/start_vllm_server.sh

echo "Setup complete! You can now:"
echo "1. Install emulators with: ./install_emulators.sh"
echo "2. Start the Qwen2.5-VL-3B-Instruct-AWQ vLLM server: ./emuvlm/start_qwen_vllm_server.sh"
echo "3. Run EmuVLM with your Game Boy ROMs"