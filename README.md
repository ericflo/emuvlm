# EMU-VLM: LLM-Powered Turn-Based Game Player

A Python-based AI agent that plays classic turn-based video games through emulators, using the **Qwen2.5-VL-3B-Instruct** vision-language model to analyze game screens and decide which buttons to press. The system connects directly to emulator APIs to capture screenshots and send inputs.

## Key Features

- **Multi-Platform Emulation:** Supports Game Boy/GBC (via PyBoy) and GBA (via mGBA+mGBA-http)
- **Direct Emulator Integration:** Captures frames and sends inputs through APIs, not screen scraping
- **Vision-Language Model Control:** Uses Qwen2.5-VL to "see" and understand game screens
- **Frame Caching:** Optimizes performance by caching model decisions for similar frames
- **Optional Memory:** Maintains summaries of game progress to remember context
- **Configurable Timing:** Adapts to different game speeds with customizable delays
- **Session Management:** Save and load game sessions for later continuation
- **Detailed Logging:** Captures frames and actions for debugging and analysis

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up emulators:**
   - PyBoy is installed via pip (included in requirements)
   - For GBA games, install mGBA and mGBA-http separately

3. **Start the vLLM server:**
   ```bash
   ./start_vllm_server.sh
   ```

4. **Edit config.yaml** with your ROM paths and settings

5. **Run the AI player:**
   ```bash
   ./play_game.py --game pokemon_red --summary off
   ```

## Command Line Options

```bash
# Basic usage
./play_game.py --game pokemon_red

# Enable game state summarization
./play_game.py --game pokemon_red --summary on

# Disable frame caching
./play_game.py --game pokemon_red --cache off

# Limit the number of turns
./play_game.py --game pokemon_red --max-turns 100

# Resume from a saved session
./play_game.py --session sessions/pokemon_red_20250227_120000.session

# Custom configuration file
./play_game.py --game pokemon_red --config my_config.yaml
```

## Testing Emulators

To verify the emulator connections work correctly:

```bash
# Test PyBoy
./test_emulators.py --emulator pyboy --rom /path/to/pokemon_red.gb --buttons Start,A,Down

# Test mGBA (must have mGBA and mGBA-http running first)
./test_emulators.py --emulator mgba --rom /path/to/pokemon_emerald.gba --buttons Start,A,B
```

## Project Structure

- `play_game.py` - Main script to run the AI player
- `emulators/` - Emulator interface implementations
- `model/` - LLM agent for analyzing frames and making decisions
- `config.yaml` - Configuration for games and model settings
- `test_emulators.py` - Script to test emulator connections
- `demo_game.py` - Test with predefined action sequences
- `test_model.py` - Prompt engineering experiments
- `monitor_game.py` - GUI for visualizing gameplay
- `start_vllm_server.sh` - Helper to launch the vLLM server
- `sessions/` - Saved game sessions
- `cache/` - Cached frames and model decisions
- `logs/` - Log files and captured frames

## Configuration

The `config.yaml` file allows you to:
- Set model parameters (API URL, temperature, etc.)
- Configure frame caching and similarity thresholds
- Define logging behavior and paths
- Configure games with specific ROMs, emulators, and button sets
- Set game-specific timing parameters for different contexts (menus, battles, etc.)
- Configure session saving/loading behavior

## Advanced Features

### Frame Caching

The system caches model decisions for similar frames to reduce API calls and improve response time. This is especially useful for repetitive game screens like menus or battle sequences. The similarity threshold can be adjusted in the configuration file.

### Session Management

Games can be saved and resumed using the session management feature. The system automatically saves game state at configurable intervals and can be resumed from any saved point.

### Dynamic Timing

Each game can have custom timing configurations for different contexts, allowing for faster navigation in menus but longer delays during battle animations or text scrolling.

## Extending

To add a new game:
1. Add an entry to `config.yaml` with the ROM path, emulator type, and actions
2. Configure game-specific timing parameters
3. If adding a new emulator type, implement a new class that extends `GameEmulator`

For more details on implementation and design decisions, see `PLAN.md`.
For current development status and upcoming features, see `TODO.md`.