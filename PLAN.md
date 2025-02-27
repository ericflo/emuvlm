# EmuVLM Project Plan and Design Decisions

## Project Overview

EmuVLM (Emulator Vision-Language Model) is designed to create a framework that allows vision-language models (VLMs) to play turn-based video games through emulators. The primary goal is to leverage advanced VLM capabilities to analyze game screens and decide on the optimal actions to take.

The project is structured as a proper Python package with command-line tools that enable users to easily set up and run gameplay sessions, with flexible configuration options.

## Design Principles

1. **Modular Architecture**: Separate emulation, model interface, and game control logic into distinct components that can be extended independently.

2. **Performance Optimization**: Use frame caching and similarity detection to minimize redundant VLM calls.

3. **Adaptability**: Support different emulators and game types with configurable parameters.

4. **User Experience**: Provide monitoring tools and the ability to intervene in gameplay.

## Architecture

### Component Overview

```
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   Emulators   │<───│  Game Player  │───>│   LLM Agent   │
└───────────────┘    └───────────────┘    └───────────────┘
        │                    ↑                    ↑
        ▼                    │                    │
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  Game Frames  │───>│    Monitor    │    │  vLLM Server  │
└───────────────┘    └───────────────┘    └───────────────┘
```

### Package Structure

```
emuvlm/
├── __init__.py         - Package initialization
├── cli.py              - Command-line interface entry points
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

### Key Components

1. **Emulators**: Interfaces for different emulators (PyBoy, mGBA)
   - Base abstraction: `EmulatorBase`
   - Common API for frame capture and input
   - Handles emulator-specific quirks

2. **LLM Agent**: VLM-powered decision-making
   - Frame analysis and action selection
   - Caching system for similar frames
   - Optional game state summarization

3. **Game Player**: Main orchestration
   - Manages game flow and timing
   - Session management
   - Frame logging and debugging

4. **Monitor**: Visualization and intervention
   - Real-time game display
   - Manual input capability
   - Game state visualization

## Implementation Details

### Emulator Abstraction

Each emulator implementation must provide:
- Frame capture (`get_frame()`)
- Input sending (`send_input(action)`)
- Initialization and cleanup

The base class ensures consistent behavior regardless of the underlying emulator.

### Frame Caching System

To improve performance, we implement:
1. Frame hashing: Convert frames to consistent hashes
2. Similarity detection: Compare frames to avoid redundant API calls
3. Cache expiration: Periodically refresh cached decisions

### Session Management

Sessions store:
- Game state summary
- Turn count and progress
- Last frame for visual reference
- Timestamp and metadata

This allows players to resume games later without losing context.

### Dynamic Timing

Games require different timing based on context:
- Menu navigation: Fast (0.3-0.5s)
- Battle animations: Slow (1.5-2.0s)
- Text scrolling: Medium (0.8-1.0s)

The system adjusts delays based on action type and game context.

## Extension Points

### Adding New Emulators

To add support for a new emulator:
1. Create a new class that extends `EmulatorBase`
2. Implement the required methods
3. Add emulator-specific configuration options
4. Register the emulator type in the appropriate factory method

### Supporting New Game Types

Different game types can be supported by:
1. Updating the configuration file
2. Adjusting timing parameters
3. Potentially enhancing the VLM prompt for game-specific behavior

### Command-Line Interface

The CLI design with multiple entry points allows for easy extension:
1. Add new commands by creating new entry point functions in cli.py
2. Register these functions in pyproject.toml's [project.scripts] section
3. Implement the new command's functionality in a dedicated module

## Game-Specific Improvements

To better support different game genres, we've implemented a game-type configuration system that customizes the AI's behavior based on the type of game being played.

### Configuration-Driven Architecture

Each game can specify:
- `game_type`: Identifier for the game category (e.g., "pokemon", "zelda", "final_fantasy")
- Game-specific timing parameters for different contexts
- Custom prompt additions with game-specific instructions
- Detection settings for loading screens and transitions

Example configuration:
```yaml
zelda_links_awakening:
  rom: "/path/to/zelda_links_awakening.gb"
  emulator: "pyboy"
  actions: ["Up", "Down", "Left", "Right", "A", "B", "Start", "Select"]
  action_delay: 0.4
  game_type: "zelda"                # Game type identifier
  timing:
    menu_nav_delay: 0.3             # Zelda-specific menu timing
    dialog_delay: 1.0
    screen_transition_delay: 0.7
    item_use_delay: 0.5
  settings:
    detect_loading_screens: true    # Enable loading screen detection
    frame_analysis: true            # More detailed frame analysis
    max_blank_frames: 5             # Anti-stalling setting
```

### Enhanced Game-Type Specific Features

1. **Loading Screen Detection**:
   - Customized algorithms for different game types
   - Grid-based analysis for complex transitions
   - Black screen detection for area transitions
   - Tracking of consecutive blank frames to prevent stalling

2. **Game-Specific Prompting**:
   - Specialized instructions based on game type
   - Examples tailored to the specific game genre
   - Control guidance based on game mechanics

3. **Anti-Stalling Mechanisms**:
   - Consecutive action tracking
   - Fallback actions when the system gets stuck
   - Customizable thresholds for different game types

## Future Directions

1. **UI Improvements**: Develop a more comprehensive GUI for monitoring and controlling games

2. **Advanced VLM Integration**: Test with more capable models and experiment with custom fine-tuning

3. **ROM Compatibility Enhancement**: Improve emulator compatibility with different ROM formats

4. **State Tracking**: Implement more sophisticated game state tracking beyond basic summaries

5. **Text Recognition**: Add OCR to better understand text boxes and dialog

6. **Multi-Step Planning**: Enable the AI to plan sequences of actions for complex game scenarios

7. **Learning from Gameplay**: Build systems to learn from successful play sessions to improve future performance