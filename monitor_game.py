#!/usr/bin/env python3
"""
Simple monitoring tool for visualizing the model's decisions in real-time.
Displays the current game frame and the model's decision history.
"""
import argparse
import logging
import os
import queue
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

import yaml
from emulators.pyboy_emulator import PyBoyEmulator
from emulators.mgba_emulator import MGBAEmulator
from model.agent import LLMAgent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GameMonitor:
    """Monitors and visualizes a game being played by the AI."""
    
    def __init__(self, config_path: str, game_name: str, use_summary: bool = False):
        """
        Initialize the monitor.
        
        Args:
            config_path: Path to configuration file
            game_name: Game key from config or path to ROM
            use_summary: Whether to use game state summarization
        """
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Determine game configuration
        if game_name in self.config['games']:
            self.game_config = self.config['games'][game_name]
        else:
            # Assume game_name is a direct path to ROM
            rom_path = game_name
            ext = Path(rom_path).suffix.lower()
            if ext in ['.gb', '.gbc']:
                emulator_type = "pyboy"
            elif ext in ['.gba']:
                emulator_type = "mgba"
            else:
                raise ValueError(f"Unsupported ROM type: {ext}")
            
            # Create minimal game config
            self.game_config = {
                'rom': rom_path,
                'emulator': emulator_type,
                'actions': ['Up', 'Down', 'Left', 'Right', 'A', 'B', 'Start', 'Select'],
                'action_delay': 1.0
            }
        
        self.game_name = game_name
        self.use_summary = use_summary
        self.model_config = self.config.get('model', {})
        
        # Create a session directory for saving data
        self.session_dir = os.path.join(
            'sessions', 
            f"{Path(self.game_config['rom']).stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        os.makedirs(self.session_dir, exist_ok=True)
        
        # Initialize monitoring variables
        self.decision_history = []
        self.running = False
        self.paused = False
        self.current_frame = None
        self.current_action = None
        self.turn_count = 0
        self.event_queue = queue.Queue()
        
        # GUI will be initialized later
        self.root = None
        self.frame_display = None
        self.history_display = None
        
        logger.info(f"Game monitor initialized for {game_name}")
    
    def initialize_game(self):
        """Initialize the emulator and agent."""
        # Initialize emulator based on type
        if self.game_config['emulator'].lower() == 'pyboy':
            self.emulator = PyBoyEmulator(self.game_config['rom'])
        elif self.game_config['emulator'].lower() == 'mgba':
            self.emulator = MGBAEmulator(self.game_config['rom'])
        else:
            raise ValueError(f"Unsupported emulator: {self.game_config['emulator']}")
        
        # Initialize LLM agent
        self.agent = LLMAgent(
            model_config=self.model_config,
            valid_actions=self.game_config['actions'],
            use_summary=self.use_summary
        )
        
        # Capture initial frame
        self.current_frame = self.emulator.get_frame()
        
        logger.info(f"Game initialized: {self.game_name}")
    
    def initialize_gui(self):
        """Initialize the GUI for monitoring."""
        self.root = tk.Tk()
        self.root.title(f"EMU-VLM Monitor - {self.game_name}")
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Game frame display
        frame_frame = ttk.LabelFrame(main_frame, text="Game Screen")
        frame_frame.grid(row=0, column=0, padx=10, pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.frame_display = ttk.Label(frame_frame)
        self.frame_display.grid(row=0, column=0, padx=5, pady=5)
        
        # Update display with initial frame
        self._update_frame_display()
        
        # Decision history display
        history_frame = ttk.LabelFrame(main_frame, text="Decision History")
        history_frame.grid(row=0, column=1, padx=10, pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.history_display = tk.Text(history_frame, width=40, height=20, wrap=tk.WORD)
        self.history_display.grid(row=0, column=0, padx=5, pady=5)
        
        history_scrollbar = ttk.Scrollbar(history_frame, orient="vertical", command=self.history_display.yview)
        history_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.history_display.configure(yscrollcommand=history_scrollbar.set)
        
        # Controls frame
        controls_frame = ttk.Frame(main_frame)
        controls_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky=(tk.W, tk.E))
        
        # Buttons
        self.start_button = ttk.Button(controls_frame, text="Start", command=self.start_game)
        self.start_button.grid(row=0, column=0, padx=5, pady=5)
        
        self.pause_button = ttk.Button(controls_frame, text="Pause", command=self.toggle_pause)
        self.pause_button.grid(row=0, column=1, padx=5, pady=5)
        
        self.stop_button = ttk.Button(controls_frame, text="Stop", command=self.stop_game)
        self.stop_button.grid(row=0, column=2, padx=5, pady=5)
        
        self.save_button = ttk.Button(controls_frame, text="Save Screenshot", command=self.save_screenshot)
        self.save_button.grid(row=0, column=3, padx=5, pady=5)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        # Configure resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        # Set up periodic GUI updates
        self._schedule_gui_update()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.stop_game)
    
    def _schedule_gui_update(self, delay=100):
        """Schedule a GUI update after delay milliseconds."""
        if self.root and self.root.winfo_exists():
            self._process_event_queue()
            self.root.after(delay, self._schedule_gui_update)
    
    def _process_event_queue(self):
        """Process events from the game thread."""
        try:
            while True:
                event = self.event_queue.get_nowait()
                event_type = event.get('type')
                
                if event_type == 'frame_update':
                    self.current_frame = event.get('frame')
                    self._update_frame_display()
                
                elif event_type == 'action':
                    action = event.get('action')
                    self.current_action = action
                    self.decision_history.append(f"Turn {self.turn_count}: {action}")
                    self._update_history_display()
                
                elif event_type == 'status':
                    self.status_var.set(event.get('message'))
                
                self.event_queue.task_done()
                
        except queue.Empty:
            pass
    
    def _update_frame_display(self):
        """Update the frame display with the current frame."""
        if self.current_frame and self.frame_display:
            # Resize the image for display if needed (optional)
            display_width = 320  # You can adjust this
            width_percent = display_width / self.current_frame.width
            display_height = int(self.current_frame.height * width_percent)
            resized_img = self.current_frame.resize((display_width, display_height))
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(resized_img)
            self.frame_display.configure(image=photo)
            self.frame_display.image = photo  # Keep a reference
    
    def _update_history_display(self):
        """Update the decision history display."""
        if self.history_display:
            self.history_display.delete(1.0, tk.END)
            for item in self.decision_history[-20:]:  # Show last 20 entries
                self.history_display.insert(tk.END, item + "\n")
            self.history_display.see(tk.END)  # Scroll to bottom
    
    def save_screenshot(self):
        """Save the current frame as a screenshot."""
        if self.current_frame:
            filename = os.path.join(
                self.session_dir, 
                f"screenshot_{self.turn_count}_{datetime.now().strftime('%H%M%S')}.png"
            )
            self.current_frame.save(filename)
            self.status_var.set(f"Screenshot saved to {filename}")
            logger.info(f"Screenshot saved to {filename}")
    
    def toggle_pause(self):
        """Pause or resume the game."""
        if self.running:
            self.paused = not self.paused
            status = "Paused" if self.paused else "Running"
            self.status_var.set(status)
            self.pause_button.configure(text="Resume" if self.paused else "Pause")
            logger.info(f"Game {status}")
    
    def start_game(self):
        """Start the game loop in a separate thread."""
        if not self.running:
            self.running = True
            self.paused = False
            self.pause_button.configure(text="Pause")
            self.status_var.set("Running")
            
            # Start game thread
            self.game_thread = threading.Thread(target=self._game_loop)
            self.game_thread.daemon = True
            self.game_thread.start()
            
            logger.info("Game started")
    
    def stop_game(self):
        """Stop the game and clean up."""
        if self.running:
            self.running = False
            self.status_var.set("Stopped")
            
            # Wait for game thread to finish
            if hasattr(self, 'game_thread') and self.game_thread.is_alive():
                self.game_thread.join(timeout=2.0)
            
            # Save decision history
            self._save_history()
            
            logger.info("Game stopped")
        
        # Close the emulator
        if hasattr(self, 'emulator'):
            self.emulator.close()
            logger.info("Emulator closed")
        
        # Close the window
        if self.root:
            self.root.destroy()
    
    def _save_history(self):
        """Save the decision history to a file."""
        history_path = os.path.join(self.session_dir, "decision_history.txt")
        with open(history_path, 'w') as f:
            for item in self.decision_history:
                f.write(item + "\n")
        logger.info(f"Decision history saved to {history_path}")
    
    def _game_loop(self):
        """
        Main game loop that runs in a separate thread.
        Captures frames, gets model decisions, and sends inputs to the emulator.
        """
        try:
            while self.running:
                if self.paused:
                    time.sleep(0.1)
                    continue
                
                # Capture current frame
                frame = self.emulator.get_frame()
                
                # Update GUI with new frame
                self.event_queue.put({
                    'type': 'frame_update',
                    'frame': frame
                })
                
                # Get model's decision
                self.event_queue.put({
                    'type': 'status',
                    'message': f"Turn {self.turn_count}: Thinking..."
                })
                
                action_text = self.agent.decide_action(frame)
                
                # Parse action
                action = self.agent.parse_action(action_text)
                
                # Update GUI with action
                self.event_queue.put({
                    'type': 'action',
                    'action': f"{action} ({action_text})" if action else f"Invalid ({action_text})"
                })
                
                # Execute action
                if action:
                    self.event_queue.put({
                        'type': 'status',
                        'message': f"Turn {self.turn_count}: Executing {action}..."
                    })
                    
                    self.emulator.send_input(action)
                    
                    # Save frame after action (optional)
                    frame_path = os.path.join(
                        self.session_dir, 
                        f"turn_{self.turn_count}_{action}.png"
                    )
                    frame.save(frame_path)
                else:
                    self.event_queue.put({
                        'type': 'status',
                        'message': f"Turn {self.turn_count}: Invalid action '{action_text}'"
                    })
                
                # Wait for action to complete
                delay = self.game_config.get('action_delay', 1.0)
                time.sleep(delay)
                
                self.turn_count += 1
                
                # Update status
                self.event_queue.put({
                    'type': 'status',
                    'message': f"Turn {self.turn_count} completed"
                })
        
        except Exception as e:
            logger.error(f"Error in game loop: {e}", exc_info=True)
            self.event_queue.put({
                'type': 'status',
                'message': f"Error: {e}"
            })
            self.running = False
    
    def run(self):
        """Initialize and run the monitor."""
        self.initialize_game()
        self.initialize_gui()
        self.root.mainloop()

def main():
    parser = argparse.ArgumentParser(description='Monitor AI gameplay')
    parser.add_argument('--game', type=str, required=True, help='Game key from config or path to ROM')
    parser.add_argument('--config', type=str, default='config.yaml', help='Path to configuration file')
    parser.add_argument('--summary', type=str, choices=['on', 'off'], default='off', 
                      help='Enable or disable game state summarization')
    
    args = parser.parse_args()
    
    use_summary = args.summary.lower() == 'on'
    
    monitor = GameMonitor(args.config, args.game, use_summary)
    monitor.run()

if __name__ == "__main__":
    main()