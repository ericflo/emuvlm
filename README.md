# EMU-VLM: LLM-Powered Turn-Based Game Player

A Python-based AI agent that plays classic turn-based video games through emulators, using the **Qwen2.5-VL-3B-Instruct** vision-language model to analyze game screens and decide which buttons to press. The system connects directly to emulator APIs to capture screenshots and send inputs.

## Key Features

- **Multi-Platform Emulation:** Supports Game Boy/GBC (via PyBoy) and GBA (via mGBA+mGBA-http)
- **Direct Emulator Integration:** Captures frames and sends inputs through APIs, not screen scraping
- **Vision-Language Model Control:** Uses Qwen2.5-VL to "see" and understand game screens
- **Optional Memory:** Can maintain summaries of game progress to remember context
- **Configurable Timing:** Adapts to different game speeds with customizable delays

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
- `start_vllm_server.sh` - Helper to launch the vLLM server

## Configuration

The `config.yaml` file allows you to:
- Set model parameters (API URL, temperature, etc.)
- Configure games with specific ROMs, emulators, and button sets
- Adjust timing parameters per game

## Extending

To add a new game:
1. Add an entry to `config.yaml` with the ROM path, emulator type, and actions
2. If adding a new emulator type, implement a new class that extends `GameEmulator`

For more details, see the full documentation in the original README and PLAN.md.