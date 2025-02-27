"""
SNES9x emulator implementation for SNES games.
"""
import logging
import subprocess
import time
import os
import atexit
from PIL import Image
import tempfile
import requests
from typing import Dict, Any, Optional, Tuple

from emuvlm.emulators.base import EmulatorBase

logger = logging.getLogger(__name__)

class SNES9xEmulator(EmulatorBase):
    """
    Emulator implementation using SNES9x for SNES games.
    
    This implementation uses the SNES9x CLI interface with
    a lightweight HTTP server for controlling the emulator.
    """
    
    def __init__(self, rom_path: str, server_port: int = 27025):
        """
        Initialize the SNES9x emulator.
        
        Args:
            rom_path: Path to the SNES ROM file
            server_port: Port for the HTTP server for communication
        """
        logger.info(f"Initializing SNES9x emulator with ROM: {rom_path}")
        
        self.rom_path = rom_path
        self.server_port = server_port
        self.api_url = f"http://localhost:{self.server_port}"
        self.snes9x_process = None
        self.server_script_path = self._create_server_script()
        
        # Start SNES9x process with server script
        self._start_snes9x()
        
        # Register cleanup function to ensure emulator is closed
        atexit.register(self.close)
        
        # Wait for the emulator to initialize
        time.sleep(2)
        
        # Test the API connection
        self._check_api_connection()
        
        # Define input mapping for SNES controls
        self.input_mapping = {
            "A": "a",
            "B": "b",
            "X": "x",
            "Y": "y",
            "L": "l",
            "R": "r",
            "Up": "up",
            "Down": "down",
            "Left": "left",
            "Right": "right",
            "Start": "start",
            "Select": "select"
        }
        
        logger.info("SNES9x emulator initialized successfully")
    
    def _create_server_script(self) -> str:
        """
        Create a temporary Python script file to act as a server between
        the emulator and our API.
        
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
SNES9X_PATH = "snes9x"
ROM_PATH = "{self.rom_path}"
SCREENSHOT_DIR = "{tempfile.gettempdir()}"

# Global variables
snes9x_process = None
last_screenshot_path = None

class Snes9xController:
    @staticmethod
    def start_emulator():
        global snes9x_process
        snes9x_process = subprocess.Popen([
            SNES9X_PATH,
            "-screenshot-directory", SCREENSHOT_DIR,
            ROM_PATH
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Started SNES9x with PID {{snes9x_process.pid}}")
        return snes9x_process.pid
    
    @staticmethod
    def stop_emulator():
        global snes9x_process
        if snes9x_process:
            snes9x_process.terminate()
            try:
                snes9x_process.wait(timeout=3)
                print("SNES9x terminated gracefully")
            except subprocess.TimeoutExpired:
                snes9x_process.kill()
                print("SNES9x killed forcefully")
    
    @staticmethod
    def take_screenshot():
        global snes9x_process, last_screenshot_path
        
        # Generate unique filename for screenshot
        timestamp = int(time.time() * 1000)
        screenshot_filename = f"snes9x_screenshot_{{timestamp}}.png"
        screenshot_path = os.path.join(SCREENSHOT_DIR, screenshot_filename)
        
        # Send F12 to SNES9x to take screenshot (default hotkey)
        subprocess.run(["xdotool", "search", "--name", "SNES9x", "windowactivate", "--sync", "key", "F12"])
        
        # Wait a moment for the screenshot to be saved
        time.sleep(0.1)
        
        # Find the most recent screenshot file
        all_screenshots = []
        for file in os.listdir(SCREENSHOT_DIR):
            if file.startswith("snes9x") and file.endswith(".png"):
                filepath = os.path.join(SCREENSHOT_DIR, file)
                all_screenshots.append((os.path.getmtime(filepath), filepath))
        
        if all_screenshots:
            # Sort by modification time (newest first)
            all_screenshots.sort(reverse=True)
            last_screenshot_path = all_screenshots[0][1]
            print(f"Screenshot taken: {{last_screenshot_path}}")
            return last_screenshot_path
        else:
            print("No screenshot found")
            return None
    
    @staticmethod
    def send_input(key):
        # Map key to SNES9x key
        key_mappings = {{
            "a": "x",
            "b": "z",
            "x": "s",
            "y": "a",
            "l": "q",
            "r": "w",
            "start": "Return",
            "select": "space",
            "up": "Up",
            "down": "Down",
            "left": "Left",
            "right": "Right"
        }}
        
        if key in key_mappings:
            xdotool_key = key_mappings[key]
            # Send keypress to SNES9x window
            subprocess.run(["xdotool", "search", "--name", "SNES9x", "windowactivate", "--sync", "key", xdotool_key])
            print(f"Sent key: {{key}} ({{xdotool_key}})")
            return True
        else:
            print(f"Unknown key: {{key}}")
            return False

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/status"):
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            status = {{"running": snes9x_process is not None and snes9x_process.poll() is None}}
            self.wfile.write(json.dumps(status).encode())
            
        elif self.path.startswith("/screenshot"):
            screenshot_path = Snes9xController.take_screenshot()
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
            success = Snes9xController.send_input(key)
            
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
                Snes9xController.stop_emulator()
                server.shutdown()
            
            threading.Timer(0.5, shutdown_server).start()
            
        else:
            self.send_response(404)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not found")

# Start emulator
Snes9xController.start_emulator()

# Start HTTP server
server = HTTPServer(("localhost", PORT), RequestHandler)
print(f"Server running on port {{PORT}}")

try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    print("Cleaning up...")
    Snes9xController.stop_emulator()
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
    
    def _start_snes9x(self) -> None:
        """
        Start the SNES9x process and the server script for API communication.
        """
        try:
            # Start the server script
            self.snes9x_process = subprocess.Popen(
                [self.server_script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            logger.info(f"Started SNES9x controller with PID {self.snes9x_process.pid}")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.error(f"Failed to start SNES9x controller: {e}")
            raise RuntimeError(f"Failed to start SNES9x controller: {e}")
    
    def _check_api_connection(self) -> bool:
        """
        Check if the SNES9x API is responding.
        
        Returns:
            bool: True if connection is successful
        """
        try:
            response = requests.get(f"{self.api_url}/status", timeout=5)
            if response.status_code == 200:
                logger.info("Successfully connected to SNES9x API")
                return True
            else:
                logger.warning(f"SNES9x API returned status code {response.status_code}")
                return False
        except requests.RequestException as e:
            logger.error(f"Failed to connect to SNES9x API: {e}")
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
                return Image.new('RGB', (256, 224), (0, 0, 0))
                
        except requests.RequestException as e:
            logger.error(f"Error getting frame from SNES9x: {e}")
            # Return a black screen as fallback
            return Image.new('RGB', (256, 224), (0, 0, 0))
    
    def send_input(self, action: str) -> None:
        """
        Send an input action to the emulator.
        
        Args:
            action: Action name (e.g., "A", "Up", "Start")
        """
        if action in self.input_mapping:
            snes9x_key = self.input_mapping[action]
            
            try:
                # Send the input command
                response = requests.post(
                    f"{self.api_url}/input",
                    data={"key": snes9x_key},
                    timeout=1
                )
                
                if response.status_code == 200:
                    logger.debug(f"Sent input action: {action}")
                else:
                    logger.warning(f"Failed to send input to SNES9x: {response.status_code}")
            except requests.RequestException as e:
                logger.error(f"Failed to send input to SNES9x: {e}")
        else:
            logger.warning(f"Unsupported action for SNES9x: {action}")
    
    def close(self) -> None:
        """
        Close the emulator and clean up resources.
        """
        if hasattr(self, 'snes9x_process') and self.snes9x_process:
            logger.info("Stopping SNES9x emulator")
            
            try:
                # First try to exit gracefully through the API
                requests.post(f"{self.api_url}/exit", timeout=1)
                time.sleep(0.5)  # Give it a moment to close
            except:
                pass  # API might already be down, continue to forced termination
            
            # If process is still running, terminate it
            if self.snes9x_process.poll() is None:
                self.snes9x_process.terminate()
                try:
                    self.snes9x_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    # If termination times out, kill the process
                    self.snes9x_process.kill()
            
            logger.info("SNES9x emulator stopped")
            
            # Clean up the temporary server script
            if hasattr(self, 'server_script_path') and os.path.exists(self.server_script_path):
                os.unlink(self.server_script_path)
                logger.debug(f"Removed server script: {self.server_script_path}")
            
            # Unregister the atexit handler
            try:
                atexit.unregister(self.close)
            except:
                pass  # Ignore if already unregistered