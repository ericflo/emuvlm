# EmuVLM

EmuVLM (Emulator Vision-Language Model) is a Python framework that combines emulators and vision-language models (VLMs) to play turn-based games. The system uses vision capabilities of the VLM to analyze game screens and decide on optimal in-game actions.

Our system now supports game-specific configurations that enhance AI gameplay for different game genres, with specialized detection and prompt systems for Pokémon, Zelda, and other game types.

## Features

- Support for multiple gaming platforms with dedicated emulators:
  - Game Boy / Game Boy Color (PyBoy)
  - Game Boy Advance (mGBA)
  - Nintendo Entertainment System (FCEUX)
  - Super Nintendo / SNES (Snes9x)
  - Sega Genesis / Mega Drive (Genesis Plus GX)
  - Nintendo 64 (Mupen64Plus)
  - PlayStation (DuckStation)
- Multi-platform VLM support:
  - Linux: Integration with Qwen2.5-VL via vLLM
  - macOS: Integration with LLaVA via llama.cpp
  - Cross-platform compatibility with automatic backend selection
- Frame caching to reduce redundant model calls and improve performance
- Session management for saving and resuming gameplay
- Dynamic timing system that adjusts delays based on context
- Enhanced logging with frame capture for debugging
- Demo mode with built-in simple game (no ROM required)
- Monitoring interface for viewing and intervening in gameplay
- Game-specific enhancements:
  - Genre-specific instruction prompts (RPG, action-adventure, etc.)
  - Specialized loading screen detection for different game types
  - Game-type configuration system for customized AI behavior
  - Anti-stalling mechanisms to prevent getting stuck

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

**Option 1: vLLM server (Linux recommended)**
- vLLM server (v0.2.5+)
- Qwen2.5-VL-3B-Instruct model
- HuggingFace Transformers (4.35.0+)
- CUDA-compatible GPU with at least 16GB VRAM

**Option 2: llama.cpp (macOS, Windows, Linux)**
- llama-cpp-python (v0.2.50+)
- llama-cpp-python-server (v0.2.0+)
- LLaVA compatible GGUF model (e.g., llava-v1.6-mistral-7b.Q5_K_M.gguf)
- Metal GPU acceleration on macOS (optional but recommended)

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
   pip install pyboy==1.6.0
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

5. **Install other emulator dependencies**
   ```bash
   # The easiest way is to use our helper script
   ./install_emulators.sh
   
   # Or install manually:
   # For NES (FCEUX)
   sudo apt install fceux lua5.1 liblua5.1-dev  # Linux
   brew install fceux lua                       # macOS
   
   # For SNES (Snes9x)
   sudo apt install snes9x-gtk                  # Linux
   brew install snes9x                          # macOS
   
   # For Nintendo 64 (Mupen64Plus)
   sudo apt install mupen64plus-ui-console      # Linux
   brew install mupen64plus                     # macOS
   
   # For PlayStation (DuckStation)
   # Download from: https://github.com/stenzek/duckstation/releases
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

6. **Install llama-cpp-python for macOS compatibility**
   ```bash
   pip install llama-cpp-python>=0.2.50
   ```

7. **Install EmuVLM with macOS dependencies**
   ```bash
   git clone https://github.com/yourusername/emuvlm.git
   cd emuvlm
   pip install -e ".[macos]"  # Install with macOS-specific dependencies
   
   # Download the recommended LLaVA model
   emuvlm-download-model
   ```

Note: macOS users will use llama.cpp with LLaVA model for VLM functions, which is fully supported and optimized for Apple Silicon with Metal GPU acceleration.

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

### Automated Emulator Installation

For convenience, you can use the provided installation script to help install all emulator dependencies:

```bash
./install_emulators.sh
```

This interactive script will:
1. Detect your operating system (Linux or macOS)
2. Install system dependencies for each emulator
3. Guide you through the installation of each emulator (PyBoy, mGBA, FCEUX, Snes9x, Genesis Plus GX, Mupen64Plus, DuckStation)
4. Install required Python packages

After running the script, you can verify your emulator installations using the test script:

```bash
# After editing ROM paths in the script
./scripts/test_emulator_example.sh
```

### Troubleshooting

#### Common Issues

1. **PyBoy Installation Errors**
   - **Problem**: SDL2 initialization errors
   - **Solution**: Ensure SDL2 libraries are properly installed with `sudo apt install libsdl2-dev libsdl2-ttf-dev` (Linux) or `brew install sdl2 sdl2_ttf` (macOS)
   
   - **Problem**: "No module named 'pyboy'"
   - **Solution**: Verify installation with `pip show pyboy`, reinstall if needed with `pip install pyboy==1.6.0`

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

You can start one of the two supported VLM servers:

#### Option 1: vLLM server (Linux)

Start the vLLM server with the Qwen2.5-VL model:

```bash
emuvlm-vllm-server
```

This will start a vLLM server with the Qwen2.5-VL-3B-Instruct model on port 8000.

#### Option 2: llama.cpp server (macOS, Windows, Linux)

Start the llama.cpp server with a LLaVA model:

```bash
# First, download the recommended LLaVA model:
emuvlm-download-model

# Then start the server
emuvlm-llama-server
```

This will start a llama.cpp server with OpenAI-compatible API endpoints on port 8000.

The system will automatically select the appropriate backend based on your platform.

### Playing a Game

To play a game defined in your config:

```bash
emuvlm --game pokemon_blue --summary on
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
# Test a single emulator
emuvlm-test-emulators --rom /path/to/rom.gb --emulator pyboy

# Test all emulators with different ROMs
emuvlm-test-emulators --all \
  --pyboy-rom /path/to/gb_rom.gb \
  --mgba-rom /path/to/gba_rom.gba \
  --fceux-rom /path/to/nes_rom.nes \
  --snes9x-rom /path/to/snes_rom.sfc \
  --genesis-rom /path/to/genesis_rom.md \
  --mupen64plus-rom /path/to/n64_rom.z64 \
  --duckstation-rom /path/to/psx_rom.bin
```

A sample script for testing all emulators is provided in `scripts/test_emulator_example.sh`.

Test the VLM model with a specific image:

```bash
# Test with the default VLM backend
emuvlm-test-model --image /path/to/game_screenshot.png

# Test specifically with llama.cpp backend
emuvlm-test-llama --model /path/to/llava-v1.5-7b-q4_k_s.gguf --image /path/to/game_screenshot.png
```

### Using the ROM Helper Utility

To create placeholder ROMs for testing or download ROMs for legally owned cartridges:

```bash
# Create a placeholder Pokemon ROM for testing
emuvlm-download-rom --game pokemon

# Create a placeholder Zelda ROM for testing
emuvlm-download-rom --game zelda
```

## Configuration

You can configure games, model parameters, and more in the `config.yaml` file:

```yaml
model:
  # Common settings
  api_url: "http://localhost:8000"
  backend: "auto"                   # "auto", "vllm", or "llama.cpp"
  summary_interval: 10
  max_tokens: 100
  temperature: 0.2
  enable_cache: true
  cache_dir: "output/cache"
  similarity_threshold: 0.95
  
  # Response format configuration
  json_schema_support: true         # Whether the model supports JSON schema responses
  max_tokens: 200                   # Increased for JSON responses
  
  # llama.cpp specific settings
  autostart_server: false
  model_path: "/path/to/llava-v1.5-7b-q4_k_s.gguf"
  n_gpu_layers: -1                  # -1 means use all available layers

games:
  pokemon_blue:
    rom: "/path/to/PokemonBlue.gb"
    emulator: "pyboy"
    actions: ["Up", "Down", "Left", "Right", "A", "B", "Start", "Select"]
    action_delay: 0.5
    game_type: "pokemon"            # Game type for specialized handling
    timing:
      menu_nav_delay: 0.3
      battle_anim_delay: 1.5
      text_scroll_delay: 0.8
    settings:
      detect_loading_screens: true  # Enable loading screen detection
      max_blank_frames: 5           # Anti-stalling setting

  zelda_links_awakening:
    rom: "/path/to/ZeldaLinksAwakening.gb"
    emulator: "pyboy"
    actions: ["Up", "Down", "Left", "Right", "A", "B", "Start", "Select"]
    action_delay: 0.4
    game_type: "zelda"              # Game type identifier
    timing:
      menu_nav_delay: 0.3           # Zelda-specific timing
      dialog_delay: 1.0
      screen_transition_delay: 0.7
      item_use_delay: 0.5
    settings:
      detect_loading_screens: true
      frame_analysis: true          # More detailed frame analysis
    prompt_additions:
      - "This is The Legend of Zelda: Link's Awakening for Game Boy."
      - "Press A to use your sword or interact with objects and people."
      - "Press B to use your equipped item."
```

## Project Structure

```
emuvlm/
├── __init__.py          - Package initialization
├── cli.py               - Command-line interface
├── play.py              - Main game playing logic
├── monitor.py           - GUI monitor for games
├── demo_game.py         - Simple built-in demo game
├── test_emulators.py    - Emulator testing utilities
├── test_model.py        - VLM testing utilities
├── config.yaml          - Default configuration
├── utils/               - Utility modules
│   ├── __init__.py
│   └── download_rom.py  - ROM download/creation utility
├── start_vllm_server.sh  - Script to start vLLM server
├── start_llama_server.sh - Script to start llama.cpp server
├── emulators/           - Emulator implementations
│   ├── __init__.py
│   ├── base.py                    - Base emulator interface
│   ├── pyboy_emulator.py          - Game Boy/GBC emulator implementation
│   ├── mgba_emulator.py           - Game Boy Advance emulator implementation
│   ├── fceux_emulator.py          - NES emulator implementation 
│   ├── snes9x_emulator.py         - SNES emulator implementation
│   ├── genesis_plus_gx_emulator.py - Sega Genesis emulator implementation
│   ├── mupen64plus_emulator.py    - Nintendo 64 emulator implementation
│   └── duckstation_emulator.py    - PlayStation emulator implementation
└── model/               - AI model components
    ├── __init__.py
    ├── agent.py         - VLM agent implementation
    └── llama_cpp/       - llama.cpp integration
        ├── __init__.py
        └── server.py    - llama.cpp server management

output/                  - All generated files (gitignored)
├── boot_frames/         - Frames captured during game initialization
├── cache/               - Cached frames for performance optimization
├── debug_frames/        - Debug frames for development
├── logs/                - Log files
│   └── frames/          - Frames captured during gameplay
├── sessions/            - Saved game sessions
└── test_output/         - Test output files and frames
```

Additional scripts:
- `install_emulators.sh` - Helper script to install all emulator dependencies
- `scripts/test_emulator_example.sh` - Example script to test all emulator implementations

## Game-Specific Enhancements

EmuVLM now uses a configuration-driven approach to provide specialized AI behaviors for different game genres.

### Configuration-Driven Game Agents

Instead of hardcoding game-specific logic, we use configuration files to define game behaviors:

```yaml
# In your game config file:
game_type: "pokemon"  # Specifies the game type
prompt_additions:
  - "This is Pokemon Blue for Game Boy, a classic RPG."
  - "Use A to interact and confirm, B to cancel."
  - "During battles, select FIGHT to use moves against opponents."
settings:
  detect_loading_screens: true  # Enable loading screen detection
```

Supported game types include:
- `pokemon` - For Pokemon games (GB, GBC, GBA)
- `zelda` - For Legend of Zelda games
- Additional types can be added as needed

### Pokemon-Specific Improvements

We've enhanced EmuVLM to better handle Pokemon gameplay:

1. **Automatic Loading Screen Detection**
   - Detects loading screens based on image statistics
   - Chooses "None" action automatically without model query
   - Prevents unnecessary actions during transitions

2. **Pokemon-Specific Knowledge**
   - Battle mechanics (FIGHT, PKMN, ITEM, RUN)
   - Dialog handling (wait for text to finish)
   - Menu navigation patterns

3. **Intelligent "None" Action Handling**
   - Improved waiting during text scrolling
   - Better handling of battle animations
   - Specialized delay timing for Pokemon gameplay

### Zelda-Specific Improvements

For action-adventure games like Zelda:

1. **Enhanced Loading Screen Detection**
   - Grid-based screen section analysis for complex transitions
   - Black screen detection for area transitions
   - Tracking of consecutive blank frames

2. **Zelda-Specific Prompting**
   - Instructions for sword combat using A button
   - Guidance for NPC interactions and chest opening
   - Examples of common Zelda gameplay scenarios

3. **Anti-Stalling Mechanisms**
   - Consecutive action tracking
   - Fallback actions when the system gets stuck
   - Customizable thresholds for different game types

## macOS Compatibility

EmuVLM supports two VLM backends:

1. **vLLM with Qwen2.5-VL-3B (Linux)**: The original implementation which requires CUDA.
2. **llama.cpp with LLaVA (macOS, Windows, Linux)**: Implementation that works on any platform, ideal for macOS.

The system automatically selects the appropriate backend based on your platform.

### Using on macOS

1. Install with macOS dependencies:
   ```bash
   pip install -e ".[macos]"
   ```

2. Download the recommended LLaVA model:
   ```bash
   emuvlm-download-model
   ```

3. Start the server:
   ```bash
   emuvlm-llama-server
   ```

4. Play games:
   ```bash
   emuvlm --game pokemon_blue
   ```

## License

MIT License

## Acknowledgments

- [PyBoy](https://github.com/Baekalfen/PyBoy) - Game Boy/Game Boy Color emulator
- [mGBA](https://mgba.io/) - Game Boy Advance emulator
- [FCEUX](https://fceux.com/) - Nintendo Entertainment System emulator
- [Snes9x](https://github.com/snes9xgit/snes9x) - Super Nintendo emulator
- [Genesis Plus GX](https://github.com/ekeeke/Genesis-Plus-GX) - Sega Genesis/Mega Drive emulator
- [Mupen64Plus](https://mupen64plus.org/) - Nintendo 64 emulator
- [DuckStation](https://github.com/stenzek/duckstation) - PlayStation emulator
- [Qwen2.5-VL](https://github.com/QwenLM/Qwen2-VL) - Vision-language model
- [vLLM](https://github.com/vllm-project/vllm) - LLM inference engine
- [llama.cpp](https://github.com/ggerganov/llama.cpp) - Efficient LLM inference
- [LLaVA](https://github.com/haotian-liu/LLaVA) - Large language and vision assistant

For more details on implementation and design decisions, see `PLAN.md`.
For current development status and upcoming features, see `TODO.md`.