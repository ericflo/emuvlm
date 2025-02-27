#!/usr/bin/env python3
"""
Demo script to show EmuVLM capabilities with a simple built-in game.
"""
import argparse
import logging
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont
import threading
import time
import os
import random
import yaml
from io import BytesIO
import base64

from emuvlm.model.agent import LLMAgent

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("emuvlm.demo")

class SimpleGameEmulator:
    """
    A simple game emulator that renders a basic turn-based game.
    This demonstrates the EmuVLM system without requiring external ROMs.
    """
    
    def __init__(self, width=240, height=160):
        """
        Initialize the simple game emulator.
        
        Args:
            width: Screen width in pixels
            height: Screen height in pixels
        """
        self.width = width
        self.height = height
        self.screen = Image.new('RGB', (width, height), (0, 0, 0))
        self.draw = ImageDraw.Draw(self.screen)
        
        # Game state
        self.player_pos = [width // 4, height // 2]
        self.goal_pos = [3 * width // 4, height // 2]
        self.obstacles = []
        self.score = 0
        self.moves = 0
        self.game_over = False
        
        # Try to load a font
        self.font = None
        try:
            # Try system fonts
            system_fonts = [
                "/System/Library/Fonts/Supplemental/Arial.ttf",  # macOS
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
                "C:\\Windows\\Fonts\\arial.ttf"  # Windows
            ]
            for font_path in system_fonts:
                if os.path.exists(font_path):
                    self.font = ImageFont.truetype(font_path, 12)
                    break
        except:
            # Fallback to default font
            self.font = ImageFont.load_default()
        
        # Generate initial game state
        self._generate_obstacles(5)
        self._render_frame()
    
    def get_frame(self):
        """
        Get the current game frame.
        
        Returns:
            PIL Image of the current game state
        """
        self._render_frame()
        return self.screen.copy()
    
    def send_input(self, action):
        """
        Process a game action.
        
        Args:
            action: Action name (e.g., "Up", "Down", "A")
        """
        if self.game_over:
            # If game is over, reset on any input
            self._reset_game()
            return
        
        # Increment move counter
        self.moves += 1
        
        # Process movement
        if action == "Up":
            self.player_pos[1] = max(10, self.player_pos[1] - 10)
        elif action == "Down":
            self.player_pos[1] = min(self.height - 10, self.player_pos[1] + 10)
        elif action == "Left":
            self.player_pos[0] = max(10, self.player_pos[0] - 10)
        elif action == "Right":
            self.player_pos[0] = min(self.width - 10, self.player_pos[0] + 10)
        elif action == "A":
            # A button collects items if close to the goal
            dx = abs(self.player_pos[0] - self.goal_pos[0])
            dy = abs(self.player_pos[1] - self.goal_pos[1])
            distance = (dx**2 + dy**2)**0.5
            if distance < 20:
                self.score += 10
                # Move goal to a new position
                self._move_goal()
                # Add more obstacles periodically
                if self.score % 30 == 0:
                    self._generate_obstacles(1)
        elif action == "B":
            # B button removes obstacles if you have points
            if self.score >= 5 and len(self.obstacles) > 0:
                self.obstacles.pop()  # Remove one obstacle
                self.score -= 5
        elif action == "Start":
            # Reset the game
            self._reset_game()
        
        # Check for collisions with obstacles
        for obs in self.obstacles:
            dx = abs(self.player_pos[0] - obs[0])
            dy = abs(self.player_pos[1] - obs[1])
            distance = (dx**2 + dy**2)**0.5
            if distance < 15:  # Collision radius
                self.game_over = True
                break
    
    def close(self):
        """Clean up resources."""
        pass  # Nothing to clean up for this simple emulator
    
    def _render_frame(self):
        """Render the current game state to the screen."""
        # Clear screen
        self.draw.rectangle((0, 0, self.width, self.height), fill=(0, 0, 40))
        
        # Draw goal
        self.draw.ellipse(
            (self.goal_pos[0] - 8, self.goal_pos[1] - 8, 
             self.goal_pos[0] + 8, self.goal_pos[1] + 8),
            fill=(255, 215, 0)  # Gold
        )
        
        # Draw obstacles
        for obs in self.obstacles:
            self.draw.ellipse(
                (obs[0] - 8, obs[1] - 8, obs[0] + 8, obs[1] + 8),
                fill=(255, 0, 0)  # Red
            )
        
        # Draw player
        self.draw.ellipse(
            (self.player_pos[0] - 8, self.player_pos[1] - 8, 
             self.player_pos[0] + 8, self.player_pos[1] + 8),
            fill=(0, 255, 0)  # Green
        )
        
        # Draw score and moves
        if self.font:
            self.draw.text((10, 10), f"Score: {self.score}", fill=(255, 255, 255), font=self.font)
            self.draw.text((10, 30), f"Moves: {self.moves}", fill=(255, 255, 255), font=self.font)
        
        # Draw game over message
        if self.game_over:
            if self.font:
                self.draw.text((self.width // 2 - 40, self.height // 2 - 10), 
                             "GAME OVER", fill=(255, 0, 0), font=self.font)
            else:
                self.draw.text((self.width // 2 - 40, self.height // 2 - 10), 
                             "GAME OVER", fill=(255, 0, 0))
    
    def _generate_obstacles(self, count):
        """Generate random obstacles."""
        for _ in range(count):
            # Place obstacles away from player and goal
            while True:
                x = random.randint(20, self.width - 20)
                y = random.randint(20, self.height - 20)
                
                # Check distance from player
                dx1 = abs(x - self.player_pos[0])
                dy1 = abs(y - self.player_pos[1])
                dist1 = (dx1**2 + dy1**2)**0.5
                
                # Check distance from goal
                dx2 = abs(x - self.goal_pos[0])
                dy2 = abs(y - self.goal_pos[1])
                dist2 = (dx2**2 + dy2**2)**0.5
                
                # Ensure obstacles aren't too close to player or goal
                if dist1 > 30 and dist2 > 30:
                    self.obstacles.append([x, y])
                    break
    
    def _move_goal(self):
        """Move the goal to a new random position."""
        while True:
            x = random.randint(20, self.width - 20)
            y = random.randint(20, self.height - 20)
            
            # Check distance from player
            dx = abs(x - self.player_pos[0])
            dy = abs(y - self.player_pos[1])
            dist = (dx**2 + dy**2)**0.5
            
            # Ensure goal isn't too close or too far from player
            if 50 < dist < 150:
                self.goal_pos = [x, y]
                break
    
    def _reset_game(self):
        """Reset the game state."""
        self.player_pos = [self.width // 4, self.height // 2]
        self.goal_pos = [3 * self.width // 4, self.height // 2]
        self.obstacles = []
        self.score = 0
        self.moves = 0
        self.game_over = False
        self._generate_obstacles(5)

class DemoGameApp:
    """Demo application for EmuVLM with a simple game."""
    
    def __init__(self, root, use_ai=True, api_url="http://localhost:8000"):
        """
        Initialize the demo app.
        
        Args:
            root: Tkinter root window
            use_ai: Whether to use the LLM agent for automatic play
            api_url: URL of the model API for LLM agent
        """
        self.root = root
        self.use_ai = use_ai
        self.api_url = api_url
        
        # Configure window
        self.root.title("EmuVLM Demo - Simple Game")
        self.root.geometry("600x600")
        self.root.minsize(400, 400)
        
        # Initialize the game emulator
        self.game = SimpleGameEmulator(width=240, height=160)
        
        # Initialize the LLM agent if AI is enabled
        self.agent = None
        if self.use_ai:
            try:
                model_config = {
                    'api_url': self.api_url,
                    'temperature': 0.3,
                    'max_tokens': 100,
                    'enable_cache': True
                }
                
                valid_actions = ['Up', 'Down', 'Left', 'Right', 'A', 'B', 'Start']
                
                logger.info(f"Initializing LLM agent with API at {self.api_url}")
                self.agent = LLMAgent(model_config, valid_actions)
            except Exception as e:
                logger.error(f"Failed to initialize LLM agent: {e}")
                messagebox.showerror("AI Error", f"Failed to initialize LLM agent: {str(e)}")
                self.use_ai = False
        
        # Set up the UI
        self._setup_ui()
        
        # AI control thread
        self.ai_running = False
        self.ai_thread = None
        
        # Start the game
        self._update_display()
        
        # Set up window close handler
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _setup_ui(self):
        """Set up the user interface."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Game frame display area
        self.display_frame = ttk.Frame(main_frame)
        self.display_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.display_label = ttk.Label(self.display_frame)
        self.display_label.pack(expand=True)
        
        # Controls frame
        controls_frame = ttk.Frame(main_frame, padding="5")
        controls_frame.pack(fill=tk.X, pady=10)
        
        # Arrow keys
        arrows_frame = ttk.Frame(controls_frame)
        arrows_frame.pack(side=tk.LEFT, padx=20)
        
        # Up button
        up_btn = ttk.Button(arrows_frame, text="↑", width=3, 
                         command=lambda: self._send_action("Up"))
        up_btn.grid(row=0, column=1, padx=5, pady=5)
        
        # Left, Down, Right buttons
        left_btn = ttk.Button(arrows_frame, text="←", width=3, 
                          command=lambda: self._send_action("Left"))
        left_btn.grid(row=1, column=0, padx=5, pady=5)
        
        down_btn = ttk.Button(arrows_frame, text="↓", width=3, 
                           command=lambda: self._send_action("Down"))
        down_btn.grid(row=1, column=1, padx=5, pady=5)
        
        right_btn = ttk.Button(arrows_frame, text="→", width=3, 
                            command=lambda: self._send_action("Right"))
        right_btn.grid(row=1, column=2, padx=5, pady=5)
        
        # Action buttons frame
        action_frame = ttk.Frame(controls_frame)
        action_frame.pack(side=tk.LEFT, padx=20)
        
        # A and B buttons
        a_btn = ttk.Button(action_frame, text="A", width=3, 
                        command=lambda: self._send_action("A"))
        a_btn.grid(row=0, column=1, padx=5, pady=5)
        
        b_btn = ttk.Button(action_frame, text="B", width=3, 
                        command=lambda: self._send_action("B"))
        b_btn.grid(row=0, column=0, padx=5, pady=5)
        
        # Start button
        start_btn = ttk.Button(action_frame, text="Start", 
                            command=lambda: self._send_action("Start"))
        start_btn.grid(row=1, column=0, columnspan=2, padx=5, pady=5)
        
        # AI controls
        ai_frame = ttk.Frame(main_frame, padding="5")
        ai_frame.pack(fill=tk.X, pady=5)
        
        if self.use_ai:
            self.ai_button_var = tk.StringVar(value="Start AI")
            ai_button = ttk.Button(ai_frame, textvariable=self.ai_button_var, 
                                command=self._toggle_ai)
            ai_button.pack(side=tk.LEFT, padx=5)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # AI explanation text
        if self.use_ai:
            explanation_frame = ttk.Frame(main_frame, padding="5")
            explanation_frame.pack(fill=tk.X, pady=5)
            
            explanation_text = (
                "This demo lets a vision-language model (VLM) play the game.\n"
                "The green circle is the player, yellow is the goal, and red circles are obstacles.\n"
                "Try to collect the yellow circles with A, avoid red obstacles, and use B to remove obstacles."
            )
            
            explanation_label = ttk.Label(explanation_frame, text=explanation_text, wraplength=400)
            explanation_label.pack(pady=5)
    
    def _update_display(self):
        """Update the display with the current game frame."""
        try:
            # Get the current frame
            frame = self.game.get_frame()
            
            # Scale up the frame for display
            scale = 3
            width, height = frame.size
            frame = frame.resize((width * scale, height * scale), Image.LANCZOS)
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(frame)
            
            # Update the label
            self.display_label.configure(image=photo)
            self.display_label.image = photo  # Keep a reference
            
            # Schedule the next update
            self.root.after(50, self._update_display)
            
        except Exception as e:
            logger.error(f"Error updating display: {e}")
            self.status_var.set(f"Display error: {str(e)}")
    
    def _send_action(self, action):
        """
        Send an action to the game.
        
        Args:
            action: Action name (e.g., "Up", "A")
        """
        try:
            # Update status
            self.status_var.set(f"Action: {action}")
            
            # Send action to the game
            self.game.send_input(action)
            
        except Exception as e:
            logger.error(f"Error sending action: {e}")
            self.status_var.set(f"Action error: {str(e)}")
    
    def _toggle_ai(self):
        """Toggle AI control of the game."""
        if self.ai_running:
            # Stop AI
            self.ai_running = False
            self.ai_button_var.set("Start AI")
            self.status_var.set("AI stopped")
        else:
            # Start AI
            self.ai_running = True
            self.ai_button_var.set("Stop AI")
            self.status_var.set("AI running")
            
            # Start AI thread if it's not already running
            if not self.ai_thread or not self.ai_thread.is_alive():
                self.ai_thread = threading.Thread(target=self._ai_loop)
                self.ai_thread.daemon = True
                self.ai_thread.start()
    
    def _ai_loop(self):
        """Main loop for AI-controlled gameplay."""
        while self.ai_running:
            try:
                # Get current frame
                frame = self.game.get_frame()
                
                # Ask the agent for the next action
                action_text = self.agent.decide_action(frame)
                logger.info(f"AI suggests: {action_text}")
                
                # Parse the action
                action = self.agent.parse_action(action_text)
                if action:
                    logger.info(f"AI executing: {action}")
                    
                    # Update the UI from the main thread
                    self.root.after(0, lambda a=action: self._send_action(a))
                    
                    # Wait between actions
                    time.sleep(1)
                else:
                    logger.warning(f"Could not parse AI action: {action_text}")
                    time.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"Error in AI loop: {e}")
                time.sleep(1)
    
    def _on_close(self):
        """Handle window close event."""
        # Stop AI thread
        self.ai_running = False
        
        # Wait briefly for thread to exit
        if self.ai_thread and self.ai_thread.is_alive():
            time.sleep(0.2)
        
        # Close the game
        self.game.close()
        
        # Destroy the window
        self.root.destroy()

def main():
    """Main entry point for the demo."""
    parser = argparse.ArgumentParser(description='EmuVLM Demo with Simple Game')
    parser.add_argument('--no-ai', action='store_true', help='Disable AI (play manually only)')
    parser.add_argument('--api-url', type=str, default='http://localhost:8000', 
                      help='URL of the model API for LLM agent')
    args = parser.parse_args()
    
    # Create and start the GUI
    root = tk.Tk()
    app = DemoGameApp(root, use_ai=not args.no_ai, api_url=args.api_url)
    root.mainloop()

if __name__ == "__main__":
    main()