# macOS Compatibility Guide for EmuVLM

This document provides guidance for running EmuVLM on macOS systems, addressing platform-specific considerations and optimizations.

## Overview

EmuVLM supports two VLM (Vision Language Model) backends:

1. **vLLM with Qwen2.5-VL (Linux only)**: The original implementation which requires CUDA.
2. **llama.cpp with LLaVA (Cross-platform)**: Implementation that works on macOS, Linux, and Windows.

On macOS, the system automatically uses the llama.cpp backend.

## Installation on macOS

1. Install system dependencies:
   ```bash
   # Install Homebrew if not already installed
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   
   # Install SDL2 for PyBoy
   brew install sdl2 sdl2_ttf
   ```

2. Install EmuVLM with macOS-specific dependencies:
   ```bash
   # Clone the repository
   git clone https://github.com/yourusername/emuvlm.git
   cd emuvlm
   
   # Install with macOS dependencies
   pip install -e ".[macos]"
   ```

3. Download the LLaVA model:
   ```bash
   emuvlm-download-model
   ```

## Metal GPU Acceleration

The llama.cpp backend automatically uses Metal GPU acceleration on Apple Silicon and compatible Intel Macs, providing good performance for LLM inference.

To check if Metal acceleration is working:
1. Start the server with verbose output: `emuvlm-llama-server --verbose`
2. Look for "Metal" in the logs to confirm it's being used

## Emulator Compatibility

The following emulators are supported on macOS:

- **PyBoy**: Game Boy/Game Boy Color emulator (fully supported)
- **mGBA**: Game Boy Advance emulator (requires building from source)
- **FCEUX**: NES emulator (available via Homebrew)
- **Snes9x**: SNES emulator (available via Homebrew)
- **Genesis Plus GX**: Sega Genesis emulator (partial support)
- **Mupen64Plus**: Nintendo 64 emulator (available via Homebrew)
- **DuckStation**: PlayStation emulator (available as standalone app)

### Installing emulators on macOS

The easiest way to install the emulators is to use the provided script:
```bash
./install_emulators.sh
```

## Troubleshooting

### Metal Acceleration Issues
- If you encounter errors related to Metal, make sure your macOS is updated to the latest version
- For Intel Macs, check if your GPU supports Metal

### Performance Tips
- Reduce the context size if you encounter memory issues: `emuvlm-llama-server --ctx 1024`
- Reduce the number of GPU layers for older hardware: `emuvlm-llama-server --gpu-layers 24`

## Known Limitations

- The vLLM backend is not available on macOS
- Some emulators may require additional configuration or building from source
- Performance will vary based on Mac hardware (M1/M2/M3 series perform best)

For additional help, check the main README.md or open an issue on GitHub.