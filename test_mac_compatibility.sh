#!/bin/bash
# Test script for macOS compatibility with llama.cpp

# Check system
if [[ "$(uname)" != "Darwin" ]]; then
    echo "This script is intended for macOS testing. On Linux, vLLM is recommended."
    echo "You can still proceed if you want to test llama.cpp on Linux."
    read -p "Continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check for llama-cpp-python
if ! python -c "import llama_cpp" &>/dev/null; then
    echo "llama-cpp-python is not installed. Installing now..."
    pip install "llama-cpp-python>=0.2.50"
fi

# Ensure the project is installed in development mode
pip install -e .

# Check if model path is provided or use a default
MODEL_PATH="${1:-/path/to/your/model.gguf}"
if [ "$MODEL_PATH" == "/path/to/your/model.gguf" ]; then
    echo "No model path provided. Please specify the path to a LLaVA GGUF model:"
    echo "./test_mac_compatibility.sh /path/to/your/llava-model.gguf"
    exit 1
fi

# Check if model exists
if [ ! -f "$MODEL_PATH" ]; then
    echo "Model file not found at $MODEL_PATH"
    exit 1
fi

# Check for a test image or use the first one we find in the output directory
TEST_IMAGE="${2:-}"
if [ -z "$TEST_IMAGE" ]; then
    # Find a PNG image file in the output directory
    TEST_IMAGE=$(find output -name "*.png" | head -n 1)
    if [ -z "$TEST_IMAGE" ]; then
        echo "No test image found. Please specify a path to a test image:"
        echo "./test_mac_compatibility.sh $MODEL_PATH /path/to/test_image.png"
        exit 1
    fi
    echo "Using test image: $TEST_IMAGE"
fi

# Test server functionality
echo "Testing llama.cpp server functionality..."
echo "Server will start and run for 10 seconds to verify it works"

# Start server in background with port 8123 (to avoid conflicts)
TEST_PORT=8123
python -m emuvlm.test_llama --model "$MODEL_PATH" --server --port $TEST_PORT &
SERVER_PID=$!

# Wait for server to start (max 30 seconds)
for i in {1..30}; do
    if curl -s "http://localhost:$TEST_PORT/v1/models" >/dev/null; then
        echo "Server started successfully!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "Server failed to start after 30 seconds."
        kill $SERVER_PID 2>/dev/null || true
        exit 1
    fi
    echo "Waiting for server to start... ($i/30)"
    sleep 1
done

# Test server API with a basic health check
if curl -s "http://localhost:$TEST_PORT/health" | grep -q "ok"; then
    echo "Server health check passed"
else
    echo "Warning: Server health check failed, but proceeding anyway"
fi

# Let it run for a few seconds
sleep 10

# Kill the server
kill $SERVER_PID 2>/dev/null || true
echo "Server test completed."

# Wait a moment for server to fully shutdown
sleep 3

# Test image analysis capability with LLM backend
echo "Testing image analysis with llama.cpp backend..."
python -m emuvlm.test_llama --model "$MODEL_PATH" --image "$TEST_IMAGE"

# Verify config integration
echo -e "\nTesting configuration integration...\n"
CONFIG_YAML="${CONFIG_YAML:-/Users/ericflo/Development/emuvlm/emuvlm/config.yaml}"

if [ -f "$CONFIG_YAML" ]; then
    echo "Verifying llama.cpp settings in $CONFIG_YAML"
    if grep -q "backend.*auto\|llama.cpp" "$CONFIG_YAML"; then
        echo "✅ Backend setting found in config.yaml"
    else
        echo "⚠️ Warning: Backend setting may be missing in config.yaml"
    fi
    
    if grep -q "model_path" "$CONFIG_YAML"; then
        echo "✅ model_path setting found in config.yaml"
    else
        echo "⚠️ Warning: model_path setting may be missing in config.yaml"
    fi
else
    echo "⚠️ Warning: Config file not found, skipping config verification"
fi

echo "All tests completed!"
echo ""
echo "To use EmuVLM with llama.cpp backend:"
echo "1. Start the server: emuvlm-llama-server $MODEL_PATH"
echo "2. Run a game: emuvlm --game pokemon_blue"
echo ""
echo "The system will automatically detect you're on macOS and use the llama.cpp backend"