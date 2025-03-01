# EmuVLM

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![GitHub issues](https://img.shields.io/github/issues/ericflo/emuvlm)](https://github.com/ericflo/emuvlm/issues)
[![GitHub stars](https://img.shields.io/github/stars/ericflo/emuvlm)](https://github.com/ericflo/emuvlm/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/ericflo/emuvlm)](https://github.com/ericflo/emuvlm/network)
[![GitHub contributors](https://img.shields.io/github/contributors/ericflo/emuvlm)](https://github.com/ericflo/emuvlm/graphs/contributors)
[![Last Commit](https://img.shields.io/github/last-commit/ericflo/emuvlm)](https://github.com/ericflo/emuvlm/commits/main)

EmuVLM lets AI play retro games by "seeing" the game screen and choosing actions. It connects emulators with vision language models (VLMs) that can understand images.

<!--![EmuVLM Demo](https://github.com/ericflo/emuvlm/raw/main/docs/images/demo.gif)-->

## What it does

- 🎮 AI plays Game Boy, Game Boy Color, and other retro games
- 👁️ Uses vision models to analyze game screens and make decisions
- 🧠 Works with multiple AI models (LLaVA, Qwen, MiniCPM)
- 💾 Supports saving/loading game sessions
- 🖥️ Works on macOS, Linux, and Windows (via WSL)

## Quick Start

### Prerequisites

- Python 3.8+ (3.10 recommended)
- Game Boy/GBC ROMs (legally obtained)
- macOS, Linux, or Windows with WSL2

### Installation

```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install EmuVLM
git clone https://github.com/ericflo/emuvlm.git
cd emuvlm
pip install -e .

# Install emulator dependencies
./install_emulators.sh

# Download a model (LLaVA is the default)
emuvlm-download-model
```

### Play Games

1. Start the model server:
   ```bash
   emuvlm-llama-server
   ```

2. Run the built-in demo (no ROM needed):
   ```bash
   emuvlm-demo
   ```

3. Or play with your own ROM:
   ```bash
   emuvlm --game /path/to/pokemon.gb
   ```

## Supported Games

EmuVLM works best with turn-based games:

- **Fully Supported:** Game Boy/GBC games (especially Pokémon, Zelda)
- **Beta Support:** Game Boy Advance, NES, SNES, Genesis, N64, PlayStation

## Configuration

Configure your setup in `config.yaml`:

```yaml
model:
  # Use LLaVA (default), Qwen, or MiniCPM
  model_type: "llava"
  # Adjust temperature (0.0-1.0)
  temperature: 0.2

games:
  pokemon_blue:
    rom: "/path/to/PokemonBlue.gb"
    emulator: "pyboy"
```

## Command Reference

| Command | Description |
|---------|-------------|
| `emuvlm --game pokemon_blue` | Play a configured game |
| `emuvlm-demo` | Run the built-in demo game |
| `emuvlm-llama-server` | Start the model server |
| `emuvlm-download-model` | Download the default model |
| `emuvlm-download-model --model-type qwen` | Download the Qwen model |
| `emuvlm-monitor --game pokemon_blue` | Watch and intervene in gameplay |
| `emuvlm-download-rom --game pokemon` | Create a placeholder ROM |

## Advanced Options

- **Select different model types:**
  ```bash
  emuvlm-download-model --model-type qwen
  emuvlm-llama-server --model-type qwen
  ```

- **Enable game state summarization:**
  ```bash
  emuvlm --game zelda --summary on
  ```

- **Resume a saved session:**
  ```bash
  emuvlm --game pokemon_blue --session path/to/session.session
  ```

## Troubleshooting

- **Model server not starting:** 
  - Check you have enough disk space for the model (~5GB)
  - Make sure you've downloaded the model with `emuvlm-download-model`

- **Game not responding correctly:**
  - Try adjusting timing in config.yaml (action_delay)
  - Make sure your ROM is compatible

- **Installation problems:**
  - Use the install script: `./install_emulators.sh`
  - Check error messages for missing dependencies

- **Platform-specific issues:**
  - For macOS: See [MAC_COMPATIBILITY.md](MAC_COMPATIBILITY.md)
  - For Windows WSL: See [WSL_COMPATIBILITY.md](WSL_COMPATIBILITY.md)

## Project Structure

- `emuvlm/` - Main package
  - `emulators/` - Emulator integrations
  - `model/` - AI model code
  - `cli.py` - Command-line interface
  - `config.yaml` - Default configuration

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add some amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

Please make sure to update tests as appropriate.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [PyBoy](https://github.com/Baekalfen/PyBoy), [mGBA](https://mgba.io/), and other emulator projects
- [LLaVA](https://github.com/haotian-liu/LLaVA), [Qwen](https://github.com/QwenLM/Qwen-VL), and [MiniCPM](https://github.com/OpenBMB/MiniCPM) model creators
- [llama.cpp](https://github.com/ggerganov/llama.cpp) for local model inference

For more details on implementation, see [PLAN.md](PLAN.md).
For platform-specific compatibility details, see:
- [MAC_COMPATIBILITY.md](MAC_COMPATIBILITY.md) for macOS
- [WSL_COMPATIBILITY.md](WSL_COMPATIBILITY.md) for Windows WSL