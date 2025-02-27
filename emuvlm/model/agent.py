"""
LLM agent for analyzing game frames and deciding on actions.
"""
import base64
import io
import json
import logging
import re
import requests
import time
import hashlib
import os
import platform
import sys
from pathlib import Path
from PIL import Image, ImageChops
from typing import Dict, List, Optional, Any, Union, Tuple

logger = logging.getLogger(__name__)

# Import llama.cpp server module if available
try:
    from .llama_cpp import server as llama_cpp_server
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    logger.warning("llama.cpp not available. To use llama.cpp backend (recommended for macOS), install: pip install llama-cpp-python>=0.2.50")

class LLMAgent:
    """
    Uses an LLM with vision capabilities to decide game actions based on screenshots.
    
    Supports:
    - Qwen2.5-VL-3B-Instruct via vLLM server (Linux)
    - LLaVA via llama.cpp (macOS, Windows, Linux)
    """
    
    def __init__(self, model_config: Dict[str, Any], valid_actions: List[str], use_summary: bool = False):
        """
        Initialize the LLM Agent.
        
        Args:
            model_config: Configuration for the model API (URL, parameters, etc.)
            valid_actions: List of valid actions the agent can choose from
            use_summary: Whether to use the summarization feature
        """
        self.model_config = model_config
        self.api_url = model_config.get('api_url', 'http://localhost:8000')
        self.valid_actions = valid_actions
        self.use_summary = use_summary
        
        # For custom system message in testing
        self.custom_system_message = None
        
        # Determine backend type
        self.backend = model_config.get('backend', 'auto')
        if self.backend == 'auto':
            # Auto-detect: use llama.cpp on macOS, vLLM on Linux
            system = platform.system()
            if system == 'Darwin':  # macOS
                self.backend = 'llama.cpp'
            else:
                self.backend = 'vllm'
        
        # Validate backend availability
        if self.backend == 'llama.cpp' and not LLAMA_CPP_AVAILABLE:
            raise ImportError(
                "llama.cpp backend requested but not available. "
                "Please install with: pip install llama-cpp-python>=0.2.50"
            )
            
        # Start integrated server if needed
        self._maybe_start_server()
        
        # For summary feature
        self.history = []
        self.summary = ""
        self.summary_interval = model_config.get('summary_interval', 10)  # Summarize every X turns
        self.turn_count = 0
        
        # For frame caching
        self.enable_cache = model_config.get('enable_cache', True)
        self.cache_dir = Path(model_config.get('cache_dir', 'cache'))
        self.frame_cache = {}  # Map from frame hash to (action, confidence)
        self.similarity_threshold = model_config.get('similarity_threshold', 0.95)
        self.last_frame = None
        self.last_frame_hash = None
        
        # For debugging and testing
        self._last_raw_response = None  # Store the raw response for debugging
        
        # Create cache directory if it doesn't exist
        if self.enable_cache and not self.cache_dir.exists():
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created cache directory: {self.cache_dir}")
        
        logger.info(f"LLM Agent initialized with backend: {self.backend}")
        logger.info(f"API URL: {self.api_url}")
        logger.info(f"Valid actions: {len(valid_actions)} possible actions")
        logger.info(f"Summary feature is {'enabled' if use_summary else 'disabled'}")
        logger.info(f"Frame caching is {'enabled' if self.enable_cache else 'disabled'}")
        logger.info(f"JSON schema support is {'enabled' if model_config.get('json_schema_support', True) else 'disabled'}")
    
    def _maybe_start_server(self):
        """
        Start an integrated model server if configured.
        """
        autostart = self.model_config.get('autostart_server', False)
        if not autostart:
            return
            
        # Start the appropriate server based on backend
        if self.backend == 'llama.cpp':
            # Get model parameters
            model_path = self.model_config.get('model_path')
            if not model_path:
                logger.error("model_path must be specified when using llama.cpp backend with autostart")
                raise ValueError("model_path not specified")
                
            # Resolve relative path if needed
            if not os.path.isabs(model_path):
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                model_path = os.path.join(base_dir, model_path)
                logger.info(f"Resolved relative model path to: {model_path}")
                
            # Verify the model file exists
            if not os.path.exists(model_path):
                logger.error(f"Model file not found: {model_path}")
                logger.error(f"Please run 'emuvlm-download-model' to download the required model")
                raise FileNotFoundError(f"Model file not found: {model_path}")
                
            # Parse host and port from API URL
            try:
                host_part = self.api_url.split('://')[1].split(':')[0]
                host = host_part if host_part != 'localhost' else '127.0.0.1'
                port = int(self.api_url.split(':')[-1].split('/')[0])
            except (IndexError, ValueError) as e:
                logger.error(f"Failed to parse host/port from API URL: {self.api_url}")
                raise ValueError(f"Invalid API URL format: {self.api_url}") from e
            
            # Start server with additional configuration options
            logger.info(f"Starting llama.cpp server with model: {model_path}")
            llama_cpp_server.start_server(
                model_path=model_path,
                host=host,
                port=port,
                n_gpu_layers=self.model_config.get('n_gpu_layers', -1),
                n_ctx=self.model_config.get('n_ctx', 2048),
                verbose=self.model_config.get('verbose', False)
            )
            
            # Verify server is running by checking the API endpoint
            logger.info("Verifying server connection...")
            max_retries = 10
            for i in range(max_retries):
                if llama_cpp_server.check_server_status(host, port):
                    logger.info(f"Successfully connected to llama.cpp server at {self.api_url}")
                    break
                if i == max_retries - 1:
                    logger.error(f"Failed to connect to server after {max_retries} attempts")
                    raise ConnectionError(f"Could not connect to llama.cpp server at {self.api_url}")
                time.sleep(1)
                
        elif self.backend == 'vllm':
            # vLLM can't be started programmatically as easily, so we'll just log a message
            if platform.system() == 'Darwin':
                logger.warning("vLLM is not supported on macOS. Switching to llama.cpp backend is recommended.")
            logger.info("vLLM server autostart not implemented. Please use ./start_vllm_server.sh")
    
    def decide_action(self, frame: Image.Image) -> str:
        """
        Analyze the current game frame and decide on the next action.
        
        Args:
            frame: PIL Image of the current game frame
            
        Returns:
            str: The agent's decision as text, or None for no action
        """
        # Check if loading screen detection is enabled and this is a loading screen
        detect_loading = self.model_config.get('detect_loading_screens', False)
        if detect_loading and self._is_loading_screen(frame):
            logger.info("Loading screen detected - choosing not to act")
            return None
            
        # Check cache first if enabled
        if self.enable_cache:
            # Check if this frame is very similar to the last one
            if self.last_frame is not None:
                similarity = self._calculate_frame_similarity(frame, self.last_frame)
                if similarity > self.similarity_threshold:
                    logger.info(f"Frame is similar to previous frame (similarity: {similarity:.4f})")
                    # If we have a cached action for the last frame, use it
                    if self.last_frame_hash in self.frame_cache:
                        cached_action = self.frame_cache[self.last_frame_hash]
                        logger.info(f"Using cached action: {cached_action}")
                        return cached_action
            
            # Calculate frame hash for caching
            frame_hash = self._calculate_frame_hash(frame)
            
            # Save for next frame comparison
            self.last_frame = frame.copy()
            self.last_frame_hash = frame_hash
            
            # Check if we have this exact frame cached
            if frame_hash in self.frame_cache:
                cached_action = self.frame_cache[frame_hash]
                logger.info(f"Cache hit for frame hash {frame_hash[:8]}... - Action: {cached_action}")
                return cached_action
        
        # If we get here, we need to query the model
        # Prepare the image for the model
        image_data = self._prepare_image(frame)
        
        # Get the game type from config for game-specific prompts
        game_type = self._get_game_type()
        
        # Construct the prompt with context-specific enhancements
        prompt = self._construct_prompt(image_data, game_type=game_type)
        
        # Query the model
        response = self._query_model(prompt)
        
        # Handle different response formats
        valid_action = None
        
        # If the response looks like JSON, parse it with our parse_action method
        if response and (response.strip().startswith('{') and response.strip().endswith('}')):
            valid_action = self.parse_action(response)
            logger.info(f"Parsed JSON response into action: {valid_action}")
        elif response in self.valid_actions:
            # If the response is already a valid action, use it directly
            valid_action = response
            logger.info(f"Using direct action response: {valid_action}")
        else:
            # For any other responses, use parse_action to get a valid action
            valid_action = self.parse_action(response)
            logger.info(f"Parsed text response into action: {valid_action}")
        
        # Update history if summary feature is enabled
        if self.use_summary:
            self._update_history(frame, valid_action)
            
            # Also store the reasoning if available and the response is JSON
            try:
                if response and response.strip().startswith('{'):
                    json_data = json.loads(response)
                    if 'reasoning' in json_data:
                        reason = json_data['reasoning']
                        # Append reasoning to the latest history entry
                        if self.history:
                            self.history[-1] += f" - Reasoning: {reason}"
            except (json.JSONDecodeError, KeyError):
                # Ignore any JSON parsing errors here
                pass
        
        # Cache the result if frame caching is enabled
        if self.enable_cache and self.last_frame_hash is not None:
            self.frame_cache[self.last_frame_hash] = valid_action
            # Save the frame to disk for future analysis if needed
            self._save_frame_to_cache(frame, self.last_frame_hash, valid_action)
            
        return valid_action
        
    def _get_game_type(self) -> str:
        """
        Get the current game type from the model config.
        This is used to load appropriate game-specific prompts.
        
        Returns:
            str: The game type ID (e.g., "pokemon", "zelda", etc.) or empty string if not set
        """
        # Check if the model config contains a game_type field
        return self.model_config.get('game_type', '')
    
    def parse_action(self, action_text: str) -> str:
        """
        Parse the model's response into a valid action.
        
        Args:
            action_text: Text response from the model
            
        Returns:
            str: A valid action or empty string if parsing failed
        """
        # First, try to parse the response as JSON
        try:
            # Check if the response is a valid JSON
            if action_text and (action_text.strip().startswith('{') and action_text.strip().endswith('}')):
                response_json = json.loads(action_text)
                
                # Check if the JSON has the expected structure
                if 'action' in response_json:
                    chosen_action = response_json['action']
                    
                    # If the action is in our valid actions list, return it
                    if chosen_action in self.valid_actions:
                        logger.info(f"Parsed valid action from JSON: {chosen_action}")
                        return chosen_action
                    # Handle "None" action specifically
                    elif chosen_action == "None":
                        logger.info("Agent chose to do nothing (None action)")
                        # Return None to indicate no action should be taken
                        return None
                    
                    # Log the reasoning if available
                    if 'reasoning' in response_json:
                        logger.debug(f"Agent reasoning: {response_json['reasoning']}")
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            # Continue with text-based parsing if JSON parsing fails
        
        # Handle empty responses
        if not action_text or action_text.strip() == "":
            # For empty responses, default to a reasonable action like Up
            logger.warning("Received empty response from model, defaulting to 'Up'")
            return "Up"
            
        # Convert to lowercase for case-insensitive matching
        text = action_text.lower()
        
        # Try direct matching first (with normalization)
        for valid_action in self.valid_actions:
            # Check for exact match
            if valid_action.lower() == text:
                return valid_action
            
            # Check for action within text
            action_pattern = rf'\b{re.escape(valid_action.lower())}\b'
            if re.search(action_pattern, text):
                return valid_action
        
        # Try more flexible matching with context
        context_patterns = [
            (r'press\s+(\w+)', 1),  # "press A" -> "A"
            (r'push\s+(\w+)', 1),   # "push B" -> "B"
            (r'move\s+(up|down|left|right)', 1),  # "move up" -> "up"
            (r'go\s+(up|down|left|right)', 1),    # "go left" -> "left"
            (r'select\s+(\w+)', 1),  # "select start" -> "start"
            (r'button\s+(\w+)', 1),  # "button A" -> "A"
        ]
        
        for pattern, group in context_patterns:
            match = re.search(pattern, text)
            if match:
                action_candidate = match.group(group).capitalize()
                # Verify it's in our valid actions list
                if action_candidate in self.valid_actions:
                    return action_candidate
                # Special case for directional inputs
                if action_candidate.lower() in ['up', 'down', 'left', 'right']:
                    capitalized = action_candidate.capitalize()
                    if capitalized in self.valid_actions:
                        return capitalized
        
        # If we could match anything, try to find a default based on the context
        if "up" in text or "move" in text:
            return "Up"
        if "a" in text or "button" in text:
            return "A"
            
        # If all else fails, default to a safe action
        logger.warning(f"Could not parse a valid action from: '{action_text}', defaulting to 'Up'")
        return "Up"
    
    def _prepare_image(self, image: Image.Image) -> str:
        """
        Convert a PIL image to base64 for the model API.
        
        Args:
            image: PIL Image to convert
            
        Returns:
            str: Base64-encoded image
        """
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
        return img_str
    
    def _construct_prompt(self, image_data: str, game_type: str = '') -> Dict[str, Any]:
        """
        Construct the prompt for the model, including the image and instructions.
        
        Args:
            image_data: Base64-encoded image string
            game_type: String identifier for the game type to use specific prompts
            
        Returns:
            Dict: Prompt in the format expected by the model API
        """
        # List available actions for the model
        action_list = ", ".join(self.valid_actions)
        
        # Create JSON schema for response validation
        action_enum = self.valid_actions.copy()
        action_enum.append("None")  # Add None as a valid action
        
        json_schema = {
            "type": "object",
            "properties": {
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation of why this action was chosen based on the game state"
                },
                "action": {
                    "type": "string",
                    "enum": action_enum,
                    "description": f"The selected action from the list: {action_list} or None to do nothing"
                }
            },
            "required": ["action", "reasoning"],
            "additionalProperties": False
        }
        
        # Get additional prompt pieces from model config
        prompt_additions = self.model_config.get('prompt_additions', [])
        
        # Base system message that's used for all games
        base_system_message = f"""You are an AI playing a turn-based video game.
Analyze the game screen and decide the best action to take next.
You can choose from these actions: {action_list}, or choose "None" to do nothing.

IMPORTANT INSTRUCTION ABOUT "NONE":
- If you see a loading screen, choose "None"
- If text tells you to wait or not press buttons, choose "None"
- If the game is processing something and no input is needed, choose "None"
- Only press buttons when it's clearly required by the game state

EXAMPLES:
1. If you see a battle menu with options, choose an appropriate button ("A" to select, etc.)
2. If you see a character that needs to move, choose a direction ("Up", "Down", etc.)
3. If you see text saying "Loading..." or "Please wait", choose "None"
4. If you see a warning saying "Do not press buttons", choose "None"
"""

        # Game-specific instructions based on game_type
        game_specific_instructions = ""
        
        # Add game-specific instructions based on the game type
        if game_type == 'pokemon':
            game_specific_instructions = """POKÉMON GAMEPLAY INSTRUCTIONS:
- Press A to advance through dialog text and make selections in menus
- Use Up/Down to navigate menus, and Left/Right to change pages sometimes
- Press B to cancel or go back
- Press Start to open the game menu
- In battles, choose Attack, Pokémon, Item, or Run using directional keys and A to select

POKÉMON-SPECIFIC EXAMPLES:
1. If you see a battle menu with options like "FIGHT", "PKMN", "ITEM", "RUN", navigate with directional buttons and select with A
2. If you see dialog text that has finished appearing, press A to continue
3. If you see dialog text still being typed out, choose "None" and wait
4. If you're in the overworld, use directional buttons to navigate
5. If you see a menu, use Up/Down to navigate and A to select
"""
        elif game_type == 'zelda':
            game_specific_instructions = """ZELDA GAMEPLAY INSTRUCTIONS:
- Press A to use your sword or interact with objects and people
- Press B to use your selected item
- Use directional buttons to move Link around the world
- Press Start to open the inventory to select different items
- Pay attention to the environment for clues about where to go next

ZELDA-SPECIFIC EXAMPLES:
1. If you see enemies, press A to swing your sword to attack
2. If you see NPCs, press A to talk to them
3. If you see a chest, move Link toward it and press A to open
4. If you're in a menu, use directional buttons to navigate and A to select
5. If you see signs or text appearing, wait for it to finish then press A to continue
"""
        # Add more game types as needed
        
        # Add any custom prompt additions from the config
        custom_instructions = "\n".join(prompt_additions) if prompt_additions else ""
        
        # Format based on the backend
        if self.backend == 'llama.cpp':
            # Check if we have a custom system message (for testing)
            if self.custom_system_message:
                system_message = self.custom_system_message
            else:
                # Enhanced Pokémon-specific instructions
                system_message = f"""You are an AI playing a Pokémon game (likely Pokémon Red, Blue, or Yellow).
Analyze the game screen and decide the best action to take next.
You can choose from these actions: {action_list}, or choose "None" to do nothing.

IMPORTANT INSTRUCTION ABOUT POKÉMON GAMEPLAY:
- Press A to advance through dialog text and make selections in menus
- Use Up/Down to navigate menus, and Left/Right to change pages sometimes
- Press B to cancel or go back
- Press Start to open the game menu
- In battles, choose Attack, Pokémon, Item, or Run using directional keys and A to select

IMPORTANT INSTRUCTION ABOUT "NONE":
- If you see a loading screen, choose "None"
- If text is still appearing (being typed out), choose "None"
- If an animation is playing, choose "None"
- Only press buttons when it's clearly required by the game state

POKÉMON-SPECIFIC EXAMPLES:
1. If you see a battle menu with options like "FIGHT", "PKMN", "ITEM", "RUN", navigate with directional buttons and select with A
2. If you see dialog text that has finished appearing, press A to continue
3. If you see dialog text still being typed out, choose "None" and wait
4. If you're in the overworld, use directional buttons to navigate
5. If you see a menu, use Up/Down to navigate and A to select

You MUST respond ONLY with a JSON object in this EXACT format, with no other text:
{{
  "action": "A",
  "reasoning": "I'm pressing A to select the attack option in this Pokémon battle. The battle menu is open and my cursor is on the attack option."
}}

or

{{
  "action": "None",
  "reasoning": "I'm choosing to do nothing because the text is still appearing on screen and I should wait until it's finished."
}}

Where "action" is EXACTLY one of: {', '.join(self.valid_actions + ['None'])}"""
            else:
                # Enhanced detailed instructions with more examples for llama.cpp
                system_message = f"""You are an AI playing a turn-based video game.
Analyze the game screen and decide the best action to take next.
You can choose from these actions: {action_list}, or choose "None" to do nothing.

IMPORTANT INSTRUCTION ABOUT "NONE":
- If you see a loading screen, choose "None"
- If text tells you to wait or not press buttons, choose "None"
- If the game is processing something and no input is needed, choose "None"
- Only press buttons when it's clearly required by the game state

EXAMPLES:
1. If you see a battle menu with options, choose an appropriate button ("A" to select, etc.)
2. If you see a character that needs to move, choose a direction ("Up", "Down", etc.)
3. If you see text saying "Loading..." or "Please wait", choose "None"
4. If you see a warning saying "Do not press buttons", choose "None"

You MUST respond ONLY with a JSON object in this EXACT format, with no other text:
{{
  "action": "A",
  "reasoning": "I'm pressing A to select an attack in this battle. The screen shows that I'm in a battle and need to choose an action."
}}

or

{{
  "action": "None",
  "reasoning": "I'm choosing to do nothing because the screen shows a loading message and indicates I should wait."
}}

Where "action" is EXACTLY one of: {', '.join(self.valid_actions + ['None'])}"""
        else:
            # For vLLM, the json_schema enforces the format, but we still improve the instructions
            if is_pokemon:
                # Pokémon-specific instructions for vLLM
                system_message = f"""You are an AI playing a Pokémon game (likely Pokémon Red, Blue, or Yellow).
Analyze the game screen and decide the best action to take next.
You can choose from these actions: {action_list}, or choose "None" to do nothing.

IMPORTANT INSTRUCTION ABOUT POKÉMON GAMEPLAY:
- Press A to advance through dialog text and make selections in menus
- Use Up/Down to navigate menus, and Left/Right to change pages sometimes
- Press B to cancel or go back
- Press Start to open the game menu
- In battles, choose Attack, Pokémon, Item, or Run using directional keys and A to select

IMPORTANT INSTRUCTION ABOUT "NONE":
- If you see a loading screen, choose "None"
- If text is still appearing (being typed out), choose "None"
- If an animation is playing, choose "None"
- Only press buttons when it's clearly required by the game state

POKÉMON-SPECIFIC EXAMPLES:
1. If you see a battle menu with options like "FIGHT", "PKMN", "ITEM", "RUN", navigate with directional buttons and select with A
2. If you see dialog text that has finished appearing, press A to continue
3. If you see dialog text still being typed out, choose "None" and wait
4. If you're in the overworld, use directional buttons to navigate
5. If you see a menu, use Up/Down to navigate and A to select

You MUST respond with a JSON object containing exactly two fields:
- 'action': EXACTLY one of: {', '.join(self.valid_actions + ['None'])}
- 'reasoning': A brief explanation of your choice

Your response will be automatically validated against a JSON schema."""
            else:
                # Standard instructions for vLLM
                system_message = f"""You are an AI playing a turn-based video game.
Analyze the game screen and decide the best action to take next.
You can choose from these actions: {action_list}, or choose "None" to do nothing.

IMPORTANT INSTRUCTION ABOUT "NONE":
- If you see a loading screen, choose "None"
- If text tells you to wait or not press buttons, choose "None"
- If the game is processing something and no input is needed, choose "None"
- Only press buttons when it's clearly required by the game state

EXAMPLES:
1. If you see a battle menu with options, choose an appropriate button ("A" to select, etc.)
2. If you see a character that needs to move, choose a direction ("Up", "Down", etc.) 
3. If you see text saying "Loading..." or "Please wait", choose "None"
4. If you see a warning saying "Do not press buttons", choose "None"

You MUST respond with a JSON object containing exactly two fields:
- 'action': EXACTLY one of: {', '.join(self.valid_actions + ['None'])}
- 'reasoning': A brief explanation of your choice

Your response will be automatically validated against a JSON schema."""
        
        # Include summary if enabled and available
        if self.use_summary and self.summary:
            system_message += f"\n\nHere's a summary of what has happened so far in the game:\n{self.summary}"
        
        user_message = "What action should I take in this game? Choose one of the available actions or 'None' to do nothing."
        
        # Construct the prompt differently based on backend
        if self.backend == 'llama.cpp':
            # For llama.cpp, we need to format the messages differently
            # Format based on OpenAI Vision API
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": [
                    {"type": "text", "text": user_message},
                    {"type": "image_url", 
                     "image_url": {"url": f"data:image/png;base64,{image_data}"}}
                ]}
            ]
        else:
            # For vLLM, use the standard format
            messages = [
                {"role": "system", "content": system_message},
                {
                    "role": "user", 
                    "content": [
                        {"type": "image", "image": f"data:image/png;base64,{image_data}"},
                        {"type": "text", "text": user_message}
                    ]
                }
            ]
        
        # Set model parameters based on backend
        params = {
            "messages": messages,
            "max_tokens": self.model_config.get('max_tokens', 200),  # Increased for JSON response
            "temperature": self.model_config.get('temperature', 0.2),  # Lower temperature for more focused responses
            "stream": False
        }
        
        # Add appropriate response format based on backend
        if self.backend == 'llama.cpp':
            # llama.cpp uses json_object type format
            params["response_format"] = {
                "type": "json_object"
            }
        else:
            # vLLM uses json_schema type format
            params["response_format"] = {
                "type": "json_schema",
                "schema": json_schema
            }
        
        return params
    
    def _query_model(self, prompt: Dict[str, Any]) -> str:
        """
        Send the prompt to the model API and get the response.
        
        Args:
            prompt: Complete prompt in the API's expected format
            
        Returns:
            str: Model's text response or JSON string
        """
        try:
            start_time = time.time()
            
            # Check if backend supports JSON response format
            supports_json_response = True
            
            # Some older versions may not support response_format at all
            if self.model_config.get('json_schema_support', True) is False:
                # Remove the response_format from the prompt if not supported
                if 'response_format' in prompt:
                    logger.warning("JSON response format not supported by this backend, removing response_format")
                    prompt.pop('response_format')
                    supports_json_response = False
            
            # Both backends (vLLM and llama.cpp) provide OpenAI-compatible API
            logger.debug(f"Sending request to {self.backend} backend at {self.api_url}")
            
            # For debugging: print out the exact payload we're sending
            logger.debug(f"Request payload: {json.dumps(prompt)}")
            
            response = requests.post(
                f"{self.api_url}/v1/chat/completions",
                json=prompt,
                headers={"Content-Type": "application/json"},
                timeout=60  # Models with vision can take longer, especially first requests
            )
            
            elapsed_time = time.time() - start_time
            logger.info(f"Model API call took {elapsed_time:.2f} seconds")
            
            if response.status_code != 200:
                logger.error(f"API error: {response.status_code} - {response.text}")
                # Provide more detailed error with backend info
                backend_info = f"using {self.backend} backend"
                return f"Error {response.status_code} {backend_info}"
            
            result = response.json()
            # Extract the text content from the API response
            # The exact path should be the same for both backends (OpenAI format)
            try:
                text_response = result["choices"][0]["message"]["content"]
                
                # Store the raw response for debugging and testing
                self._last_raw_response = text_response
                
                # Check for JSON format response (if we're using JSON response format)
                if supports_json_response:
                    try:
                        # If the response starts with { it's likely a JSON 
                        if text_response.strip().startswith('{'): 
                            # Sometimes the model generates invalid JSON with extra tokens at the end
                            # Find the last valid closing brace
                            json_str = text_response.strip()
                            
                            # First try: Look for a complete JSON object
                            try:
                                # Try to find a valid JSON object by looking for matching brackets
                                brace_count = 0
                                for i, char in enumerate(json_str):
                                    if char == '{':
                                        brace_count += 1
                                    elif char == '}':
                                        brace_count -= 1
                                        if brace_count == 0:
                                            # We found a complete JSON object
                                            json_str = json_str[:i+1]
                                            break
                                        
                                # Now try to parse the cleaned JSON
                                json_data = json.loads(json_str)
                            except json.JSONDecodeError:
                                # Second try: Look for a partial JSON with just the action key
                                logger.warning("Failed first JSON parse attempt, trying to extract partial JSON")
                                # Try to directly extract an action field 
                                full_text = json_str
                                
                                # Try to find the action field
                                action_match = re.search(r'"action"\s*:\s*"([^"]+)"', full_text, re.IGNORECASE)
                                if not action_match:
                                    # Also try with single quotes
                                    action_match = re.search(r'"action"\s*:\s*\'([^\']+)\'', full_text, re.IGNORECASE)
                                
                                if not action_match:
                                    # Try capitalized version
                                    action_match = re.search(r'"Action"\s*:\s*"([^"]+)"', full_text, re.IGNORECASE)
                                
                                # Direct check for action terms
                                if not action_match:
                                    # Look for any of our valid actions surrounded by quotes
                                    actions_pattern = '|'.join(self.valid_actions + ['None'])
                                    direct_action = re.search(rf'"({actions_pattern})"', full_text)
                                    if direct_action:
                                        action_val = direct_action.group(1)
                                        logger.info(f"Found direct action mention: {action_val}")
                                        json_data = {"action": action_val}
                                    else:
                                        # If we can't find an action, re-raise to fall back to text parsing
                                        raise
                                else:
                                    action_val = action_match.group(1)
                                    logger.info(f"Extracted action from partial JSON: {action_val}")
                                    # Create a minimal valid JSON
                                    json_data = {"action": action_val}
                            
                            # Validate that the JSON response has the action field
                            if 'action' in json_data:
                                chosen_action = json_data['action']
                            elif 'Action' in json_data:  # Try different capitalization
                                chosen_action = json_data['Action']
                            else:
                                # Try finding something that looks like an action, allowing for the most flexibility
                                for key, value in json_data.items():
                                    if (isinstance(value, str) and 
                                        (value in self.valid_actions or value == "None")):
                                        logger.info(f"Found action key '{key}' with valid value: {value}")
                                        chosen_action = value
                                        break
                                else:
                                    chosen_action = None
                                
                            # If it's a valid action, return it directly
                            if chosen_action in self.valid_actions:
                                logger.info(f"Valid JSON action response: {chosen_action}")
                                
                                # Log reasoning if available
                                if 'reasoning' in json_data:
                                    logger.debug(f"Agent reasoning: {json_data['reasoning']}")
                                elif 'Reasoning' in json_data:
                                    logger.debug(f"Agent reasoning: {json_data['Reasoning']}")
                                
                                return chosen_action
                            
                            # If it's "None", return None to indicate no action
                            elif chosen_action == "None":
                                logger.info("Agent chose to do nothing ('None' action)")
                                return None  # Return None to indicate no action
                            
                            # Return the full JSON string for further parsing
                            return text_response
                    except json.JSONDecodeError:
                        # Not JSON or invalid JSON, continue with text parsing
                        logger.warning("Response is not valid JSON, falling back to text parsing")
                
                # Process as regular text response
                clean_response = text_response.strip()
                
                # If the response is one of our valid actions, return it directly
                for action in self.valid_actions:
                    if action.lower() == clean_response.lower():
                        return action
                    
                    # Check if action appears as a word in the response
                    action_pattern = rf'\b{re.escape(action.lower())}\b'
                    if re.search(action_pattern, clean_response.lower()):
                        return action
                
                return clean_response
            except (KeyError, IndexError) as e:
                logger.error(f"Failed to parse API response: {e}")
                logger.debug(f"Response: {result}")
                # Add retry logic for connection issues
                if "choices" not in result:
                    logger.warning("Response missing 'choices' field, API may be incompatible")
                return "Error parsing response"
                
        except requests.RequestException as e:
            logger.error(f"Request to model API failed: {e}")
            if "Connection refused" in str(e):
                logger.error(f"Connection refused. Please ensure the {self.backend} server is running at {self.api_url}")
            elif "timed out" in str(e):
                logger.error(f"Request timed out. The {self.backend} server might be overloaded or processing a large request")
            return "Error connecting to model server"
    
    def _update_history(self, frame: Image.Image, response: str) -> None:
        """
        Update the history and generate summaries if needed.
        This is only used when the summary feature is enabled.
        
        Args:
            frame: Current game frame
            response: Model's action response
        """
        # Add this turn to history
        self.history.append(f"Turn {self.turn_count}: Model chose action '{response}'")
        self.turn_count += 1
        
        # Check if it's time to generate a summary
        if self.use_summary and self.turn_count % self.summary_interval == 0 and self.history:
            self._generate_summary()
    
    def _generate_summary(self) -> None:
        """
        Generate a summary of the game history so far using the model.
        This is an additional call to the model.
        """
        if not self.history:
            return
            
        # Prepare a prompt asking for a summary
        history_text = "\n".join(self.history)
        summary_prompt = {
            "messages": [
                {"role": "system", "content": "Summarize the following game history in a concise paragraph."},
                {"role": "user", "content": history_text}
            ],
            "max_tokens": 250,
            "temperature": 0.3,
        }
        
        try:
            # Call the model for summarization
            response = requests.post(
                f"{self.api_url}/v1/chat/completions",
                json=summary_prompt,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                self.summary = result["choices"][0]["message"]["content"].strip()
                logger.info(f"Generated new summary: {self.summary}")
                
                # After summarizing, clear the detailed history
                self.history = []
            else:
                logger.error(f"Summary generation failed: {response.status_code} - {response.text}")
                
        except requests.RequestException as e:
            logger.error(f"Summary request failed: {e}")
    
    def _calculate_frame_hash(self, frame: Image.Image) -> str:
        """
        Calculate a hash for a frame to use as a cache key.
        
        Args:
            frame: The PIL Image to hash
            
        Returns:
            str: Hexadecimal hash string
        """
        # Convert to bytes
        buffered = io.BytesIO()
        # Use a lower quality JPEG to ignore minor pixel differences
        frame.save(buffered, format="JPEG", quality=90)
        img_bytes = buffered.getvalue()
        
        # Calculate hash
        return hashlib.md5(img_bytes).hexdigest()
    
    def _calculate_frame_similarity(self, frame1: Image.Image, frame2: Image.Image) -> float:
        """
        Calculate similarity between two frames.
        
        Args:
            frame1: First PIL Image
            frame2: Second PIL Image
            
        Returns:
            float: Similarity score between 0 and 1
        """
        # Ensure the frames are the same size
        if frame1.size != frame2.size:
            frame2 = frame2.resize(frame1.size)
        
        # Calculate difference
        diff = ImageChops.difference(frame1.convert('RGB'), frame2.convert('RGB'))
        
        # Get statistics
        stat = diff.convert('L').getdata()
        diff_sum = sum(stat)
        max_diff = 255 * len(stat)
        
        # Calculate similarity (inverted difference)
        if max_diff == 0:
            return 1.0
        return 1.0 - (diff_sum / max_diff)
        
    def _is_loading_screen(self, frame: Image.Image) -> bool:
        """
        Detect if a frame is likely a loading screen.
        
        Args:
            frame: The PIL Image to analyze
            
        Returns:
            bool: True if the frame appears to be a loading screen
        """
        # Convert to grayscale for analysis
        gray = frame.convert('L')
        
        # Get pixel data
        pixels = list(gray.getdata())
        
        # Calculate basic statistics
        unique_colors = len(set(pixels))
        
        # Calculate standard deviation of pixel values (low std dev indicates uniform screen)
        import numpy as np
        pixel_array = np.array(pixels)
        std_dev = np.std(pixel_array)
        
        # Check for uniform/near-uniform frames (loading screens often have few colors)
        # For Pokemon games specifically, we want to be careful not to treat dialog boxes as loading screens
        # So we'll check both the unique color count and standard deviation
        
        # Very low color count is almost always a loading screen
        if unique_colors <= 2:
            logger.info(f"Detected loading screen: only {unique_colors} unique colors")
            return True
            
        # Low std dev combined with few colors often indicates loading screens
        if unique_colors < 5 and std_dev < 30:
            logger.info(f"Detected potential loading screen: {unique_colors} unique colors, std dev: {std_dev:.2f}")
            return True
            
        # Check for text patterns that suggest loading/waiting
        # This would require OCR, which is complex - we'll rely on the model for this
        
        logger.debug(f"Not a loading screen: {unique_colors} unique colors, std dev: {std_dev:.2f}")
        return False
    
    def _save_frame_to_cache(self, frame: Image.Image, frame_hash: str, action: str) -> None:
        """
        Save a frame to the cache directory for later analysis.
        
        Args:
            frame: The PIL Image to save
            frame_hash: The frame's hash
            action: The action that was chosen for this frame
        """
        if not self.enable_cache:
            return
            
        # Only save a subset of frames to avoid filling up the disk
        # Save 1 in every 10 frames, or if it's an important action
        important_actions = ['A', 'Start', 'Select']
        
        should_save = (self.turn_count % 10 == 0) or any(a in action for a in important_actions)
        
        if should_save:
            # Create a filename with the hash and action
            short_hash = frame_hash[:8]  # First 8 characters is enough to identify
            filename = f"{short_hash}_{action.replace(' ', '_')}.png"
            filepath = self.cache_dir / filename
            
            # Save the frame
            frame.save(filepath)
            logger.debug(f"Saved frame to cache: {filepath}")
    
    def clear_cache(self) -> None:
        """
        Clear the frame cache.
        """
        self.frame_cache = {}
        self.last_frame = None
        self.last_frame_hash = None
        logger.info("Frame cache cleared")