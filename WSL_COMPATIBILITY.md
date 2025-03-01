# Windows WSL Compatibility Guide for EmuVLM

This document provides guidance for running EmuVLM on Windows WSL (Windows Subsystem for Linux), addressing platform-specific considerations and optimizations.

## Overview

EmuVLM supports two VLM (Vision Language Model) backends:

1. **vLLM with Qwen2.5-VL (NVIDIA GPU required)**: The recommended implementation for WSL with NVIDIA GPUs.
2. **llama.cpp with Qwen2-VL (Cross-platform)**: Alternative implementation for systems without NVIDIA GPUs.

On WSL with NVIDIA GPUs, the system automatically selects the vLLM backend.

## Prerequisites

- Windows 10/11 with WSL2 enabled
- For GPU acceleration: NVIDIA GPU with CUDA support installed in WSL
- Python 3.8+ (3.10 recommended)
- Game Boy/GBC ROMs (legally obtained)

## Installation on WSL

### Quick Setup

We provide a setup script that automates most of the installation process:

```bash
# Clone the repository if you haven't already
git clone https://github.com/yourusername/emuvlm.git
cd emuvlm

# Make the setup script executable
chmod +x setup_wsl.sh

# Run the setup script (will install dependencies and configure for WSL)
./setup_wsl.sh
```

### Manual Setup

If you prefer to set up manually, follow these steps:

1. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install EmuVLM with development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

3. Install SDL dependencies for PyBoy:
   ```bash
   sudo apt-get update
   sudo apt-get install -y libsdl2-dev libsdl2-ttf-dev
   ```

4. Install vLLM (for GPU support):
   ```bash
   pip install vllm
   ```

5. Make the vLLM server script executable:
   ```bash
   chmod +x emuvlm/start_vllm_server.sh
   ```

## Installing Emulators

The easiest way to install the emulators is to use the provided script:
```bash
./install_emulators.sh
```

This interactive script will guide you through installing various emulators.

## Using with Qwen2.5-VL-3B-Instruct-AWQ

1. Start the vLLM server with Qwen2.5-VL-3B-Instruct-AWQ:
   ```bash
   ./emuvlm/start_qwen_vllm_server.sh
   ```

2. In a new terminal, run the built-in demo or your own ROM:
   ```bash
   # Run the demo game
   emuvlm-demo
   
   # Or run with your own ROM
   emuvlm --game /path/to/pokemon.gb
   ```

## GPU Acceleration in WSL

The vLLM backend automatically uses NVIDIA GPU acceleration in WSL if available. The setup script configures everything needed to use the GPU with Qwen2.5-VL-3B-Instruct-AWQ.

To verify your GPU is being used:
1. Start the vLLM server
2. In another terminal, run `nvidia-smi` to see if the Python process appears in the list of GPU processes

## Troubleshooting

### CUDA/GPU Issues
- Make sure NVIDIA drivers are properly installed in WSL
- Verify CUDA is working by running `nvidia-smi`
- If you encounter GPU memory issues, adjust `--tensor-parallel-size` in the vLLM server script

### Missing Libraries
- If you encounter SDL-related errors, make sure SDL libraries are installed: `sudo apt-get install -y libsdl2-dev libsdl2-ttf-dev`
- For other library errors, check the error message and install the required libraries

### Performance Tips
- Close unnecessary applications to free up system resources
- For memory-constrained systems, use the llama.cpp backend instead: `emuvlm-llama-server`

## Known Limitations

- Some emulators may require additional configuration
- Performance may vary based on your Windows/WSL configuration and hardware
- File access between Windows and WSL can sometimes cause path issues

For additional help, check the main README.md or open an issue on GitHub.