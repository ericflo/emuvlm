"""
Genesis Plus GX emulator implementation for Sega Genesis/Mega Drive games.
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

class GenesisPlusGXEmulator(EmulatorBase):
    """
    Emulator implementation using Genesis Plus GX for Sega Genesis/Mega Drive games.
    
    This implementation uses a Python wrapper script to control the emulator
    through pipe communication and screenshots.
    """
    
    def __init__(self, rom_path: str, server_port: int = 27030):
        """
        Initialize the Genesis Plus GX emulator.
        
        Args:
            rom_path: Path to the Sega Genesis/Mega Drive ROM file
            server_port: Port for the HTTP API server
        """
        logger.info(f"Initializing Genesis Plus GX emulator with ROM: {rom_path}")
        
        self.rom_path = rom_path
        self.server_port = server_port
        self.api_url = f"http://localhost:{self.server_port}"
        self.emulator_process = None
        self.wrapper_script_path = self._create_wrapper_script()
        
        # Start Genesis Plus GX process with wrapper
        self._start_genesis_plus_gx()
        
        # Register cleanup function to ensure emulator is closed
        atexit.register(self.close)
        
        # Wait for the emulator to initialize
        time.sleep(2)
        
        # Test the API connection
        self._check_api_connection()
        
        # Define input mapping for Genesis controls
        self.input_mapping = {
            "A": "a",     # Genesis button A (typically C on real hardware)
            "B": "b",     # Genesis button B (typically B on real hardware)
            "C": "c",     # Genesis button C (typically A on real hardware)
            "Up": "up",
            "Down": "down",
            "Left": "left",
            "Right": "right",
            "Start": "start"
        }
        
        logger.info("Genesis Plus GX emulator initialized successfully")
    
    def _create_wrapper_script(self) -> str:
        """
        Create a temporary Python script file that wraps the Genesis Plus GX emulator
        and provides an HTTP API for controlling it.
        
        Returns:
            str: Path to the wrapper script file
        """
        wrapper_script = f"""#!/usr/bin/env python3
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
GENESIS_PLUS_GX_PATH = "retroarch"  # Using RetroArch with Genesis Plus GX core
ROM_PATH = "{self.rom_path}"
SCREENSHOT_DIR = "{tempfile.gettempdir()}"

# Global variables
emulator_process = None
last_screenshot_path = None

class GenesisController:
    @staticmethod
    def start_emulator():
        global emulator_process
        emulator_process = subprocess.Popen([
            GENESIS_PLUS_GX_PATH,
            "-L", "/usr/lib/libretro/genesis_plus_gx_libretro.so",  # Path to Genesis Plus GX core
            ROM_PATH
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Started Genesis Plus GX with PID {{emulator_process.pid}}")
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
        screenshot_filename = f"genesis_screenshot_{{timestamp}}.png"
        screenshot_path = os.path.join(SCREENSHOT_DIR, screenshot_filename)
        
        # Use RetroArch's screenshot command (F8 is default)
        subprocess.run(["xdotool", "search", "--name", "RetroArch", "windowactivate", "--sync", "key", "F8"])
        
        # Wait a moment for the screenshot to be saved
        time.sleep(0.1)
        
        # RetroArch saves screenshots to its own directory, copy to our temp dir
        retroarch_screenshots = os.path.expanduser("~/.config/retroarch/screenshots")
        latest_screenshot = None
        
        if os.path.exists(retroarch_screenshots):
            all_screenshots = []
            for file in os.listdir(retroarch_screenshots):
                if file.endswith(".png"):
                    filepath = os.path.join(retroarch_screenshots, file)
                    all_screenshots.append((os.path.getmtime(filepath), filepath))
            
            if all_screenshots:
                all_screenshots.sort(reverse=True)
                latest_screenshot = all_screenshots[0][1]
                
                # Copy to our temp directory
                subprocess.run(["cp", latest_screenshot, screenshot_path])
                last_screenshot_path = screenshot_path
                print(f"Screenshot taken: {{last_screenshot_path}}")
                return last_screenshot_path
        
        # Fallback if RetroArch screenshot failed
        if not latest_screenshot:
            # Try using external screenshot tool
            try:
                subprocess.run(["scrot", "-u", screenshot_path], check=True)
                last_screenshot_path = screenshot_path
                print(f"Screenshot taken with scrot: {{last_screenshot_path}}")
                return last_screenshot_path
            except:
                print("Failed to take screenshot")
                return None
    
    @staticmethod
    def send_input(key):
        # Map key to RetroArch key
        key_mappings = {{
            "a": "x",      # Maps to RetroArch X (Genesis A/C)
            "b": "z",      # Maps to RetroArch Z (Genesis B)
            "c": "c",      # Maps to RetroArch C (Genesis C/A)
            "start": "Return",
            "up": "Up",
            "down": "Down",
            "left": "Left",
            "right": "Right"
        }}
        
        if key in key_mappings:
            xdotool_key = key_mappings[key]
            # Send keypress to RetroArch window
            subprocess.run(["xdotool", "search", "--name", "RetroArch", "windowactivate", "--sync", "key", "--delay", "100", xdotool_key])
            time.sleep(0.1)  # Short delay to let the input register
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
            status = {{"running": emulator_process is not None and emulator_process.poll() is None}}
            self.wfile.write(json.dumps(status).encode())
            
        elif self.path.startswith("/screenshot"):
            screenshot_path = GenesisController.take_screenshot()
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
            success = GenesisController.send_input(key)
            
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
                GenesisController.stop_emulator()
                server.shutdown()
            
            threading.Timer(0.5, shutdown_server).start()
            
        else:
            self.send_response(404)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not found")

# Start emulator
GenesisController.start_emulator()

# Start HTTP server
server = HTTPServer(("localhost", PORT), RequestHandler)
print(f"Server running on port {{PORT}}")

try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    print("Cleaning up...")
    GenesisController.stop_emulator()
    server.server_close()
"""
        
        # Create a temporary file for the wrapper script
        fd, path = tempfile.mkstemp(suffix='.py')
        with os.fdopen(fd, 'w') as f:
            f.write(wrapper_script)
        
        # Make the script executable
        os.chmod(path, 0o755)
        
        logger.debug(f"Created wrapper script at {path}")
        return path
    
    def _start_genesis_plus_gx(self) -> None:
        """
        Start the Genesis Plus GX emulator process with wrapper script.
        """
        try:
            # Start the wrapper script which launches the emulator
            self.emulator_process = subprocess.Popen(
                [self.wrapper_script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            logger.info(f"Started Genesis Plus GX controller with PID {self.emulator_process.pid}")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.error(f"Failed to start Genesis Plus GX controller: {e}")
            raise RuntimeError(f"Failed to start Genesis Plus GX controller: {e}")
    
    def _check_api_connection(self) -> bool:
        """
        Check if the Genesis Plus GX API is responding.
        
        Returns:
            bool: True if connection is successful
        """
        try:
            response = requests.get(f"{self.api_url}/status", timeout=5)
            if response.status_code == 200:
                logger.info("Successfully connected to Genesis Plus GX API")
                return True
            else:
                logger.warning(f"Genesis Plus GX API returned status code {response.status_code}")
                return False
        except requests.RequestException as e:
            logger.error(f"Failed to connect to Genesis Plus GX API: {e}")
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
                return Image.new('RGB', (320, 224), (0, 0, 0))
                
        except requests.RequestException as e:
            logger.error(f"Error getting frame from Genesis Plus GX: {e}")
            # Return a black screen as fallback
            return Image.new('RGB', (320, 224), (0, 0, 0))
    
    def send_input(self, action: str) -> None:
        """
        Send an input action to the emulator.
        
        Args:
            action: Action name (e.g., "A", "Up", "Start")
        """
        if action in self.input_mapping:
            genesis_key = self.input_mapping[action]
            
            try:
                # Send the input command
                response = requests.post(
                    f"{self.api_url}/input",
                    data={"key": genesis_key},
                    timeout=1
                )
                
                if response.status_code == 200:
                    logger.debug(f"Sent input action: {action}")
                else:
                    logger.warning(f"Failed to send input to Genesis Plus GX: {response.status_code}")
            except requests.RequestException as e:
                logger.error(f"Failed to send input to Genesis Plus GX: {e}")
        else:
            logger.warning(f"Unsupported action for Genesis Plus GX: {action}")
    
    def close(self) -> None:
        """
        Close the emulator and clean up resources.
        """
        if hasattr(self, 'emulator_process') and self.emulator_process:
            logger.info("Stopping Genesis Plus GX emulator")
            
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
            
            logger.info("Genesis Plus GX emulator stopped")
            
            # Clean up the temporary wrapper script
            if hasattr(self, 'wrapper_script_path') and os.path.exists(self.wrapper_script_path):
                os.unlink(self.wrapper_script_path)
                logger.debug(f"Removed wrapper script: {self.wrapper_script_path}")
            
            # Unregister the atexit handler
            try:
                atexit.unregister(self.close)
            except:
                pass  # Ignore if already unregistered