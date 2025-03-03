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
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

# Import llama.cpp server module if available
try:
    from .llama_cpp import server as llama_cpp_server

    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    logger.warning(
        'llama.cpp not available. To use llama.cpp backend (recommended for macOS), install with: pip install -e ".[macos]"'
    )


class LLMAgent:
    """
    Uses an LLM with vision capabilities to decide game actions based on screenshots.

    Supports:
    - OpenAI GPT-4o models with vision
    - Claude with vision (Haiku, Sonnet, Opus)
    - Mistral Pixtral series of models
    - Qwen2.5-VL-3B-Instruct-AWQ via vLLM server (Linux)
    - LLaVA via llama.cpp (macOS, Windows, Linux)
    - Custom OpenAI API-compatible servers
    """

    def __init__(
        self, model_config: Dict[str, Any], valid_actions: List[str], use_summary: bool = False
    ):
        """
        Initialize the LLM Agent.

        Args:
            model_config: Configuration for the model API (URL, parameters, etc.)
            valid_actions: List of valid actions the agent can choose from
            use_summary: Whether to use the summarization feature
        """
        self.model_config = model_config
        self.api_url = model_config.get("api_url", "http://localhost:8000")
        self.valid_actions = valid_actions
        self.use_summary = use_summary

        # For custom system message in testing
        self.custom_system_message = None

        # Setup Jinja2 environment for template rendering
        templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
        self.jinja_env = Environment(loader=FileSystemLoader(templates_dir))

        # Determine backend type
        self.backend = model_config.get("backend", "auto")

        # Handle the new provider option for external APIs
        self.provider = model_config.get("provider", "local")
        self.model_name = model_config.get("model_name", None)

        # Set API keys if provided
        self.api_key = model_config.get("api_key", None)
        self.organization_id = model_config.get("organization_id", None)

        # Auto-detect local backend if needed
        if self.backend == "auto" and self.provider == "local":
            # Auto-detect: use llama.cpp on macOS, vLLM on Linux
            system = platform.system()
            if system == "Darwin":  # macOS
                self.backend = "llama.cpp"
            else:
                self.backend = "vllm"

            logger.info(f"Auto-detected local backend: {self.backend}")

        # Validate backend availability for local providers
        if self.provider == "local" and self.backend == "llama.cpp" and not LLAMA_CPP_AVAILABLE:
            raise ImportError(
                "llama.cpp backend requested but not available. "
                "Please install with: pip install llama-cpp-python>=0.2.50"
            )

        # For external API providers, we don't need to start a server
        if self.provider == "local":
            # Start integrated server if needed (only for local backends)
            self._maybe_start_server()
        else:
            logger.info(f"Using external API provider: {self.provider}")
            logger.info(f"API URL: {self.api_url}")
            if self.model_name:
                logger.info(f"Model: {self.model_name}")

        # For conversation history tracking
        self.message_history = []
        self.max_message_history = model_config.get(
            "max_message_history", 5
        )  # Number of past turns to keep

        # For game summary storage
        self.summary = ""  # Store the latest game summary from model response
        self.turn_count = 0

        # For frame storage and comparison
        self.enable_cache = model_config.get("enable_cache", True)
        self.cache_dir = Path(model_config.get("cache_dir", "cache"))
        self.similarity_threshold = model_config.get("similarity_threshold", 0.95)
        self.last_frame = None
        self.last_frame_hash = None

        # For debugging and testing
        self._last_raw_response = None  # Store the raw response for debugging

        # Create cache directory if it doesn't exist
        if self.enable_cache and not self.cache_dir.exists():
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created cache directory: {self.cache_dir}")

        logger.info(f"LLM Agent initialized with provider: {self.provider}")
        if self.provider == "local":
            logger.info(f"Local backend: {self.backend}")
        logger.info(f"API URL: {self.api_url}")
        logger.info(f"Valid actions: {len(valid_actions)} possible actions")
        logger.info(f"Message history: keeping last {self.max_message_history} interactions")
        logger.info(f"Game summary storage is {'enabled' if use_summary else 'disabled'}")
        logger.info(f"Frame saving is {'enabled' if self.enable_cache else 'disabled'}")
        logger.info(
            f"JSON schema support is {'enabled' if model_config.get('json_schema_support', True) else 'disabled'}"
        )

    def _maybe_start_server(self):
        """
        Start an integrated model server if configured.
        For external API providers like OpenAI, Claude, or Mistral, this is skipped.
        """
        # Skip server startup for external providers
        if self.provider != "local":
            logger.info(f"Using external provider {self.provider}, skipping local server startup")
            return

        # Check if autostart is enabled
        autostart = self.model_config.get("autostart_server", False)
        if not autostart:
            logger.info("Autostart disabled, skipping server startup")
            return

        # Start the appropriate server based on backend
        if self.backend == "llama.cpp":
            # Get model parameters
            model_path = self.model_config.get("model_path")
            if not model_path:
                logger.error(
                    "model_path must be specified when using llama.cpp backend with autostart"
                )
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
                host_part = self.api_url.split("://")[1].split(":")[0]
                host = host_part if host_part != "localhost" else "127.0.0.1"
                port = int(self.api_url.split(":")[-1].split("/")[0])
            except (IndexError, ValueError) as e:
                logger.error(f"Failed to parse host/port from API URL: {self.api_url}")
                raise ValueError(f"Invalid API URL format: {self.api_url}") from e

            # Start server with additional configuration options
            logger.info(f"Starting llama.cpp server with model: {model_path}")
            llama_cpp_server.start_server(
                model_path=model_path,
                model_type=self.model_config.get("model_type", "llava"),
                host=host,
                port=port,
                n_gpu_layers=self.model_config.get("n_gpu_layers", -1),
                n_ctx=self.model_config.get("n_ctx", 2048),
                verbose=self.model_config.get("verbose", False),
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
                    raise ConnectionError(
                        f"Could not connect to llama.cpp server at {self.api_url}"
                    )
                time.sleep(1)

        elif self.backend == "vllm":
            # vLLM can't be started programmatically as easily, so we'll just log a message
            if platform.system() == "Darwin":
                logger.warning(
                    "vLLM is not supported on macOS. Switching to llama.cpp backend is recommended."
                )
            logger.info("vLLM server autostart not implemented. Please use ./start_vllm_server.sh")

    def decide_action(self, frame: Image.Image) -> str:
        """
        Analyze the current game frame and decide on the next action.

        Args:
            frame: PIL Image of the current game frame

        Returns:
            str: The agent's decision as text, or None for no action
        """
        # Check cache first if enabled
        if self.enable_cache:
            # Check if this frame is very similar to the last one
            if self.last_frame is not None:
                similarity = self._calculate_frame_similarity(frame, self.last_frame)
                if similarity > self.similarity_threshold:
                    logger.debug(
                        f"Frame is similar to previous frame (similarity: {similarity:.4f})"
                    )
                    # We've removed the cached action feature as it was causing more trouble than it's worth

            # Calculate frame hash for caching
            frame_hash = self._calculate_frame_hash(frame)

            # Save for next frame comparison
            self.last_frame = frame.copy()
            self.last_frame_hash = frame_hash

            # We've removed the cached action feature as it was causing more trouble than it's worth

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
        if response and (response.strip().startswith("{") and response.strip().endswith("}")):
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

        # Update message history with this action and timestamp
        frame_number = self.turn_count
        self.message_history.insert(0, (valid_action, frame_number))
        # Trim history to max length
        while len(self.message_history) > self.max_message_history:
            self.message_history.pop()

        # Extract the game summary if available in the response and JSON format
        try:
            if response and response.strip().startswith("{"):
                json_data = json.loads(response)

                # Store the game summary if available
                if "game_summary" in json_data:
                    self.summary = json_data["game_summary"]
                    logger.info(f"Updated game summary: {self.summary[:100]}...")
        except (json.JSONDecodeError, KeyError):
            # Ignore any JSON parsing errors here
            pass

        # Increment turn counter
        self.turn_count += 1

        # Save the frame to disk for future analysis if needed
        if self.enable_cache and self.last_frame_hash is not None:
            self._save_frame_to_cache(frame, self.last_frame_hash)

        return valid_action

    def _get_game_type(self) -> str:
        """
        Get the current game type from the model config.
        This is used to load appropriate game-specific prompts.

        Returns:
            str: The game type ID (e.g., "pokemon", "zelda", etc.) or empty string if not set
        """
        # Check if the model config contains a game_type field
        return self.model_config.get("game_type", "")

    def parse_action(self, action_text: str) -> str:
        """
        Parse the model's response into a valid action.

        Args:
            action_text: Text response from the model

        Returns:
            str: A valid action, None for no action, or empty string if parsing failed
        """
        # First, try to parse the response as JSON
        try:
            # Check if the response is a valid JSON
            if action_text and (
                action_text.strip().startswith("{") and action_text.strip().endswith("}")
            ):
                response_json = json.loads(action_text)

                # Check if the JSON has the expected structure
                if "action" in response_json:
                    chosen_action = response_json["action"]

                    # Log reasoning first (for all action types)
                    if "reasoning" in response_json:
                        logger.info(f"Agent reasoning: {response_json['reasoning']}")
                    else:
                        logger.warning("No reasoning provided in JSON response")

                    # Store the game summary if available and enabled
                    if "game_summary" in response_json and self.use_summary:
                        game_summary = response_json["game_summary"]
                        logger.info(f"Game summary from agent: {game_summary[:100]}...")
                        self.summary = game_summary

                    # If the action is in our valid actions list, return it
                    if chosen_action in self.valid_actions:
                        logger.info(f"Parsed valid action from JSON: {chosen_action}")
                        return chosen_action
                    # Handle "None" action specifically
                    elif chosen_action == "None":
                        logger.info("Agent chose to do nothing (None action)")
                        # Return None to indicate no action should be taken
                        return None
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            # Continue with text-based parsing if JSON parsing fails

        # Handle empty responses - no fallback
        if not action_text or action_text.strip() == "":
            logger.warning("Received empty response from model, taking no action")
            return None

        # Convert to lowercase for case-insensitive matching
        text = action_text.lower()

        # Try direct matching first (with normalization)
        for valid_action in self.valid_actions:
            # Check for exact match
            if valid_action.lower() == text:
                return valid_action

            # Check for action within text
            action_pattern = rf"\b{re.escape(valid_action.lower())}\b"
            if re.search(action_pattern, text):
                return valid_action

        # Try more flexible matching with context
        context_patterns = [
            (r"press\s+(\w+)", 1),  # "press A" -> "A"
            (r"push\s+(\w+)", 1),  # "push B" -> "B"
            (r"move\s+(up|down|left|right)", 1),  # "move up" -> "up"
            (r"go\s+(up|down|left|right)", 1),  # "go left" -> "left"
            (r"select\s+(\w+)", 1),  # "select start" -> "start"
            (r"button\s+(\w+)", 1),  # "button A" -> "A"
        ]

        for pattern, group in context_patterns:
            match = re.search(pattern, text)
            if match:
                action_candidate = match.group(group).capitalize()
                # Verify it's in our valid actions list
                if action_candidate in self.valid_actions:
                    return action_candidate
                # Special case for directional inputs
                if action_candidate.lower() in ["up", "down", "left", "right"]:
                    capitalized = action_candidate.capitalize()
                    if capitalized in self.valid_actions:
                        return capitalized

        # No default action - return None if we can't determine an action
        logger.warning(f"Could not parse a valid action from: '{action_text}', taking no action")
        return None

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
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return img_str

    def _construct_prompt(self, image_data: str, game_type: str = "") -> Dict[str, Any]:
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
        valid_actions_with_none = ", ".join(self.valid_actions + ["None"])

        # Create JSON schema for response validation
        action_enum = self.valid_actions.copy()
        action_enum.append("None")  # Add None as a valid action

        json_schema = {
            "type": "object",
            "properties": {
                "reasoning": {
                    "type": "string",
                    "description": "Detailed explanation of why this action was chosen based on the game state with visual evidence",
                },
                "action": {
                    "type": "string",
                    "enum": action_enum,
                    "description": f"The selected action from the list: {action_list} or None to do nothing",
                },
                "game_summary": {
                    "type": "string",
                    "description": "A concise summary of the current game state and progress",
                },
            },
            "required": ["action", "reasoning", "game_summary"],
            "additionalProperties": False,
        }

        # Get additional prompt pieces from model config
        prompt_additions = self.model_config.get("prompt_additions", [])

        # Get game-specific instructions from the config if available
        game_specific_instructions = ""
        if game_type:
            game_specific_instructions = self.model_config.get("game_specific_instructions", "")

        # Add any custom prompt additions from the config
        custom_instructions = "\n".join(prompt_additions) if prompt_additions else ""

        # Get summary for template if needed
        summary = self.summary if self.use_summary else ""

        # Load reasoning prompt based on game type
        reasoning_prompt = ""
        if game_type:
            try:
                reasoning_template = self.jinja_env.get_template("reasoning_prompt.j2")
                reasoning_prompt = reasoning_template.render(game_type=game_type)
            except Exception as e:
                logger.warning(f"Failed to load reasoning prompt template: {e}")

        # Check if we have a custom system message (for testing)
        if self.custom_system_message:
            system_message = self.custom_system_message
        else:
            # Render the system message from the template
            template = self.jinja_env.get_template("system_prompt.j2")
            # Check if there's a game-specific JSON example
            example_json = (
                self.model_config.get("games", {}).get(game_type, {}).get("example_json", "")
            )

            system_message = template.render(
                action_list=action_list,
                valid_actions_with_none=valid_actions_with_none,
                game_specific_instructions=game_specific_instructions,
                custom_instructions=custom_instructions,
                reasoning_prompt=reasoning_prompt,
                backend=self.backend,
                summary=summary,
                example_json=example_json,
            )

        # Prepare previous actions for the user message template
        previous_actions = []
        if self.message_history:
            # Extract the last few actions from message history
            for i, (action, timestamp) in enumerate(self.message_history):
                if i >= self.max_message_history:
                    break
                previous_actions.append((action, timestamp))

        # Current frame number and game time
        frame_number = self.turn_count
        game_time = time.strftime("%H:%M:%S", time.localtime())

        # Render the user message from template
        try:
            user_template = self.jinja_env.get_template("user_message.j2")
            user_message = user_template.render(
                frame_number=frame_number, game_time=game_time, previous_actions=previous_actions
            )
        except Exception as e:
            logger.warning(f"Failed to load user message template: {e}")
            # Fallback to basic user message
            user_message = "What action should I take in this game? Choose one of the available actions or 'None' to do nothing. Remember to always provide detailed reasoning for your choice with specific visual evidence from the screen."

        # First, prepare the message history we want to include between the system message and final user message
        history_messages = []

        # Process message history - make sure to redact image data
        if self.message_history:
            for i, (action, frame_num) in enumerate(self.message_history):
                if frame_num >= 0:  # Ensure it's a valid frame number
                    # Create a history message - assistant's response from previous turns
                    history_messages.append({"role": "assistant", "content": f"Action: {action}"})

                    # Add a simple acknowledgment from user to maintain the conversation flow
                    history_messages.append({"role": "user", "content": "What should I do next?"})

        # Construct the prompt based on the provider and backend
        if self.provider == "openai":
            # OpenAI GPT-4o format
            messages = [{"role": "system", "content": system_message}]

            # Add history messages between system and current user message
            messages.extend(history_messages)

            # Add the current user message with image
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_message},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_data}"},
                        },
                    ],
                }
            )
        elif self.provider == "anthropic":
            # For Anthropic, we handle the system message as a separate parameter later
            # Start with history messages if any
            messages = []

            # Add history messages (without the system message)
            messages.extend(history_messages)

            # Add the current user message with image
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_message},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_data,
                            },
                        },
                    ],
                }
            )

            # Add an assistant message with pre-filled JSON to guide the response format
            messages.append({"role": "assistant", "content": '{"reasoning": "'})

            # We'll add system as a top-level parameter later after params is initialized
        elif self.provider == "mistral":
            # Mistral Pixtral format (similar to OpenAI format)
            messages = [{"role": "system", "content": system_message}]

            # Add history messages between system and current user message
            messages.extend(history_messages)

            # Add the current user message with image
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_message},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_data}"},
                        },
                    ],
                }
            )
        elif self.provider == "local":
            # Local backends (llama.cpp or vLLM)
            if self.backend == "llama.cpp":
                # For llama.cpp, format based on OpenAI Vision API
                messages = [{"role": "system", "content": system_message}]

                # Add history messages between system and current user message
                messages.extend(history_messages)

                # Add the current user message with image
                messages.append(
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_message},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{image_data}"},
                            },
                        ],
                    }
                )
            else:
                # For vLLM, use the standard format
                messages = [{"role": "system", "content": system_message}]

                # Add history messages between system and current user message
                messages.extend(history_messages)

                # Add the current user message with image
                messages.append(
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_message},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{image_data}"},
                            },
                        ],
                    }
                )
        else:
            # Custom OpenAI API-compatible server format (default to OpenAI format)
            messages = [{"role": "system", "content": system_message}]

            # Add history messages between system and current user message
            messages.extend(history_messages)

            # Add the current user message with image
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_message},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_data}"},
                        },
                    ],
                }
            )

        # Set base model parameters
        params = {
            "messages": messages,
            "max_tokens": self.model_config.get("max_tokens", 200),  # Increased for JSON response
            "temperature": self.model_config.get(
                "temperature", 0.2
            ),  # Lower temperature for more focused responses
            "stream": False,
        }

        # Handle Anthropic's special system parameter requirement
        if self.provider == "anthropic":
            # For Anthropic, the system message goes as a top-level parameter, not in the messages array
            params["system"] = system_message

        # Add model name for external APIs and vLLM if specified
        if self.model_name:
            if self.provider != "local" or (self.provider == "local" and self.backend == "vllm"):
                params["model"] = self.model_name

        # Add response format if JSON schema is supported
        if self.model_config.get("json_schema_support", True):
            if self.provider == "anthropic":
                # For Anthropic API, format is now specified differently in the API
                # Using a different approach: add a format instruction to the system prompt
                original_system = params.get("system", "")
                format_instruction = '\n\nYou must respond with valid JSON in this format: {"reasoning": "...", "action": "...", "game_summary": "..."}'
                params["system"] = original_system + format_instruction
            elif self.provider == "openai":
                # OpenAI supports json_schema format
                params["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "game_action",
                        "schema": json_schema,
                        "strict": True,
                    },
                }
                logger.debug("Using JSON schema format with OpenAI")
            elif self.provider == "mistral":
                # Mistral currently supports json_object type
                params["response_format"] = {"type": "json_object"}
            elif self.provider == "local":
                if self.backend == "llama.cpp":
                    # Check if we're using the built-in llama.cpp server module
                    is_builtin_server = bool(self.model_config.get("autostart_server", False))

                    # For built-in server (llama-cpp-python), always use json_object
                    if is_builtin_server:
                        params["response_format"] = {"type": "json_object"}
                        logger.debug(
                            "Using json_object response format with built-in llama.cpp server"
                        )
                    else:
                        # For external llama.cpp binary, use schema format if enabled
                        try_schema = self.model_config.get("try_json_schema", True)
                        if try_schema:
                            params["response_format"] = {
                                # "type": "json_schema",
                                # "schema": json_schema,
                                "type": "json_schema",
                                "json_schema": {
                                    "name": "game_action",
                                    "schema": json_schema,
                                    "strict": True,
                                },
                            }
                            logger.debug(
                                "Trying JSON schema response format with external llama.cpp"
                            )
                        else:
                            params["response_format"] = {"type": "json_object"}
                else:
                    # For vLLM, use json_object format instead of json_schema
                    # vLLM has issues with json_schema currently
                    params["response_format"] = {"type": "json_object"}
            else:
                # Default for other providers (custom OpenAI API-compatible)
                # Try schema first, since most modern implementations support it
                params["response_format"] = {"type": "json_schema", "schema": json_schema}

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

            # Check if the provider supports JSON response format
            supports_json_response = True

            # Some providers/models may not support response_format at all
            if self.model_config.get("json_schema_support", True) is False:
                # Remove the response_format from the prompt if not supported
                if "response_format" in prompt:
                    logger.warning(
                        "JSON response format not supported by this provider, removing response_format"
                    )
                    prompt.pop("response_format")
                    supports_json_response = False

            # Prepare headers
            headers = {"Content-Type": "application/json"}

            # Add API key and organization ID for external providers if provided
            if self.provider in ["openai", "anthropic", "mistral"] and self.api_key:
                if self.provider == "openai":
                    headers["Authorization"] = f"Bearer {self.api_key}"
                    if self.organization_id:
                        headers["OpenAI-Organization"] = self.organization_id
                elif self.provider == "anthropic":
                    headers["x-api-key"] = self.api_key
                    headers["anthropic-version"] = (
                        "2023-06-01"  # Use appropriate Anthropic API version
                    )
                elif self.provider == "mistral":
                    headers["Authorization"] = f"Bearer {self.api_key}"

            # Determine the endpoint based on the provider
            if self.provider == "anthropic":
                endpoint = f"{self.api_url}/v1/messages"
            else:
                # OpenAI, Mistral, and OpenAI-compatible APIs use the same endpoint
                endpoint = f"{self.api_url}/v1/chat/completions"

            # Log request info
            provider_info = f"{self.provider}"
            if self.provider == "local":
                provider_info += f" with {self.backend} backend"

            logger.debug(f"Sending request to {provider_info} at {endpoint}")
            logger.debug(f"Request payload: {json.dumps(prompt)}")

            # Send the request to the appropriate endpoint
            response = requests.post(
                endpoint,
                json=prompt,
                headers=headers,
                timeout=60,  # Models with vision can take longer, especially first requests
            )

            elapsed_time = time.time() - start_time
            logger.info(f"Model API call took {elapsed_time:.2f} seconds")

            if response.status_code != 200:
                logger.error(f"API error: {response.status_code} - {response.text}")
                # Provide more detailed error with provider info
                return f"Error {response.status_code} from {provider_info}"

            result = response.json()

            # Extract the text content from the API response based on provider format
            try:
                if self.provider == "anthropic":
                    # Claude API response format
                    text_response = result["content"][0]["text"]
                else:
                    # OpenAI, Mistral, and compatible API response format
                    text_response = result["choices"][0]["message"]["content"]

                # Store the raw response for debugging and testing
                self._last_raw_response = text_response

                # Check for JSON format response (if we're using JSON response format)
                if supports_json_response:
                    try:
                        # If the response starts with { it's likely a JSON
                        if text_response.strip().startswith("{"):
                            # Sometimes the model generates invalid JSON with extra tokens at the end
                            # Find the last valid closing brace
                            json_str = text_response.strip()

                            # Log the raw JSON for debugging
                            logger.debug(f"Raw JSON response: {json_str[:200]}...")

                            # First try: Look for a complete JSON object
                            try:
                                # Try to find a valid JSON object by looking for matching brackets
                                brace_count = 0
                                for i, char in enumerate(json_str):
                                    if char == "{":
                                        brace_count += 1
                                    elif char == "}":
                                        brace_count -= 1
                                        if brace_count == 0:
                                            # We found a complete JSON object
                                            json_str = json_str[: i + 1]
                                            break

                                # Now try to parse the cleaned JSON
                                logger.debug(f"Attempting to parse JSON: {json_str[:200]}...")
                                json_data = json.loads(json_str)
                            except json.JSONDecodeError:
                                # Second try: Look for a partial JSON with just the action key
                                logger.warning(
                                    "Failed first JSON parse attempt, trying to extract partial JSON"
                                )
                                # Try to directly extract an action field
                                full_text = json_str

                                # Try to find the action field
                                action_match = re.search(
                                    r'"action"\s*:\s*"([^"]+)"', full_text, re.IGNORECASE
                                )
                                if not action_match:
                                    # Also try with single quotes
                                    action_match = re.search(
                                        r'"action"\s*:\s*\'([^\']+)\'', full_text, re.IGNORECASE
                                    )

                                if not action_match:
                                    # Try capitalized version
                                    action_match = re.search(
                                        r'"Action"\s*:\s*"([^"]+)"', full_text, re.IGNORECASE
                                    )

                                # Direct check for action terms
                                if not action_match:
                                    # Look for any of our valid actions surrounded by quotes
                                    actions_pattern = "|".join(self.valid_actions + ["None"])
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
                            if "action" in json_data:
                                chosen_action = json_data["action"]
                            elif "Action" in json_data:  # Try different capitalization
                                chosen_action = json_data["Action"]
                            else:
                                # Try finding something that looks like an action, allowing for the most flexibility
                                for key, value in json_data.items():
                                    if isinstance(value, str) and (
                                        value in self.valid_actions or value == "None"
                                    ):
                                        logger.info(
                                            f"Found action key '{key}' with valid value: {value}"
                                        )
                                        chosen_action = value
                                        break
                                else:
                                    chosen_action = None

                            # Log reasoning if available - do this for ALL actions
                            if "reasoning" in json_data:
                                logger.info(f"Agent reasoning: {json_data['reasoning']}")
                            elif "Reasoning" in json_data:
                                logger.info(f"Agent reasoning: {json_data['Reasoning']}")
                            else:
                                logger.warning("No reasoning provided in JSON response")

                            # Log game summary if available
                            if "game_summary" in json_data:
                                logger.info(f"Game summary: {json_data['game_summary']}")
                            elif "Game_summary" in json_data or "game_state" in json_data:
                                summary_key = (
                                    "Game_summary" if "Game_summary" in json_data else "game_state"
                                )
                                logger.info(f"Game summary: {json_data[summary_key]}")

                            # If it's a valid action, return it directly
                            if chosen_action in self.valid_actions:
                                logger.info(f"Valid JSON action response: {chosen_action}")
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
                    action_pattern = rf"\b{re.escape(action.lower())}\b"
                    if re.search(action_pattern, clean_response.lower()):
                        return action

                return clean_response
            except (KeyError, IndexError) as e:
                logger.error(f"Failed to parse API response: {e}")
                logger.debug(f"Response: {result}")

                # Different error handling based on provider
                if self.provider == "anthropic" and "content" not in result:
                    logger.warning(
                        "Response missing 'content' field, Claude API may be incompatible"
                    )
                elif "choices" not in result:
                    logger.warning("Response missing 'choices' field, API may be incompatible")

                return "Error parsing response"

        except requests.RequestException as e:
            logger.error(f"Request to model API failed: {e}")

            # Provide helpful error messages based on the error type
            if "Connection refused" in str(e):
                if self.provider == "local":
                    logger.error(
                        f"Connection refused. Please ensure the {self.backend} server is running at {self.api_url}"
                    )
                else:
                    logger.error(f"Connection refused to {self.provider} API at {self.api_url}")
            elif "timed out" in str(e):
                logger.error(
                    f"Request timed out. The {self.provider} API might be overloaded or processing a large request"
                )
            elif "unauthorized" in str(e).lower() or "401" in str(e):
                logger.error(f"Authorization failed. Please check your API key for {self.provider}")

            return "Error connecting to model server"

    # Summary generation from history has been removed.
    # We now only use the game_summary from the model's JSON response.

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
        diff = ImageChops.difference(frame1.convert("RGB"), frame2.convert("RGB"))

        # Get statistics
        stat = diff.convert("L").getdata()
        diff_sum = sum(stat)
        max_diff = 255 * len(stat)

        # Calculate similarity (inverted difference)
        if max_diff == 0:
            return 1.0
        return 1.0 - (diff_sum / max_diff)

    def _save_frame_to_cache(self, frame: Image.Image, frame_hash: str) -> None:
        """
        Save a frame to the cache directory for later analysis.

        Args:
            frame: The PIL Image to save
            frame_hash: The frame's hash
        """
        if not self.enable_cache:
            return

        # Use frame hash as part of the filename
        action = "Unknown"

        # Only save a subset of frames to avoid filling up the disk
        # Save 1 in every 10 frames, or if it's an important action
        important_actions = ["A", "Start", "Select"]

        # Use turn_count attribute if it exists, otherwise default to 0
        turn_count = getattr(self, "turn_count", 0)
        should_save = (turn_count % 10 == 0) or any(a in action for a in important_actions)

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
        Clear the frame comparison cache.
        """
        self.last_frame = None
        self.last_frame_hash = None
        logger.info("Frame comparison cache cleared")
