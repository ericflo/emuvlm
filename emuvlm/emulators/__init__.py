"""
Emulator interfaces for EmuVLM.

This package provides abstractions for different emulators that can be
used to play games with the LLM agent.
"""

# Import commonly used classes for easier access
from emuvlm.emulators.base import EmulatorBase
from emuvlm.emulators.pyboy_emulator import PyBoyEmulator
from emuvlm.emulators.mgba_emulator import MGBAEmulator