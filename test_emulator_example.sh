#!/bin/bash
# Example script to test various emulators with EmuVLM

# Set these values to point to your ROMs
GB_ROM="path/to/your/gameboy_rom.gb"
GBC_ROM="path/to/your/gbc_rom.gbc" 
GBA_ROM="path/to/your/gba_rom.gba"
NES_ROM="path/to/your/nes_rom.nes"
SNES_ROM="path/to/your/snes_rom.sfc"
GENESIS_ROM="path/to/your/genesis_rom.md"
N64_ROM="path/to/your/n64_rom.z64"
PS1_ROM="path/to/your/playstation_iso.bin"

# Test a single emulator
echo "Testing PyBoy (Game Boy) emulator..."
python -m emuvlm.test_emulators --emulator pyboy --rom "$GB_ROM" --iterations 3

echo "Testing mGBA (Game Boy Advance) emulator..."
python -m emuvlm.test_emulators --emulator mgba --rom "$GBA_ROM" --iterations 3

echo "Testing FCEUX (NES) emulator..."
python -m emuvlm.test_emulators --emulator fceux --rom "$NES_ROM" --iterations 3

echo "Testing Snes9x (SNES) emulator..."
python -m emuvlm.test_emulators --emulator snes9x --rom "$SNES_ROM" --iterations 3

echo "Testing Genesis Plus GX emulator..."
python -m emuvlm.test_emulators --emulator genesis --rom "$GENESIS_ROM" --iterations 3

echo "Testing Mupen64Plus (N64) emulator..."
python -m emuvlm.test_emulators --emulator mupen64plus --rom "$N64_ROM" --iterations 3

echo "Testing Duckstation (PlayStation) emulator..."
python -m emuvlm.test_emulators --emulator duckstation --rom "$PS1_ROM" --iterations 3

# Alternatively, test all emulators at once
# python -m emuvlm.test_emulators --all \
#   --pyboy-rom "$GB_ROM" \
#   --mgba-rom "$GBA_ROM" \
#   --fceux-rom "$NES_ROM" \
#   --snes9x-rom "$SNES_ROM" \
#   --genesis-rom "$GENESIS_ROM" \
#   --mupen64plus-rom "$N64_ROM" \
#   --duckstation-rom "$PS1_ROM" \
#   --iterations 3

echo "Tests completed. Check the test_output directory for results."