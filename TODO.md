# EmuVLM TODO List

## High Priority

- [x] Create formal package for EmuVLM (with pyproject.toml) for easier installation ✨
- [ ] Test with real Pokémon Red and Emerald ROMs
- [ ] Refine model prompts for more accurate action decisions in battle sequences
- [x] Add unit tests for core functionality ✨
- [x] Create example configuration for common games ✨
- [x] Add detailed installation instructions for all dependencies ✨
- [x] Verify command-line tools work correctly when installed via pip ✨

## Medium Priority

- [ ] Add support for additional emulators (SNES, NDS, etc.)
- [ ] Implement better OCR for text boxes to improve model context
- [ ] Create a GUI configuration editor for editing config.yaml
- [ ] Add support for alternative VLMs (Claude, GPT-4V, etc.) 
- [ ] Create a detailed documentation site with examples
- [ ] Add support for save states in emulators
- [ ] Implement visualization dashboard for model decision-making
- [ ] Create launcher script with ROM browser UI

## Low Priority

- [ ] Implement advanced game state tracking
- [ ] Create automated benchmark tests for different VLMs
- [ ] Add support for recording gameplay as video
- [ ] Create a web UI for remote monitoring and control
- [ ] Explore fine-tuning VLMs specifically for game play
- [ ] Investigate reinforcement learning integration
- [ ] Add multi-modal prompting with audio input from games

## Completed ✅

- [x] Implement core emulator interfaces for PyBoy
- [x] Implement core emulator interfaces for mGBA
- [x] Create base LLM agent with Qwen2.5-VL integration
- [x] Implement frame caching with similarity detection
- [x] Create session management for saving/resuming games
- [x] Implement dynamic timing system
- [x] Add enhanced logging with frame capture
- [x] Create monitor interface for visualization
- [x] Build demo game mode for testing without ROMs
- [x] Create comprehensive configuration system
- [x] Implement vLLM server launcher
- [x] Restructure project as a proper Python package
- [x] Add CLI entry points for all tools
- [x] Update documentation for package structure