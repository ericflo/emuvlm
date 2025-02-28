#!/bin/bash
# Start the llama.cpp server with LLaVA compatible model
# This provides an OpenAI-compatible API on macOS, where vLLM is not supported

# Process command line arguments
MODEL_PATH="$1"
shift

# Default parameters
HOST="0.0.0.0"
PORT="8000"
N_GPU_LAYERS="-1"
N_CTX=""  # Will be determined automatically

# Process additional arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --host)
      HOST="$2"
      shift 2
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    --n-gpu-layers)
      N_GPU_LAYERS="$2"
      shift 2
      ;;
    --n-ctx)
      N_CTX="$2"
      shift 2
      ;;
    *)
      # Unknown option
      echo "Warning: Unknown option $1"
      shift
      ;;
  esac
done

# Check if model exists
if [ ! -f "$MODEL_PATH" ]; then
    echo "Error: Model file not found at $MODEL_PATH"
    echo "Usage: $0 <path/to/model.gguf> [--host HOST] [--port PORT] [--n-gpu-layers LAYERS] [--n-ctx CTX]"
    exit 1
fi

# Start the server
echo "Starting llama.cpp server with model: $MODEL_PATH"
echo "Using Llava-v1.5-7B GGUF model for vision-language tasks"

# Enable GPU acceleration based on platform
if [[ "$(uname)" == "Darwin" ]]; then
    # macOS - use Metal
    export LLAMA_METAL=1
    echo "Enabling Metal acceleration for macOS"
elif [[ "$(uname)" == "Linux" && -e "/dev/nvidia0" ]]; then
    # Linux with NVIDIA GPU
    export LLAMA_CUBLAS=1
    echo "Enabling CUDA acceleration for Linux"
fi

# Check file exists and is readable
if [ ! -r "$MODEL_PATH" ]; then
    echo "Error: Model file not found or not readable: $MODEL_PATH"
    exit 1
fi

# Determine available memory and adjust context size if needed
if [[ "$(uname)" == "Darwin" ]]; then
    # Get macOS memory in GB
    TOTAL_MEM=$(sysctl hw.memsize | awk '{print int($2/1024/1024/1024)}')
else
    # Get Linux memory in GB
    TOTAL_MEM=$(free -g | grep Mem | awk '{print $2}')
fi

# Adjust context size based on available memory and model size
MODEL_SIZE=$(du -h "$MODEL_PATH" | cut -f1)
echo "Available memory: ${TOTAL_MEM}GB, Model size: ${MODEL_SIZE}"

CTX_SIZE=4096  # Default
if [ "$TOTAL_MEM" -lt 8 ]; then
    CTX_SIZE=2048
    echo "Limited memory detected, reducing context size to $CTX_SIZE"
elif [ "$TOTAL_MEM" -gt 32 ]; then
    CTX_SIZE=8192
    echo "Large memory detected, increasing context size to $CTX_SIZE"
fi

# Use provided context size if specified
if [ -n "$N_CTX" ]; then
    CTX_SIZE="$N_CTX"
    echo "Using specified context size: $CTX_SIZE"
fi

# Start the server using the built-in server module with optimized parameters
echo "Starting llama.cpp server with:"
echo "  - Model: $MODEL_PATH"
echo "  - Host: $HOST"
echo "  - Port: $PORT"
echo "  - Context size: $CTX_SIZE"
echo "  - GPU layers: $N_GPU_LAYERS"

# Use Python from the virtual environment if it exists
if [ -f "../venv/bin/python" ]; then
    PYTHON="../venv/bin/python"
elif [ -f "./venv/bin/python" ]; then
    PYTHON="./venv/bin/python"
else
    PYTHON="python"
fi

# Check if we need to download the mmproj file for Qwen2-VL
MMPROJ_PATH="models/mmproj-Qwen2-VL-7B-Instruct-f32.gguf"
if [[ ! -f "$MMPROJ_PATH" ]]; then
    echo "Multimodal projector file not found, will attempt to download it automatically"
    
    # URL for the mmproj file
    MMPROJ_URL="https://huggingface.co/bartowski/Qwen2-VL-7B-Instruct-GGUF/resolve/main/mmproj-Qwen2-VL-7B-Instruct-f32.gguf"
    
    # Download the file if curl is available
    if command -v curl &> /dev/null; then
        echo "Downloading mmproj file with curl..."
        mkdir -p "$(dirname "$MMPROJ_PATH")"
        curl -L -o "$MMPROJ_PATH" "$MMPROJ_URL"
        if [ $? -eq 0 ]; then
            echo "Successfully downloaded multimodal projector file"
        else
            echo "Failed to download multimodal projector file"
            echo "The Python module will attempt to download it automatically"
        fi
    else
        echo "curl not found, the Python module will handle downloading"
    fi
fi

# Check if this is a Qwen2-VL model
if [[ "$MODEL_PATH" == *"qwen"* ]] || [[ "$MODEL_PATH" == *"Qwen"* ]] || [[ "$MODEL_PATH" == *"vl"* ]] || [[ "$MODEL_PATH" == *"VL"* ]]; then
    echo "Detected Qwen2-VL model, enabling multimodal support"
    if [[ -f "$MMPROJ_PATH" ]]; then
        "$PYTHON" -m llama_cpp.server \
            --model "$MODEL_PATH" \
            --host "$HOST" \
            --port "$PORT" \
            --n_gpu_layers "$N_GPU_LAYERS" \
            --n_ctx "$CTX_SIZE" \
            --n_batch 512 \
            --chat_format chatml \
            --temperature 0.2 \
            --top_p 0.9 \
            --mmproj "$MMPROJ_PATH" \
            --cache-type "prefix" \
            --cache-size 2048
    else
        echo "Warning: Multimodal projector file not found at $MMPROJ_PATH"
        echo "Will try to download it automatically, but if this fails,"
        echo "you can manually download it from:"
        echo "https://huggingface.co/bartowski/Qwen2-VL-7B-Instruct-GGUF/resolve/main/mmproj-Qwen2-VL-7B-Instruct-f32.gguf"
        
        # Run without the mmproj file - our Python module will handle downloading
        "$PYTHON" -m llama_cpp.server \
            --model "$MODEL_PATH" \
            --host "$HOST" \
            --port "$PORT" \
            --n_gpu_layers "$N_GPU_LAYERS" \
            --n_ctx "$CTX_SIZE" \
            --n_batch 512 \
            --chat_format chatml \
            --temperature 0.2 \
            --top_p 0.9 \
            --cache-type "prefix" \
            --cache-size 2048
    fi
else
    # Standard model without multimodal
    "$PYTHON" -m llama_cpp.server \
        --model "$MODEL_PATH" \
        --host "$HOST" \
        --port "$PORT" \
        --n_gpu_layers "$N_GPU_LAYERS" \
        --n_ctx "$CTX_SIZE" \
        --n_batch 512 \
        --chat_format chatml \
        --temperature 0.2 \
        --top_p 0.9 \
        --cache-type "prefix" \
        --cache-size 2048
fi