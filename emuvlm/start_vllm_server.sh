#!/bin/bash
# Start the vLLM server with Qwen2.5-VL-3B model

# Set the model ID
MODEL_ID="Qwen/Qwen2.5-VL-3B-Instruct"

# Start vLLM server with OpenAI-compatible API
python -m vllm.entrypoints.openai.api_server \
    --model $MODEL_ID \
    --host 0.0.0.0 \
    --port 8000 \
    --tensor-parallel-size 1