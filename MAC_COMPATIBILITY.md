# macOS Compatibility with llama.cpp

This document explains how to use EmuVLM on macOS, where vLLM is not supported.

## Overview

EmuVLM now supports two VLM backends:

1. **vLLM with Qwen2.5-VL-3B (Linux)**: The original implementation which requires CUDA.
2. **llama.cpp with LLaVA (macOS, Windows, Linux)**: New implementation that works on any platform, ideal for macOS.

The system automatically selects the appropriate backend based on your platform.

## Requirements for macOS

- Python 3.8+ (3.10+ recommended)
- llama-cpp-python package (installed automatically with `pip install -e ".[macos]"`)
- A LLaVA-compatible GGUF model file
- Metal-compatible GPU (for hardware acceleration)

## Installation on macOS

1. Clone the repository:
```bash
git clone https://github.com/yourusername/emuvlm.git
cd emuvlm
```

2. Install with macOS dependencies:
```bash
pip install -e ".[macos]"
```

3. Download the recommended LLaVA model using the built-in tool:
   ```bash
   emuvlm-download-model
   ```
   
   This will download the [Llava-v1.5-7B-GGUF (Q4_K_S)](https://huggingface.co/second-state/Llava-v1.5-7B-GGUF/blob/main/llava-v1.5-7b-q4_k_s.gguf) model which provides the best balance of size and performance.
   
   Other model options (manual download required):
   - [LLaVA v1.5 7B (higher quality, larger file)](https://huggingface.co/second-state/Llava-v1.5-7B-GGUF/blob/main/llava-v1.5-7b-q8_0.gguf)
   - [LLaVA v1.6 Mistral 7B](https://huggingface.co/mys/ggml_llava-v1.6-mistral-7b/blob/main/ggml-model-Q5_K_M.gguf)
   - [Bakllava 1 7B](https://huggingface.co/mys/ggml_bakllava-1-7b/tree/main)

## Usage on macOS

### Starting the Server

```bash
# After downloading the model with emuvlm-download-model
emuvlm-llama-server
```

### Playing Games

```bash
# The system will automatically use the llama.cpp backend on macOS
emuvlm --game pokemon_blue
```

### Testing the Integration

```bash
# Test if everything is working correctly
./test_mac_compatibility.sh /path/to/llava-v1.5-7b-q4_k_s.gguf

# Test with a specific game frame image
emuvlm-test-llama --model /path/to/llava-v1.5-7b-q4_k_s.gguf --image /path/to/game_frame.png
```

## Configuration

You can configure the llama.cpp backend in `config.yaml`:

```yaml
model:
  # Common settings
  api_url: "http://localhost:8000"
  backend: "auto"                   # "auto", "vllm", or "llama.cpp"
  max_tokens: 200                   # Max tokens to generate for action decision
  temperature: 0.2                  # Lower temperature for more focused responses
  
  # Response format configuration
  json_schema_support: true         # Whether the model supports JSON schema responses
  
  # llama.cpp specific settings 
  autostart_server: false           # Whether to start the server automatically
  model_path: "/path/to/llava-v1.5-7b-q4_k_s.gguf"
  n_gpu_layers: -1                  # -1 means use all GPU layers
  n_ctx: 2048                       # Context window size
```

### JSON Schema Response Format

EmuVLM now supports structured JSON responses from the model using JSON schema validation. This provides several benefits:

1. **Validated Responses**: The model is forced to return a valid action from the predefined list
2. **Reasoning Included**: Each action includes the model's reasoning, making debugging easier
3. **Do Nothing Option**: The model can explicitly choose to do nothing when appropriate

Example JSON response format:

```json
{
  "action": "Up",
  "reasoning": "I need to navigate upward in the menu to select the first option"
}
```

If your LLM doesn't support JSON schema validation, you can disable it by setting:
```yaml
model:
  json_schema_support: false
```

When disabled, the system falls back to the original text-based response parsing.

## Performance Tips

1. For best performance on Apple Silicon, ensure Metal acceleration is enabled:
   ```bash
   export LLAMA_METAL=1
   ```

2. Adjust the n_ctx parameter if you encounter memory issues:
   ```bash
   emuvlm-llama-server /path/to/model.gguf --n-ctx 1024
   ```

3. Use a quantized model (Q4_K_M, Q5_K_M) for better performance.

## Troubleshooting

- **Server fails to start**: Check if the model path is correct and the model is compatible with LLaVA
- **Slow responses**: Try enabling Metal acceleration with `export LLAMA_METAL=1`
- **Out of memory**: Use a smaller model or reduce the context size with `--n-ctx`
- **No valid responses**: Make sure you're using a LLaVA-compatible model for vision tasks

## Models Tested

The following models have been tested with EmuVLM on macOS:

- **Llava-v1.5-7B-GGUF (Q4_K_S)** - **Recommended**: Best balance of speed and quality for game playing
- Llava-v1.5-7B-GGUF (Q8_0) - Higher quality but slower and larger file size
- LLaVA v1.6 Mistral 7B (Q5_K_M) - Good alternative with different base model
- Bakllava 1 7B (Q5_K_M) - Another alternative based on Mistral

## Additional Resources

- [llama.cpp GitHub Repository](https://github.com/ggerganov/llama.cpp)
- [LLaVA GitHub Repository](https://github.com/haotian-liu/LLaVA)
- [Llava-v1.5-7B-GGUF Models](https://huggingface.co/second-state/Llava-v1.5-7B-GGUF)
- [Model Comparison: Q4_K_S vs Q8_0](https://github.com/ggerganov/llama.cpp/blob/master/docs/GGUF.md#quantization-formats)