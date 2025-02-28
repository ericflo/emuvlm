"""
Constants used throughout the emuvlm package.
"""

# Vision-language model paths and URLs
MODEL_PATHS = {
    "llava": "models/llava-v1.5-7b-Q4_K_S.gguf",
    "qwen": "models/Qwen2-VL-7B-Instruct-Q4_K_M.gguf",
    "minicpm": "models/Model-7.6B-Q4_K_M.gguf",
}

MODEL_URLS = {
    "llava": "https://huggingface.co/second-state/Llava-v1.5-7B-GGUF/resolve/main/llava-v1.5-7b-Q4_K_S.gguf",
    "qwen": "https://huggingface.co/bartowski/Qwen2-VL-7B-Instruct-GGUF/resolve/main/Qwen2-VL-7B-Instruct-Q4_K_M.gguf",
    "minicpm": "https://huggingface.co/openbmb/MiniCPM-o-2_6-gguf/resolve/main/Model-7.6B-Q4_K_M.gguf",
}

MMPROJ_PATHS = {
    "llava": "models/llava-v1.5-7b-mmproj-f16.gguf",
    "qwen": "models/mmproj-Qwen2-VL-7B-Instruct-f32.gguf",
    "minicpm": "models/mmproj-model-f16.gguf",
}

MMPROJ_URLS = {
    "llava": "https://huggingface.co/mys/ggml_llava-v1.5-7b/resolve/main/mmproj-model-f16.gguf",
    "qwen": "https://huggingface.co/bartowski/Qwen2-VL-7B-Instruct-GGUF/resolve/main/mmproj-Qwen2-VL-7B-Instruct-f32.gguf",
    "minicpm": "https://huggingface.co/openbmb/MiniCPM-o-2_6-gguf/resolve/main/mmproj-model-f16.gguf",
}

# Valid model types
VALID_MODEL_TYPES = ["llava", "qwen", "minicpm"]

# Model related settings
MODEL_BACKENDS = ["auto", "vllm", "llama.cpp"]
MODEL_PROVIDERS = ["local", "openai", "anthropic", "mistral", "custom"]
DEFAULT_MAX_TOKENS = 200
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_MESSAGE_HISTORY = 8
DEFAULT_N_CTX = 2048

# Default API URLs and headers
DEFAULT_API_URLS = {
    "openai": "https://api.openai.com",
    "anthropic": "https://api.anthropic.com",
    "mistral": "https://api.mistral.ai",
}

API_ENDPOINTS = {
    "anthropic": "/v1/messages",
    "openai": "/v1/chat/completions",
    "mistral": "/v1/chat/completions",
    "custom": "/v1/chat/completions",
}

# Environment variable names for API keys
API_KEY_ENV_VARS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "mistral": "MISTRAL_API_KEY",
}

# Emulator types and ROM mappings
EMULATOR_TYPES = [
    "pyboy",
    "mgba",
    "fceux",
    "snes9x",
    "genesis_plus_gx",
    "mupen64plus",
    "duckstation",
    "gamegear",
]
ROM_EXTENSIONS = {
    ".gb": "pyboy",
    ".gbc": "pyboy",
    ".gba": "mgba",
    ".nes": "fceux",
    ".sfc": "snes9x",
    ".smc": "snes9x",
    ".md": "genesis_plus_gx",
    ".gen": "genesis_plus_gx",
    ".smd": "genesis_plus_gx",
    ".n64": "mupen64plus",
    ".z64": "mupen64plus",
    ".v64": "mupen64plus",
    ".iso": "duckstation",
    ".bin": "duckstation",
    ".cue": "duckstation",
    ".img": "duckstation",
    ".gg": "gamegear",
}

# Game actions and categorization
DEFAULT_ACTIONS = ["Up", "Down", "Left", "Right", "A", "B", "Start", "Select"]
ACTION_CATEGORIES = {
    "navigation": ["Up", "Down", "Left", "Right"],
    "confirm": ["A"],
    "cancel": ["B"],
    "menu": ["Start"],
    "special": ["Select"],
    "wait": ["None"],
}

# Default timing values
DEFAULT_ACTION_DELAYS = {
    "navigation": 0.3,  # For directional inputs
    "confirm": 0.6,  # For A button
    "cancel": 0.6,  # For B button
    "menu": 0.4,  # For Start button
    "special": 0.4,  # For Select button
    "wait": 0.2,  # For "None" action
}

# File paths and directories
DEFAULT_CACHE_DIR = "output/cache"
DEFAULT_LOG_DIR = "output/logs"
DEFAULT_LOG_FILE = "output/logs/emuvlm.log"
DEFAULT_FRAMES_DIR = "output/logs/frames"
DEFAULT_SESSION_DIR = "output/sessions"
TEMPLATES_DIR = "templates"

# Caching settings
DEFAULT_ENABLE_CACHE = True
DEFAULT_SIMILARITY_THRESHOLD = 0.95
IMPORTANT_ACTIONS_FOR_CACHE = ["A", "Start", "Select"]

# Session settings
DEFAULT_AUTO_SAVE_INTERVAL = 50

# Game types
GAME_TYPES = [
    "pokemon",
    "zelda",
    "metroid",
    "mario",
    "kirby",
    "tetris",
    "castlevania",
    "final_fantasy",
    "mega_man",
]

# JSON related settings
DEFAULT_JSON_SCHEMA_SUPPORT = True
DEFAULT_TRY_JSON_SCHEMA = True
