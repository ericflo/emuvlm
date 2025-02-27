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

- Python 3.8+
- For Game Boy / Game Boy Color games: PyBoy
- For Game Boy Advance games: mGBA
- For the VLM component: vLLM with Qwen2.5-VL-3B-Instruct model

### Install from source

```bash
git clone https://github.com/yourusername/emuvlm.git
cd emuvlm
pip install -e .
```

This will install the EmuVLM package and its dependencies, making the command-line tools like `emuvlm`, `emuvlm-demo`, etc. available in your environment.

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