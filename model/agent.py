"""
LLM agent for analyzing game frames and deciding on actions.
"""
import base64
import io
import logging
import re
import requests
import time
from PIL import Image
from typing import Dict, List, Optional, Any, Union

logger = logging.getLogger(__name__)

class LLMAgent:
    """
    Uses an LLM with vision capabilities to decide game actions based on screenshots.
    
    Currently supports Qwen2.5-VL-3B-Instruct via a vLLM server.
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
        
        # For summary feature
        self.history = []
        self.summary = ""
        self.summary_interval = model_config.get('summary_interval', 10)  # Summarize every X turns
        self.turn_count = 0
        
        logger.info(f"LLM Agent initialized with {len(valid_actions)} possible actions")
        logger.info(f"Summary feature is {'enabled' if use_summary else 'disabled'}")
    
    def decide_action(self, frame: Image.Image) -> str:
        """
        Analyze the current game frame and decide on the next action.
        
        Args:
            frame: PIL Image of the current game frame
            
        Returns:
            str: The agent's decision as text
        """
        # Prepare the image for the model
        image_data = self._prepare_image(frame)
        
        # Construct the prompt
        prompt = self._construct_prompt(image_data)
        
        # Query the model
        response = self._query_model(prompt)
        
        # Update history if summary feature is enabled
        if self.use_summary:
            self._update_history(frame, response)
            
        return response
    
    def parse_action(self, action_text: str) -> Optional[str]:
        """
        Parse the model's response into a valid action.
        
        Args:
            action_text: Text response from the model
            
        Returns:
            Optional[str]: A valid action or None if parsing failed
        """
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
        
        # If we couldn't match anything, return None
        logger.warning(f"Could not parse a valid action from: '{action_text}'")
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
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
        return img_str
    
    def _construct_prompt(self, image_data: str) -> Dict[str, Any]:
        """
        Construct the prompt for the model, including the image and instructions.
        
        Args:
            image_data: Base64-encoded image string
            
        Returns:
            Dict: Prompt in the format expected by the model API
        """
        # List available actions for the model
        action_list = ", ".join(self.valid_actions)
        
        system_message = f"""You are an AI playing a turn-based video game.
Analyze the game screen and decide the best action to take next.
You can only choose from these actions: {action_list}.
Respond with just the name of the action (e.g., "A" or "Up") without explanation."""
        
        # Include summary if enabled and available
        if self.use_summary and self.summary:
            system_message += f"\n\nHere's a summary of what has happened so far in the game:\n{self.summary}"
        
        # Construct the full prompt according to the API's expected format
        # This format is for vLLM serving Qwen2.5-VL
        messages = [
            {"role": "system", "content": system_message},
            {
                "role": "user", 
                "content": [
                    {"type": "image", "image": f"data:image/png;base64,{image_data}"},
                    {"type": "text", "text": "What action should I take in this game? Choose one of the available actions."}
                ]
            }
        ]
        
        return {
            "messages": messages,
            "max_tokens": 100,
            "temperature": 0.2,  # Lower temperature for more focused responses
        }
    
    def _query_model(self, prompt: Dict[str, Any]) -> str:
        """
        Send the prompt to the model API and get the response.
        
        Args:
            prompt: Complete prompt in the API's expected format
            
        Returns:
            str: Model's text response
        """
        try:
            # Assuming vLLM API with OpenAI-compatible endpoint
            response = requests.post(
                f"{self.api_url}/v1/chat/completions",
                json=prompt,
                headers={"Content-Type": "application/json"},
                timeout=30  # Models with vision can take longer
            )
            
            if response.status_code != 200:
                logger.error(f"API error: {response.status_code} - {response.text}")
                return "Error"
            
            result = response.json()
            # Extract the text content from the API response
            # The exact path depends on the API response format
            try:
                text_response = result["choices"][0]["message"]["content"]
                return text_response.strip()
            except (KeyError, IndexError) as e:
                logger.error(f"Failed to parse API response: {e}")
                logger.debug(f"Response: {result}")
                return "Error parsing response"
                
        except requests.RequestException as e:
            logger.error(f"Request to model API failed: {e}")
            return "Error"
    
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