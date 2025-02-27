"""
FCEUX emulator implementation for NES games.
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

class FCEUXEmulator(EmulatorBase):
    """
    Emulator implementation using FCEUX for NES games.
    
    This implementation uses the FCEUX Lua API via a WebSocket server
    for controlling the emulator and getting screenshots.
    """
    
    def __init__(self, rom_path: str, lua_port: int = 27020):
        """
        Initialize the FCEUX emulator.
        
        Args:
            rom_path: Path to the NES ROM file
            lua_port: Port for the FCEUX Lua API WebSocket
        """
        logger.info(f"Initializing FCEUX emulator with ROM: {rom_path}")
        
        self.rom_path = rom_path
        self.lua_port = lua_port
        self.ws_url = f"ws://localhost:{self.lua_port}"
        self.http_url = f"http://localhost:{self.lua_port}"
        self.fceux_process = None
        self.lua_script_path = self._create_lua_script()
        
        # Start FCEUX process with Lua API enabled
        self._start_fceux()
        
        # Register cleanup function to ensure emulator is closed
        atexit.register(self.close)
        
        # Wait for the emulator to initialize
        time.sleep(2)
        
        # Test the API connection
        self._check_api_connection()
        
        # Define input mapping
        self.input_mapping = {
            "A": "A",
            "B": "B",
            "Up": "up",
            "Down": "down",
            "Left": "left",
            "Right": "right",
            "Start": "start",
            "Select": "select"
        }
        
        logger.info("FCEUX emulator initialized successfully")
    
    def _create_lua_script(self) -> str:
        """
        Create a temporary Lua script file for FCEUX with WebSocket server.
        
        Returns:
            str: Path to the Lua script file
        """
        lua_script = """
        -- WebSocket server for FCEUX
        server_port = """ + str(self.lua_port) + """
        
        -- Initialize the server
        socket = require("socket")
        http = require("socket.http")
        server = socket.bind("localhost", server_port)
        server:settimeout(0)
        
        print("WebSocket server started on port " .. server_port)
        
        -- Variables to track state
        clients = {}
        last_screenshot_time = 0
        screenshot_interval = 100 -- ms
        
        -- Main loop
        while true do
            -- Accept new connections
            client = server:accept()
            if client then
                client:settimeout(0)
                table.insert(clients, client)
                print("New client connected")
            end
            
            -- Handle client messages
            for i, client in ipairs(clients) do
                local msg, err = client:receive()
                if msg then
                    -- Process commands
                    if msg:sub(1, 10) == "SCREENSHOT" then
                        -- Take screenshot and send back image data
                        local ss = gui.gdscreenshot()
                        local width = ss:width()
                        local height = ss:height()
                        local data = "SCREENSHOT:" .. width .. ":" .. height .. ":"
                        
                        for y = 0, height - 1 do
                            for x = 0, width - 1 do
                                local pixel = ss:getpixel(x, y)
                                local r, g, b = bit.band(bit.rshift(pixel, 16), 0xFF),
                                                bit.band(bit.rshift(pixel, 8), 0xFF),
                                                bit.band(pixel, 0xFF)
                                data = data .. string.char(r) .. string.char(g) .. string.char(b)
                            end
                        end
                        
                        client:send(data)
                    elseif msg:sub(1, 5) == "INPUT" then
                        -- Process input command
                        local input_type = msg:sub(7)
                        local joypad_table = {}
                        joypad_table[input_type] = true
                        joypad.set(1, joypad_table) -- Set for player 1
                        emu.frameadvance() -- Advance one frame to register input
                        joypad_table[input_type] = false
                        joypad.set(1, joypad_table) -- Release the button
                        client:send("OK")
                    elseif msg == "STATUS" then
                        -- Return emulator status
                        client:send("RUNNING")
                    elseif msg == "EXIT" then
                        -- Gracefully exit
                        client:send("BYE")
                        client:close()
                        table.remove(clients, i)
                    end
                end
            end
            
            -- Advance emulation
            emu.frameadvance()
        end
        """
        
        # Create a temporary file for the Lua script
        fd, path = tempfile.mkstemp(suffix='.lua')
        with os.fdopen(fd, 'w') as f:
            f.write(lua_script)
        
        logger.debug(f"Created Lua script at {path}")
        return path
    
    def _start_fceux(self) -> None:
        """
        Start the FCEUX process with Lua script for API communication.
        """
        cmd = [
            "fceux",
            "--loadlua", self.lua_script_path,
            "--nogui",  # Optional: Run without GUI for headless operation
            self.rom_path
        ]
        
        try:
            # Start FCEUX process
            self.fceux_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            logger.info(f"Started FCEUX process with PID {self.fceux_process.pid}")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.error(f"Failed to start FCEUX: {e}")
            raise RuntimeError(f"Failed to start FCEUX: {e}")
    
    def _check_api_connection(self) -> bool:
        """
        Check if the FCEUX Lua API is responding.
        
        Returns:
            bool: True if connection is successful
        """
        try:
            response = requests.get(f"{self.http_url}/status", timeout=5)
            if response.status_code == 200:
                logger.info("Successfully connected to FCEUX Lua API")
                return True
            else:
                logger.warning(f"FCEUX API returned status code {response.status_code}")
                return False
        except requests.RequestException as e:
            logger.error(f"Failed to connect to FCEUX API: {e}")
            return False
    
    def get_frame(self) -> Image.Image:
        """
        Get the current frame from the emulator.
        
        Returns:
            PIL Image of the current screen
        """
        try:
            # Request a screenshot from the API
            response = requests.get(f"{self.http_url}/screenshot", timeout=5)
            
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
                return Image.new('RGB', (256, 240), (0, 0, 0))
                
        except requests.RequestException as e:
            logger.error(f"Error getting frame from FCEUX: {e}")
            # Return a black screen as fallback
            return Image.new('RGB', (256, 240), (0, 0, 0))
    
    def send_input(self, action: str) -> None:
        """
        Send an input action to the emulator.
        
        Args:
            action: Action name (e.g., "A", "Up", "Start")
        """
        if action in self.input_mapping:
            fceux_key = self.input_mapping[action]
            
            try:
                # Send the input command
                response = requests.post(
                    f"{self.http_url}/input",
                    data={"key": fceux_key},
                    timeout=1
                )
                
                if response.status_code == 200:
                    logger.debug(f"Sent input action: {action}")
                else:
                    logger.warning(f"Failed to send input to FCEUX: {response.status_code}")
            except requests.RequestException as e:
                logger.error(f"Failed to send input to FCEUX: {e}")
        else:
            logger.warning(f"Unsupported action for FCEUX: {action}")
    
    def close(self) -> None:
        """
        Close the emulator and clean up resources.
        """
        if hasattr(self, 'fceux_process') and self.fceux_process:
            logger.info("Stopping FCEUX emulator")
            
            try:
                # First try to exit gracefully through the API
                requests.post(f"{self.http_url}/exit", timeout=1)
                time.sleep(0.5)  # Give it a moment to close
            except:
                pass  # API might already be down, continue to forced termination
            
            # If process is still running, terminate it
            if self.fceux_process.poll() is None:
                self.fceux_process.terminate()
                try:
                    self.fceux_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    # If termination times out, kill the process
                    self.fceux_process.kill()
            
            logger.info("FCEUX emulator stopped")
            
            # Clean up the temporary Lua script
            if hasattr(self, 'lua_script_path') and os.path.exists(self.lua_script_path):
                os.unlink(self.lua_script_path)
                logger.debug(f"Removed Lua script: {self.lua_script_path}")
            
            # Unregister the atexit handler
            try:
                atexit.unregister(self.close)
            except:
                pass  # Ignore if already unregistered