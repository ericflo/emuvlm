# ROM Directory

Place your ROM files in the appropriate subdirectories:

- `gb/`: Game Boy ROMs (`.gb`)
- `gbc/`: Game Boy Color ROMs (`.gbc`)
- `gba/`: Game Boy Advance ROMs (`.gba`)
- `gamegear/`: Sega Game Gear ROMs (`.gg`)
- `nes/`: Nintendo Entertainment System ROMs (`.nes`)
- `snes/`: Super Nintendo Entertainment System ROMs (`.snes`, `.smc`)
- `genesis/`: Sega Genesis/Mega Drive ROMs (`.md`, `.bin`, `.smd`)
- `n64/`: Nintendo 64 ROMs (`.n64`, `.z64`, `.v64`)
- `ps1/`: PlayStation 1 ROMs (`.bin`, `.cue`, `.iso`, `.ccd`, `.img`, `.sub`)

## Notes:

1. ROMs are **not** included with this project and must be provided by the user.
2. All ROM files are gitignored to prevent copyright issues.
3. Please ensure you have the legal right to use any ROMs you place in these directories.
4. For PS1 games, use the `.cue` file as the ROM path in configuration files.
5. Configure your ROMs in the YAML files inside the `examples/` directory or create your own configuration files.

## Example Configuration:

```yaml
rom_path: roms/snes/chrono_trigger.smc
emulator: snes9x
game_name: Chrono Trigger
```