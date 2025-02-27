"""
Mupen64Plus emulator implementation for Nintendo 64 games.
"""
import logging
import subprocess
import time
import os
import atexit
from PIL import Image
import tempfile
import requests
import socket
from typing import Dict, Any, Optional, Tuple

from emuvlm.emulators.base import EmulatorBase

logger = logging.getLogger(__name__)

class Mupen64PlusEmulator(EmulatorBase):
    """
    Emulator implementation using Mupen64Plus for Nintendo 64 games.
    
    This implementation uses a Python server that communicates with 
    Mupen64Plus via its CLI interface and custom UI input handling.
    """
    
    def __init__(self, rom_path: str, server_port: int = 27035):
        """
        Initialize the Mupen64Plus emulator.
        
        Args:
            rom_path: Path to the Nintendo 64 ROM file
            server_port: Port for the HTTP API server
        """
        logger.info(f"Initializing Mupen64Plus emulator with ROM: {rom_path}")
        
        self.rom_path = rom_path
        self.server_port = server_port
        self.api_url = f"http://localhost:{self.server_port}"
        self.emulator_process = None
        self.server_script_path = self._create_server_script()
        
        # Start Mupen64Plus process with server
        self._start_mupen64plus()
        
        # Register cleanup function to ensure emulator is closed
        atexit.register(self.close)
        
        # Wait for the emulator to initialize
        time.sleep(3)
        
        # Test the API connection
        self._check_api_connection()
        
        # Define input mapping for N64 controls
        self.input_mapping = {
            "A": "a",
            "B": "b",
            "Z": "z",
            "Up": "up",
            "Down": "down",
            "Left": "left",
            "Right": "right",
            "C-Up": "i",    # C buttons mapped to I, K, J, L
            "C-Down": "k",
            "C-Left": "j",
            "C-Right": "l",
            "L": "q",
            "R": "w",
            "Start": "Return"
        }
        
        logger.info("Mupen64Plus emulator initialized successfully")
    
    def _create_server_script(self) -> str:
        """
        Create a temporary Python script file that serves as a controller
        for the Mupen64Plus emulator.
        
        Returns:
            str: Path to the server script file
        """
        server_script = f"""#!/usr/bin/env python3
import os
import sys
import time
import subprocess
import threading
import tempfile
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs
import json

# Configuration
PORT = {self.server_port}
MUPEN64PLUS_PATH = "mupen64plus"
ROM_PATH = "{self.rom_path}"
SCREENSHOT_DIR = "{tempfile.gettempdir()}"

# Global variables
emulator_process = None
last_screenshot_path = None

class Mupen64PlusController:
    @staticmethod
    def start_emulator():
        global emulator_process
        
        # Create configuration directory if it doesn't exist
        config_dir = os.path.expanduser("~/.config/mupen64plus")
        os.makedirs(config_dir, exist_ok=True)
        
        # Start the emulator with UI
        emulator_process = subprocess.Popen([
            MUPEN64PLUS_PATH,
            "--noosd",         # Disable on-screen display
            ROM_PATH
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        print(f"Started Mupen64Plus with PID {{emulator_process.pid}}")
        return emulator_process.pid
    
    @staticmethod
    def stop_emulator():
        global emulator_process
        if emulator_process:
            emulator_process.terminate()
            try:
                emulator_process.wait(timeout=3)
                print("Emulator terminated gracefully")
            except subprocess.TimeoutExpired:
                emulator_process.kill()
                print("Emulator killed forcefully")
    
    @staticmethod
    def take_screenshot():
        global emulator_process, last_screenshot_path
        
        # Generate unique filename for screenshot
        timestamp = int(time.time() * 1000)
        screenshot_filename = f"mupen64plus_screenshot_{{timestamp}}.png"
        screenshot_path = os.path.join(SCREENSHOT_DIR, screenshot_filename)
        
        # Use scrot to capture the Mupen64Plus window
        try:
            # First try to capture the specific window
            subprocess.run([
                "xdotool", "search", "--name", "Mupen64Plus", "windowactivate"
            ])
            
            # Brief pause to ensure window is active
            time.sleep(0.2)
            
            # Use scrot to capture the active window
            subprocess.run([
                "scrot", "-u", screenshot_path
            ], check=True)
            
            # If successful, store and return the path
            if os.path.exists(screenshot_path):
                last_screenshot_path = screenshot_path
                print(f"Screenshot taken: {{last_screenshot_path}}")
                return last_screenshot_path
        except Exception as e:
            print(f"Error taking screenshot: {{e}}")
        
        # Fallback to window-less screenshot
        try:
            subprocess.run([
                "scrot", screenshot_path
            ], check=True)
            
            # If successful, store and return the path
            if os.path.exists(screenshot_path):
                last_screenshot_path = screenshot_path
                print(f"Screenshot taken (fallback): {{last_screenshot_path}}")
                return last_screenshot_path
        except Exception as e:
            print(f"Error taking fallback screenshot: {{e}}")
        
        print("Failed to take screenshot")
        return None
    
    @staticmethod
    def send_input(key):
        # Map key to key to send
        key_mappings = {{
            "a": "x",      # A button
            "b": "c",      # B button
            "z": "z",      # Z button
            "start": "Return",
            "up": "Up",
            "down": "Down",
            "left": "Left",
            "right": "Right",
            "c-up": "i",   # C-Up
            "c-down": "k", # C-Down
            "c-left": "j", # C-Left
            "c-right": "l", # C-Right
            "l": "q",      # L button
            "r": "w"       # R button
        }}
        
        if key.lower() in key_mappings:
            xdotool_key = key_mappings[key.lower()]
            try:
                # Activate the Mupen64Plus window
                subprocess.run([
                    "xdotool", "search", "--name", "Mupen64Plus", "windowactivate", "--sync"
                ])
                
                # Small delay to ensure window is active
                time.sleep(0.05)
                
                # Send the keypress
                subprocess.run([
                    "xdotool", "key", "--delay", "50", xdotool_key
                ])
                
                print(f"Sent key: {{key}} ({{xdotool_key}})")
                return True
            except Exception as e:
                print(f"Error sending key {{key}}: {{e}}")
                return False
        else:
            print(f"Unknown key: {{key}}")
            return False

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/status"):
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            status = {{"running": emulator_process is not None and emulator_process.poll() is None}}
            self.wfile.write(json.dumps(status).encode())
            
        elif self.path.startswith("/screenshot"):
            screenshot_path = Mupen64PlusController.take_screenshot()
            if screenshot_path and os.path.exists(screenshot_path):
                self.send_response(200)
                self.send_header("Content-type", "image/png")
                self.end_headers()
                with open(screenshot_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(500)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Failed to take screenshot")
                
        else:
            self.send_response(404)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not found")
    
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode("utf-8")
        params = {{}}
        
        if content_length > 0:
            # Parse form data or JSON
            if self.headers.get("Content-Type") == "application/json":
                params = json.loads(post_data)
            else:
                # Simple form parsing
                for item in post_data.split("&"):
                    if "=" in item:
                        key, value = item.split("=", 1)
                        params[key] = value
        
        if self.path.startswith("/input"):
            key = params.get("key", "")
            success = Mupen64PlusController.send_input(key)
            
            self.send_response(200 if success else 400)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            result = {{"success": success}}
            self.wfile.write(json.dumps(result).encode())
            
        elif self.path.startswith("/exit"):
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({{"exiting": True}}).encode())
            
            # Schedule shutdown after response
            def shutdown_server():
                print("Shutting down server...")
                Mupen64PlusController.stop_emulator()
                server.shutdown()
            
            threading.Timer(0.5, shutdown_server).start()
            
        else:
            self.send_response(404)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not found")

# Start emulator
Mupen64PlusController.start_emulator()

# Start HTTP server
server = HTTPServer(("localhost", PORT), RequestHandler)
print(f"Server running on port {{PORT}}")

try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    print("Cleaning up...")
    Mupen64PlusController.stop_emulator()
    server.server_close()
"""
        
        # Create a temporary file for the server script
        fd, path = tempfile.mkstemp(suffix='.py')
        with os.fdopen(fd, 'w') as f:
            f.write(server_script)
        
        # Make the script executable
        os.chmod(path, 0o755)
        
        logger.debug(f"Created server script at {path}")
        return path
    
    def _start_mupen64plus(self) -> None:
        """
        Start the Mupen64Plus process and controller server.
        """
        try:
            # Start the server script
            self.emulator_process = subprocess.Popen(
                [self.server_script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            logger.info(f"Started Mupen64Plus controller with PID {self.emulator_process.pid}")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.error(f"Failed to start Mupen64Plus controller: {e}")
            raise RuntimeError(f"Failed to start Mupen64Plus controller: {e}")
    
    def _check_api_connection(self) -> bool:
        """
        Check if the Mupen64Plus API is responding.
        
        Returns:
            bool: True if connection is successful
        """
        try:
            response = requests.get(f"{self.api_url}/status", timeout=5)
            if response.status_code == 200:
                logger.info("Successfully connected to Mupen64Plus API")
                return True
            else:
                logger.warning(f"Mupen64Plus API returned status code {response.status_code}")
                return False
        except requests.RequestException as e:
            logger.error(f"Failed to connect to Mupen64Plus API: {e}")
            return False
    
    def get_frame(self) -> Image.Image:
        """
        Get the current frame from the emulator.
        
        Returns:
            PIL Image of the current screen
        """
        try:
            # Request a screenshot from the API
            response = requests.get(f"{self.api_url}/screenshot", timeout=5)
            
            if response.status_code == 200:
                # Load the image from response content
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                    temp_file.write(response.content)
                    temp_path = temp_file.name
                
                # Open the image and remove the temp file
                img = Image.open(temp_path)
                os.unlink(temp_path)
                
                return img
            else:
                logger.error(f"Failed to get screenshot: {response.status_code}")
                # Return a black screen as fallback
                return Image.new('RGB', (640, 480), (0, 0, 0))
                
        except requests.RequestException as e:
            logger.error(f"Error getting frame from Mupen64Plus: {e}")
            # Return a black screen as fallback
            return Image.new('RGB', (640, 480), (0, 0, 0))
    
    def send_input(self, action: str) -> None:
        """
        Send an input action to the emulator.
        
        Args:
            action: Action name (e.g., "A", "Up", "Start")
        """
        if action in self.input_mapping:
            mupen64plus_key = self.input_mapping[action]
            
            try:
                # Send the input command
                response = requests.post(
                    f"{self.api_url}/input",
                    data={"key": mupen64plus_key},
                    timeout=1
                )
                
                if response.status_code == 200:
                    logger.debug(f"Sent input action: {action}")
                else:
                    logger.warning(f"Failed to send input to Mupen64Plus: {response.status_code}")
            except requests.RequestException as e:
                logger.error(f"Failed to send input to Mupen64Plus: {e}")
        else:
            logger.warning(f"Unsupported action for Mupen64Plus: {action}")
    
    def close(self) -> None:
        """
        Close the emulator and clean up resources.
        """
        if hasattr(self, 'emulator_process') and self.emulator_process:
            logger.info("Stopping Mupen64Plus emulator")
            
            try:
                # First try to exit gracefully through the API
                requests.post(f"{self.api_url}/exit", timeout=1)
                time.sleep(0.5)  # Give it a moment to close
            except:
                pass  # API might already be down, continue to forced termination
            
            # If process is still running, terminate it
            if self.emulator_process.poll() is None:
                self.emulator_process.terminate()
                try:
                    self.emulator_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    # If termination times out, kill the process
                    self.emulator_process.kill()
            
            logger.info("Mupen64Plus emulator stopped")
            
            # Clean up the temporary server script
            if hasattr(self, 'server_script_path') and os.path.exists(self.server_script_path):
                os.unlink(self.server_script_path)
                logger.debug(f"Removed server script: {self.server_script_path}")
            
            # Unregister the atexit handler
            try:
                atexit.unregister(self.close)
            except:
                pass  # Ignore if already unregistered