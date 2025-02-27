# EmuVLM

EmuVLM (Emulator Vision-Language Model) is a Python framework that combines emulators and vision-language models (VLMs) to play turn-based games. The system uses vision capabilities of the VLM to analyze game screens and decide on optimal in-game actions.

## Features

- Support for Game Boy, Game Boy Color (via PyBoy) and Game Boy Advance (via mGBA) emulators
- Integration with Qwen2.5-VL vision-language model
- Frame caching to reduce redundant model calls and improve performance
- Session management for saving and resuming gameplay
- Dynamic timing system that adjusts delays based on context
- Enhanced logging with frame capture for debugging
- Demo mode with built-in simple game (no ROM required)
- Monitoring interface for viewing and intervening in gameplay

## Installation

### Prerequisites

#### System Requirements
- Linux (Ubuntu 20.04+, Debian 11+) or macOS (12.0+)
- CUDA-compatible GPU with at least 16GB VRAM (for vLLM server with Qwen2.5-VL model)
- 16GB RAM minimum, 32GB recommended
- 25GB free disk space (mostly for model storage)

#### Python Environment
- Python 3.8+ (3.10 recommended)
- pip 21.0+
- virtualenv or conda (recommended for environment isolation)

#### Required Python Packages
- torch>=2.0.0
- numpy>=1.20.0
- pillow>=9.0.0
- opencv-python>=4.5.0
- requests>=2.25.0
- pyyaml>=6.0
- tqdm>=4.62.0
- imagehash>=4.3.0
- psutil>=5.9.0

#### Emulator Dependencies
- For PyBoy (Game Boy/Game Boy Color):
  - SDL2 development libraries
  - NumPy
  - PyPNG
  - PySDL2
  
- For mGBA (Game Boy Advance):
  - Qt5 development libraries
  - SDL2 development libraries
  - libzip development libraries
  - CMake (build dependency)

#### VLM Requirements
- vLLM server (v0.2.5+)
- Qwen2.5-VL-3B-Instruct model
- HuggingFace Transformers (4.35.0+)

### Platform-Specific Installation Instructions

#### Linux (Ubuntu/Debian)

1. **Install system dependencies**
   ```bash
   # For PyBoy
   sudo apt update
   sudo apt install -y python3-dev python3-pip python3-venv libsdl2-dev
   
   # For mGBA
   sudo apt install -y build-essential cmake libzip-dev libsdl2-dev qtbase5-dev libqt5opengl5-dev
   ```

2. **Set up Python environment**
   ```bash
   python3 -m venv emuvlm-env
   source emuvlm-env/bin/activate
   pip install --upgrade pip setuptools wheel
   ```

3. **Install PyBoy**
   ```bash
   pip install pyboy==1.6.1
   ```

4. **Install mGBA Python bindings**
   ```bash
   git clone https://github.com/mgba-emu/mgba.git
   cd mgba
   mkdir build && cd build
   cmake -DCMAKE_INSTALL_PREFIX=/usr/local -DBUILD_PYTHON=ON ..
   make -j$(nproc)
   sudo make install
   cd ../..
   ```

5. **Install CUDA and PyTorch** (for GPU support)
   ```bash
   # For CUDA 12.1
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
   ```

6. **Install vLLM and set up Qwen2.5-VL model**
   ```bash
   pip install vllm==0.2.5
   # Download model (requires huggingface-cli)
   pip install huggingface_hub
   huggingface-cli download Qwen/Qwen2.5-VL-3B-Instruct --local-dir ./models/Qwen2.5-VL-3B-Instruct
   ```

7. **Install EmuVLM**
   ```bash
   git clone https://github.com/yourusername/emuvlm.git
   cd emuvlm
   pip install -e .
   ```

#### macOS

1. **Install system dependencies**
   ```bash
   # Install Homebrew if not already installed
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   
   # For PyBoy
   brew install sdl2 sdl2_ttf
   
   # For mGBA
   brew install cmake qt5 sdl2 libzip
   # Link Qt5 (needed for build process)
   export PATH="/usr/local/opt/qt@5/bin:$PATH"
   ```

2. **Set up Python environment**
   ```bash
   python3 -m venv emuvlm-env
   source emuvlm-env/bin/activate
   pip install --upgrade pip setuptools wheel
   ```

3. **Install PyBoy**
   ```bash
   pip install pyboy==1.6.1
   ```

4. **Install mGBA Python bindings**
   ```bash
   git clone https://github.com/mgba-emu/mgba.git
   cd mgba
   mkdir build && cd build
   cmake -DCMAKE_INSTALL_PREFIX=/usr/local -DBUILD_PYTHON=ON -DCMAKE_PREFIX_PATH=$(brew --prefix qt5) ..
   make -j$(sysctl -n hw.ncpu)
   sudo make install
   cd ../..
   ```

5. **Install PyTorch**
   ```bash
   pip install torch torchvision torchaudio
   ```

6. **Install vLLM and set up Qwen2.5-VL model**
   ```bash
   pip install vllm==0.2.5
   # Download model (requires huggingface-cli)
   pip install huggingface_hub
   huggingface-cli download Qwen/Qwen2.5-VL-3B-Instruct --local-dir ./models/Qwen2.5-VL-3B-Instruct
   ```

7. **Install EmuVLM**
   ```bash
   git clone https://github.com/yourusername/emuvlm.git
   cd emuvlm
   pip install -e .
   ```

### Verifying Installation

To verify that your installation is working correctly:

1. Start the vLLM server as described in the "Starting the VLM Server" section
2. Run the demo game (no ROMs required):
   ```bash
   emuvlm-demo
   ```
3. Test your model connection:
   ```bash
   emuvlm-test-model --image test_data/sample_screen.png
   ```
   If you don't have a test image, you can use the demo to generate one first.

### Troubleshooting

#### Common Issues

1. **PyBoy Installation Errors**
   - **Problem**: SDL2 initialization errors
   - **Solution**: Ensure SDL2 libraries are properly installed with `sudo apt install libsdl2-dev libsdl2-ttf-dev` (Linux) or `brew install sdl2 sdl2_ttf` (macOS)
   
   - **Problem**: "No module named 'pyboy'"
   - **Solution**: Verify installation with `pip show pyboy`, reinstall if needed with `pip install pyboy==1.6.1`

2. **mGBA Compilation Issues**
   - **Problem**: Qt5 not found during cmake
   - **Solution**: Install Qt5 and set CMAKE_PREFIX_PATH, e.g., `-DCMAKE_PREFIX_PATH=$(brew --prefix qt5)` on macOS
   
   - **Problem**: libzip not found
   - **Solution**: Install libzip-dev with `sudo apt install libzip-dev` (Linux) or `brew install libzip` (macOS)

3. **vLLM Server Errors**
   - **Problem**: CUDA out of memory
   - **Solution**: Reduce batch size or try a smaller model variant
   
   - **Problem**: Model not found
   - **Solution**: Verify the model path is correct and that all files were properly downloaded
   
   - **Problem**: "Cannot connect to vLLM server"
   - **Solution**: Check that the server is running on the expected host and port (default: http://localhost:8000)

4. **Python Version Conflicts**
   - **Problem**: ModuleNotFoundError or version conflicts
   - **Solution**: Use a fresh virtual environment with `python -m venv emuvlm-env && source emuvlm-env/bin/activate`

#### Additional Resources

If you encounter persistent issues:
- Check the project GitHub Issues page
- Consult the documentation for [PyBoy](https://github.com/Baekalfen/PyBoy), [mGBA](https://mgba.io/), [vLLM](https://github.com/vllm-project/vllm), or [Qwen2.5-VL](https://github.com/QwenLM/Qwen2-VL) depending on where the problem lies
- Run with debug logging: `emuvlm --debug`

## Usage

### Starting the VLM Server

First, start the VLM server with the Qwen2.5-VL model:

```bash
emuvlm-vllm-server
```

This will start a vLLM server with the Qwen2.5-VL-3B-Instruct model on port 8000.

### Playing a Game

To play a game defined in your config:

```bash
emuvlm --game pokemon_red --summary on
```

Or directly using a ROM path:

```bash
emuvlm --game /path/to/your/rom.gb
```

Additional options:
- `--summary on/off`: Enable/disable game state summarization
- `--cache on/off`: Enable/disable frame caching
- `--max-turns N`: Set maximum number of turns
- `--session PATH`: Resume a saved session
- `--config PATH`: Specify a custom config file

### Demo Mode

Try the built-in demo game (no ROM required):

```bash
emuvlm-demo
```

### Monitor Mode

To monitor and interact with a game manually:

```bash
emuvlm-monitor --game pokemon_red
```

### Testing Tools

Test emulator implementations:

```bash
emuvlm-test-emulators --rom /path/to/rom.gb --emulator pyboy
```

Test the VLM model with a specific image:

```bash
emuvlm-test-model --image /path/to/game_screenshot.png
```

## Configuration

You can configure games, model parameters, and more in the `config.yaml` file:

```yaml
model:
  api_url: "http://localhost:8000"
  summary_interval: 10
  max_tokens: 100
  temperature: 0.2
  enable_cache: true
  cache_dir: "cache"
  similarity_threshold: 0.95

games:
  pokemon_red:
    rom: "/path/to/PokemonRed.gb"
    emulator: "pyboy"
    actions: ["Up", "Down", "Left", "Right", "A", "B", "Start", "Select"]
    action_delay: 0.5
    timing:
      menu_nav_delay: 0.3
      battle_anim_delay: 1.5
      text_scroll_delay: 0.8
```

## Project Structure

```
emuvlm/
├── __init__.py         - Package initialization
├── cli.py              - Command-line interface
├── play.py             - Main game playing logic
├── monitor.py          - GUI monitor for games
├── demo_game.py        - Simple built-in demo game
├── test_emulators.py   - Emulator testing utilities
├── test_model.py       - VLM testing utilities
├── config.yaml         - Default configuration
├── start_vllm_server.sh - Script to start VLM server
├── emulators/          - Emulator implementations
│   ├── __init__.py
│   ├── base.py         - Base emulator interface
│   ├── pyboy_emulator.py - Game Boy emulator implementation
│   └── mgba_emulator.py - Game Boy Advance emulator implementation
└── model/              - AI model components
    ├── __init__.py
    └── agent.py        - VLM agent implementation
```

## Advanced Features

### Frame Caching

The system uses image hashing and similarity detection to avoid repeated VLM calls for similar frames, significantly improving performance.

### Session Management

Save gameplay progress and resume later:

```bash
# Save happens automatically at intervals, or press Ctrl+C
# Resume a session
emuvlm --session sessions/pokemon_red_20240227_123456.session
```

### Dynamic Timing

The system adjusts delay times between actions based on context:
- Shorter delays for menu navigation
- Longer delays for battle animations
- Medium delays for text scrolling

## License

MIT License

## Acknowledgments

- [PyBoy](https://github.com/Baekalfen/PyBoy) - Game Boy emulator
- [mGBA](https://mgba.io/) - Game Boy Advance emulator
- [Qwen2.5-VL](https://github.com/QwenLM/Qwen2-VL) - Vision-language model
- [vLLM](https://github.com/vllm-project/vllm) - LLM inference engine

For more details on implementation and design decisions, see `PLAN.md`.
For current development status and upcoming features, see `TODO.md`.