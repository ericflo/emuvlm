#!/usr/bin/env python3
"""
Monitor script that displays game frames and provides user with the option
to intervene in gameplay.
"""
import argparse
import logging
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import threading
import time
import os
import yaml
from pathlib import Path

from emuvlm.emulators.pyboy_emulator import PyBoyEmulator
from emuvlm.emulators.mgba_emulator import MGBAEmulator

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("emuvlm.monitor")

class GameMonitor:
    """GUI application to monitor and interact with the game."""
    
    def __init__(self, root, emulator, config):
        """
        Initialize the monitor GUI.
        
        Args:
            root: Tkinter root window
            emulator: Initialized emulator instance
            config: Game configuration
        """
        self.root = root
        self.emulator = emulator
        self.config = config
        
        # Configure window
        self.root.title(f"EmuVLM Monitor - {os.path.basename(config.get('rom', 'Unknown Game'))}")
        self.root.geometry("600x600")
        self.root.minsize(400, 400)
        
        # Set up the UI
        self._setup_ui()
        
        # Flag to control the monitoring thread
        self.running = True
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        # Set up window close handler
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _setup_ui(self):
        """Set up the user interface."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Game frame display area
        self.display_label = ttk.Label(main_frame)
        self.display_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Controls frame
        controls_frame = ttk.Frame(main_frame, padding="5")
        controls_frame.pack(fill=tk.X, pady=10)
        
        # Action buttons
        self.valid_actions = self.config.get('actions', ['Up', 'Down', 'Left', 'Right', 'A', 'B', 'Start', 'Select'])
        for action in self.valid_actions:
            btn = ttk.Button(controls_frame, text=action, command=lambda a=action: self._send_action(a))
            btn.pack(side=tk.LEFT, padx=5)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def _monitor_loop(self):
        """Main loop to update the display with the current game frame."""
        while self.running:
            try:
                # Get the current frame
                frame = self.emulator.get_frame()
                
                # Update the display
                self._update_display(frame)
                
                # Small delay to avoid hammering the CPU
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                if self.running:  # Only show error if still running
                    self.status_var.set(f"Error: {str(e)}")
                    time.sleep(1)
    
    def _update_display(self, frame):
        """
        Update the display with a new frame.
        
        Args:
            frame: PIL Image of the current game frame
        """
        try:
            # Resize the image for display if needed
            display_width = self.display_label.winfo_width()
            if display_width < 50:  # Window might not be fully initialized
                display_width = 400
            
            # Calculate new height maintaining aspect ratio
            aspect_ratio = frame.height / frame.width
            display_height = int(display_width * aspect_ratio)
            
            # Resize the image
            resized_frame = frame.resize((display_width, display_height), Image.LANCZOS)
            
            # Convert to PhotoImage for Tkinter
            photo = ImageTk.PhotoImage(resized_frame)
            
            # Update the label
            self.display_label.configure(image=photo)
            self.display_label.image = photo  # Keep a reference to avoid garbage collection
            
            # Update status
            self.status_var.set("Game running")
            
        except Exception as e:
            logger.error(f"Error updating display: {e}")
            self.status_var.set(f"Display error: {str(e)}")
    
    def _send_action(self, action):
        """
        Send an action to the emulator.
        
        Args:
            action: The action to send (e.g., "A", "Up")
        """
        try:
            logger.info(f"Sending action: {action}")
            self.status_var.set(f"Sending action: {action}")
            
            # Send the action to the emulator
            self.emulator.send_input(action)
            
            # Update status
            self.status_var.set(f"Sent action: {action}")
            
        except Exception as e:
            logger.error(f"Error sending action: {e}")
            self.status_var.set(f"Action error: {str(e)}")
    
    def _on_close(self):
        """Handle window close event."""
        self.running = False
        time.sleep(0.2)  # Give monitor thread time to exit
        
        # Close the emulator
        try:
            self.emulator.close()
        except:
            pass
        
        # Destroy the window
        self.root.destroy()

def load_config(config_path):
    """Load configuration from YAML file."""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {}

def main():
    """Main entry point for the monitor."""
    parser = argparse.ArgumentParser(description='Monitor and interact with EmuVLM games')
    parser.add_argument('--game', type=str, required=True, help='Game key from config or path to ROM')
    parser.add_argument('--config', type=str, default='config.yaml', help='Path to configuration file')
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Determine which game to play
    if args.game in config.get('games', {}):
        game_config = config['games'][args.game]
        game_name = args.game
    else:
        # Assume args.game is a direct path to ROM
        rom_path = args.game
        ext = Path(rom_path).suffix.lower()
        if ext in ['.gb', '.gbc']:
            emulator_type = "pyboy"
        elif ext in ['.gba']:
            emulator_type = "mgba"
        else:
            raise ValueError(f"Unsupported ROM type: {ext}")
        
        # Create minimal game config
        game_config = {
            'rom': rom_path,
            'emulator': emulator_type,
            'actions': ['Up', 'Down', 'Left', 'Right', 'A', 'B', 'Start', 'Select'],
        }
        game_name = os.path.basename(rom_path)
    
    # Initialize emulator
    try:
        if game_config['emulator'].lower() == 'pyboy':
            emulator = PyBoyEmulator(game_config['rom'])
        elif game_config['emulator'].lower() == 'mgba':
            emulator = MGBAEmulator(game_config['rom'])
        else:
            raise ValueError(f"Unsupported emulator: {game_config['emulator']}")
    
        # Create and start the GUI
        root = tk.Tk()
        app = GameMonitor(root, emulator, game_config)
        root.mainloop()
        
    except Exception as e:
        logger.error(f"Error starting monitor: {e}")
        messagebox.showerror("Error", f"Failed to start monitor: {str(e)}")

if __name__ == "__main__":
    main()