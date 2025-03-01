# EmuVLM WSL Setup Instructions

This guide provides step-by-step instructions for setting up EmuVLM on Windows WSL with Qwen2.5-VL-3B-Instruct-AWQ.

## Prerequisites

- Windows 10/11 with WSL2 enabled
- NVIDIA GPU with CUDA support installed in WSL
- Python 3.8+ (3.10 recommended)
- Game Boy/GBC ROMs (legally obtained)

## Setup Steps

1. **Prepare your environment**

   First, ensure you have WSL2 installed with Ubuntu or a similar distribution, and that your NVIDIA drivers are properly installed. You can verify CUDA support by running:

   ```bash
   nvidia-smi
   ```

   If CUDA is properly installed, you should see your GPU listed with details.

2. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/emuvlm.git
   cd emuvlm
   ```

3. **Run the WSL setup script**

   We've created a setup script that automates the installation process:

   ```bash
   # Make the script executable
   chmod +x setup_wsl.sh

   # Run the setup script
   ./setup_wsl.sh
   ```

   This script will:
   - Create a virtual environment
   - Install EmuVLM with development dependencies
   - Install SDL dependencies for PyBoy
   - Install vLLM for GPU support
   - Create a Qwen2.5-VL-3B-Instruct-AWQ specific vLLM server script

4. **Install emulators**

   Install the PyBoy emulator (for Game Boy/GBC games) and other emulators as needed:

   ```bash
   ./install_emulators.sh
   ```

   Follow the interactive prompts to install the emulators you want to use.

5. **Start the vLLM server with Qwen2.5-VL-3B-Instruct-AWQ**

   ```bash
   # Make sure you're in the virtual environment
   source venv/bin/activate

   # Start the Qwen2.5-VL-3B-Instruct-AWQ vLLM server
   ./emuvlm/start_qwen_vllm_server.sh
   ```

   The first time you run this, it will download the Qwen2.5-VL-3B-Instruct-AWQ model, which may take some time depending on your internet connection.

6. **Run EmuVLM with your Game Boy ROMs**

   In a new terminal window (keep the vLLM server running):

   ```bash
   # Make sure you're in the virtual environment
   source venv/bin/activate

   # Run with the WSL test configuration
   emuvlm --config wsl_test_config.yaml --game tetris
   ```

   You can replace `tetris` with other game configurations defined in `wsl_test_config.yaml`, such as `super_mario_land`, `pokemon_blue`, or `kirby_dream_land`.

## Troubleshooting

- **vLLM server fails to start**: Make sure your NVIDIA GPU is properly set up with CUDA in WSL. Check that you have enough GPU memory available.

- **CUDA not found**: Install CUDA in WSL following NVIDIA's documentation.

- **SDL-related errors**: Make sure SDL libraries are installed: `sudo apt-get install -y libsdl2-dev libsdl2-ttf-dev`

- **Cannot find ROM files**: Verify the paths in `wsl_test_config.yaml` match your actual ROM locations.

- **Memory errors**: If you encounter memory issues with larger models, try adjusting the tensor parallelism by modifying the `--tensor-parallel-size` parameter in the vLLM server script.

For more information, see the [WSL_COMPATIBILITY.md](WSL_COMPATIBILITY.md) document.