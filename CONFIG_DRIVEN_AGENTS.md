# Config-Driven Game Agents in EmuVLM

This documentation explains the configuration-driven approach for game-specific AI agents in EmuVLM.

## Overview

Instead of hardcoding game-specific logic in the agent code, we've implemented a configuration-driven approach that:

1. Uses game type identifiers to load appropriate prompts
2. Allows game-specific prompts to be defined in config files
3. Makes features like loading screen detection optional
4. Provides clear, declarative configuration for different game types

## Key Components

### 1. Game Type Configuration

In your game config YAML file, specify a `game_type` to identify the game:

```yaml
# Pokemon Blue config example
game_type: "pokemon"
```

Supported game types include:
- `pokemon` - For Pokemon games (GB, GBC, GBA)
- `zelda` - For Legend of Zelda games
- Additional types can be added as needed

### 2. Prompt Additions

You can provide game-specific prompt additions to guide the AI:

```yaml
prompt_additions:
  - "This is Pokemon Blue for Game Boy, a classic RPG."
  - "Use A to interact and confirm, B to cancel."
  - "During battles, select FIGHT to use moves against opponents."
```

### 3. Loading Screen Detection

Enable automatic loading screen detection with the config:

```yaml
settings:
  detect_loading_screens: true  # Enable loading screen detection
```

When enabled, the agent will:
- Analyze frames for characteristics of loading screens
- Automatically return "None" for loading screens without querying the model
- Log when loading screens are detected

### 4. Game-Specific Timing

Different games have different timing needs:

```yaml
timing:
  menu_nav_delay: 0.3           # Faster for menu navigation
  battle_anim_delay: 1.5        # Longer for battle animations
  text_scroll_delay: 0.8        # Medium for text scrolling
```

## Adding a New Game Type

To add support for a new game type:

1. Create a YAML config file with the appropriate `game_type`
2. In `agent.py`, update the `_construct_prompt` method to include instructions for the new game type
3. Add appropriate `prompt_additions` for the specific game
4. Configure timing parameters appropriate for the game

## Example Usage

Start a Pokemon Blue session with our improved config:

```bash
./test_pokemon_updated.sh
```

This uses the `examples/pokemon_blue_updated.yaml` config which includes:
- Pokemon-specific game type
- Custom prompt additions for Pokemon gameplay
- Enabled loading screen detection
- Game-specific timing parameters

## Benefits

This approach provides several advantages:

1. **Modularity**: Game-specific logic is in config files, not code
2. **Extensibility**: Add new game types without changing agent code
3. **Customization**: Users can adjust prompts to suit their needs
4. **Clarity**: Clear separation between game-specific and general logic