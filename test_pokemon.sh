#!/bin/bash

# Script to test Pokemon gameplay with improved AI logic

# Set the Pokemon ROM path
POKEMON_ROM="/Users/ericflo/Development/emuvlm/roms/gb/Pokemon - Blue Version (UE) [S][T+Por1.2_CBT].gb"

# Set the number of turns to play
MAX_TURNS=50

# Set the config file path
CONFIG_FILE="emuvlm/config.yaml"

# Run the game with improved settings
python emuvlm/play.py --game "$POKEMON_ROM" --config "$CONFIG_FILE" --max-turns "$MAX_TURNS"

# Note: This script assumes that the improvements to agent.py (for loading screen detection and
# Pokemon-specific prompting) have already been made.