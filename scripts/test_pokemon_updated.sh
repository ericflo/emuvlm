#!/bin/bash

# Script to test Pokemon gameplay with our improved configuration approach
# This version uses the game configuration from config.yaml

# Set the number of turns to play
MAX_TURNS=50

# Set the config file path 
CONFIG_FILE="emuvlm/config.yaml"

# Set the game name from config.yaml
GAME_NAME="pokemon_blue"

# Run the game with improved settings
python emuvlm/play.py --game "$GAME_NAME" --config "$CONFIG_FILE" --max-turns "$MAX_TURNS"

# Note: This script assumes that the improvements to agent.py have been made
# to use the game_type and prompt_additions from the config.yaml file.