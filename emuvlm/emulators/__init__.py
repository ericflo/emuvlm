"""
Emulator interfaces for EmuVLM.

This package provides abstractions for different emulators that can be
used to play games with the LLM agent.
"""

# Import commonly used classes for easier access
from emuvlm.emulators.base import EmulatorBase
from emuvlm.emulators.pyboy_emulator import PyBoyEmulator
from emuvlm.emulators.mgba_emulator import MGBAEmulator
from emuvlm.emulators.fceux_emulator import FCEUXEmulator
from emuvlm.emulators.snes9x_emulator import SNES9xEmulator
from emuvlm.emulators.genesis_plus_gx_emulator import GenesisPlusGXEmulator
from emuvlm.emulators.mupen64plus_emulator import Mupen64PlusEmulator
from emuvlm.emulators.duckstation_emulator import DuckstationEmulator