#!/bin/bash
# Test macOS compatibility features of EmuVLM
# This script verifies that the llama.cpp backend works properly on macOS

set -e  # Exit on any error

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "This script is intended to be run on macOS only."
    echo "Current OS: $OSTYPE"
    exit 1
fi

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Testing EmuVLM macOS Compatibility ===${NC}"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to run a test and report results
run_test() {
    local test_name="$1"
    local command="$2"
    
    echo -e "\n${YELLOW}Testing: ${test_name}${NC}"
    if eval "$command"; then
        echo -e "${GREEN}✓ PASSED: ${test_name}${NC}"
        return 0
    else
        echo -e "${RED}✗ FAILED: ${test_name}${NC}"
        return 1
    fi
}

# Step 1: Check if Metal is available
echo -e "\n${YELLOW}Checking for Metal GPU support...${NC}"
if system_profiler SPMetalDataType | grep -q "Metal Support"; then
    echo -e "${GREEN}✓ Metal is supported on this Mac${NC}"
else
    echo -e "${YELLOW}⚠ Metal might not be fully supported on this Mac${NC}"
    echo "This may affect performance, but EmuVLM should still work."
fi

# Step 2: Check for required dependencies
echo -e "\n${YELLOW}Checking for required dependencies...${NC}"
MISSING_DEPS=0

# Check Python version
PYTHON_VERSION=$(python3 --version | cut -d ' ' -f 2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [[ $PYTHON_MAJOR -ge 3 && $PYTHON_MINOR -ge 8 ]]; then
    echo -e "${GREEN}✓ Python version $PYTHON_VERSION is compatible${NC}"
else
    echo -e "${RED}✗ Python version $PYTHON_VERSION is too old. EmuVLM requires Python 3.8+${NC}"
    MISSING_DEPS=1
fi

# Check for llama-cpp-python
if pip show llama-cpp-python &>/dev/null; then
    LLAMA_VERSION=$(pip show llama-cpp-python | grep Version | cut -d ' ' -f 2)
    echo -e "${GREEN}✓ llama-cpp-python is installed (version $LLAMA_VERSION)${NC}"
else
    echo -e "${RED}✗ llama-cpp-python is not installed${NC}"
    echo "Install it with: pip install -e \".[macos]\""
    MISSING_DEPS=1
fi

# Check for SDL2 (required for PyBoy)
if brew list sdl2 &>/dev/null; then
    echo -e "${GREEN}✓ SDL2 is installed${NC}"
else
    echo -e "${YELLOW}⚠ SDL2 is not installed${NC}"
    echo "Install it with: brew install sdl2 sdl2_ttf"
    echo "This is required for PyBoy emulator"
fi

# Step 3: Check for model file
echo -e "\n${YELLOW}Checking for LLaVA model file...${NC}"
MODEL_PATH="models/llava-v1.5-7b-Q4_K_S.gguf"
if [ -f "$MODEL_PATH" ]; then
    echo -e "${GREEN}✓ LLaVA model file found at $MODEL_PATH${NC}"
else
    echo -e "${YELLOW}⚠ LLaVA model file not found at $MODEL_PATH${NC}"
    echo "You can download it with: emuvlm-download-model"
fi

# Step 4: Test starting the server
echo -e "\n${YELLOW}Testing llama.cpp server startup (this might take a moment)...${NC}"
if [ -f "$MODEL_PATH" ]; then
    # Start server in the background and capture output
    echo "Starting server..."
    emuvlm-llama-server "$MODEL_PATH" --direct > server_test.log 2>&1 &
    SERVER_PID=$!
    
    # Wait for server to start (up to 30 seconds)
    MAX_WAIT=30
    for i in $(seq 1 $MAX_WAIT); do
        if curl -s http://localhost:8000/v1/models &>/dev/null; then
            echo -e "${GREEN}✓ Server started successfully${NC}"
            # Kill the server
            kill $SERVER_PID
            wait $SERVER_PID 2>/dev/null || true
            break
        fi
        
        if ! ps -p $SERVER_PID &>/dev/null; then
            echo -e "${RED}✗ Server process died unexpectedly${NC}"
            cat server_test.log
            break
        fi
        
        # Show progress
        if [ $i -eq 10 ]; then
            echo "Still waiting for server to start..."
        fi
        
        sleep 1
        
        if [ $i -eq $MAX_WAIT ]; then
            echo -e "${RED}✗ Server failed to start within $MAX_WAIT seconds${NC}"
            kill $SERVER_PID 2>/dev/null || true
            wait $SERVER_PID 2>/dev/null || true
            cat server_test.log
        fi
    done
    
    # Check if Metal acceleration was detected
    if grep -q "Metal" server_test.log; then
        echo -e "${GREEN}✓ Metal GPU acceleration is enabled${NC}"
    else
        echo -e "${YELLOW}⚠ Metal GPU acceleration was not detected${NC}"
        echo "This might affect performance. Check server_test.log for details."
    fi
    
else
    echo -e "${YELLOW}⚠ Skipping server test as model file is not available${NC}"
fi

# Step 5: Test basic model functionality if server test passed
if [ -f "$MODEL_PATH" ] && [ -f "output/test_images/controller_test.png" ]; then
    echo -e "\n${YELLOW}Testing model inference with a sample image...${NC}"
    if emuvlm-test-llama --model "$MODEL_PATH" --image "output/test_images/controller_test.png" --no-autostart; then
        echo -e "${GREEN}✓ Model inference test passed${NC}"
    else
        echo -e "${RED}✗ Model inference test failed${NC}"
    fi
else
    echo -e "\n${YELLOW}⚠ Skipping model inference test${NC}"
    echo "This test requires the model file and a sample test image"
fi

# Step 6: Summary and cleanup
echo -e "\n${YELLOW}=== Test Summary ===${NC}"
if [ $MISSING_DEPS -eq 1 ]; then
    echo -e "${RED}⚠ Some dependencies are missing. Please install them before using EmuVLM.${NC}"
else
    echo -e "${GREEN}✓ Your system has all the required dependencies for EmuVLM.${NC}"
fi

# Clean up
rm -f server_test.log

echo -e "\n${YELLOW}For more information, see MAC_COMPATIBILITY.md${NC}"