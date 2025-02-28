"""
A server module that provides OpenAI-compatible API endpoints using llama.cpp.
This allows Mac users to run the VLM locally, as vLLM is not supported on macOS.
"""

import os
import sys
import signal
import subprocess
import time
import logging
import json
import atexit
import requests
import platform
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

logger = logging.getLogger(__name__)

# Global to store the subprocess reference
_server_process = None

def download_mmproj_file() -> str:
    """
    Download the LLaVA multimodal projector file if it doesn't exist.
    
    Returns:
        str: Path to the mmproj file
    """
    # Define paths
    model_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    mmproj_dir = model_dir / "models"
    mmproj_file = mmproj_dir / "llava-v1.5-7b-mmproj-f16.gguf"
    
    # Create directory if it doesn't exist
    os.makedirs(mmproj_dir, exist_ok=True)
    
    # Check if the file already exists
    if not mmproj_file.exists():
        logger.info(f"Downloading LLaVA multimodal projector file to {mmproj_file}")
        
        # URL for the mmproj file - updated to correct URL
        mmproj_url = "https://huggingface.co/mys/ggml_llava-v1.5-7b/resolve/main/mmproj-model-f16.gguf"
        
        try:
            # Download the file
            response = requests.get(mmproj_url, stream=True)
            response.raise_for_status()
            
            # Save the file
            with open(mmproj_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            logger.info(f"Successfully downloaded multimodal projector file")
        except Exception as e:
            logger.error(f"Failed to download multimodal projector file: {e}")
            raise
    
    return str(mmproj_file)

def start_server(
    model_path: str,
    host: str = "127.0.0.1", 
    port: int = 8000,
    n_gpu_layers: int = -1,
    n_ctx: int = 2048,
    n_batch: int = 512,
    temperature: float = 0.2,
    top_p: float = 0.9,
    verbose: bool = False,
    multimodal: bool = True
) -> None:
    """
    Start the llama.cpp server with OpenAI API compatibility.
    
    Args:
        model_path: Path to the GGUF model file
        host: Hostname to bind the server to
        port: Port to run the server on
        n_gpu_layers: Number of layers to offload to GPU (-1 for all)
        n_ctx: Context window size
        n_batch: Batch size for prompt processing
        temperature: Temperature for sampling
        top_p: Top p for sampling
        verbose: Enable verbose logging
        multimodal: Use multimodal LLaVA support
    """
    global _server_process
    
    if _server_process is not None:
        logger.warning("Server already running")
        return
    
    # Make sure model file exists
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")
    
    # Set environment variables for hardware acceleration
    if platform.system() == 'Darwin':  # macOS
        os.environ["LLAMA_METAL"] = "1"
        logger.info("Enabling Metal acceleration for macOS")
    elif platform.system() == 'Linux' and os.path.exists('/dev/nvidia0'):
        os.environ["LLAMA_CUBLAS"] = "1"
        logger.info("Enabling CUDA acceleration for Linux")
    
    # Determine if this is a multimodal model by checking filename
    model_name = os.path.basename(model_path).lower()
    is_llava_model = "llava" in model_name or multimodal
    
    # Build command with enhanced options for better performance
    cmd = [
        sys.executable, "-m", "llama_cpp.server",  # Use the built-in server module
        "--model", model_path,
        "--host", host,
        "--port", str(port),
        "--n_gpu_layers", str(n_gpu_layers),
        "--n_ctx", str(n_ctx),
        "--n_batch", str(n_batch),
        "--chat_format", "chatml",
        "--cache_type", "prefix",  # Enable prefix caching for better performance
        "--cache_size", "2048"     # Cache size in number of tokens
    ]
    
    # Add multimodal support for LLaVA models
    if is_llava_model:
        try:
            mmproj_path = download_mmproj_file()
            logger.info(f"Using multimodal projector: {mmproj_path}")
            # Use a new parameter name that the server script supports
            cmd.extend(["--clip_model_path", mmproj_path])
        except Exception as e:
            logger.error(f"Failed to set up multimodal support: {e}")
    
    if verbose:
        cmd.extend(["--verbose", "1"])
    
    logger.info(f"Starting llama.cpp server with command: {' '.join(cmd)}")
    
    try:
        # Start server as subprocess
        _server_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE if not verbose else None,
            stderr=subprocess.STDOUT if not verbose else None,
            text=True
        )
        
        # Register shutdown handler
        atexit.register(stop_server)
        
        # Wait for server to start
        logger.info("Waiting for server to start...")
        server_url = f"http://{host}:{port}/v1/models"
        
        # Try to connect to the server for up to 30 seconds
        for _ in range(30):
            try:
                response = requests.get(server_url)
                if response.status_code == 200:
                    logger.info(f"Server started successfully on {host}:{port}")
                    return
            except requests.RequestException:
                pass
            
            # Check if process is still running
            if _server_process.poll() is not None:
                # Process exited
                stdout, stderr = _server_process.communicate()
                error_msg = f"Server process exited unexpectedly with code {_server_process.returncode}"
                if stdout:
                    error_msg += f"\nStdout: {stdout}"
                if stderr:
                    error_msg += f"\nStderr: {stderr}"
                _server_process = None
                raise RuntimeError(error_msg)
                
            time.sleep(1)
            
        # If we get here, server didn't start
        stop_server()
        raise TimeoutError("Server startup timed out after 30 seconds")
        
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        if _server_process is not None:
            _server_process.terminate()
            _server_process = None
        raise

def stop_server() -> None:
    """
    Stop the llama.cpp server if it's running.
    """
    global _server_process
    
    if _server_process is None:
        return
    
    logger.info("Stopping llama.cpp server...")
    
    # Unregister the exit handler to avoid recursion
    atexit.unregister(stop_server)
    
    # Send SIGTERM to process
    _server_process.terminate()
    
    try:
        # Wait for up to 5 seconds for graceful shutdown
        _server_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        # Force kill if it doesn't respond to SIGTERM
        logger.warning("Server not responding to SIGTERM, sending SIGKILL")
        _server_process.kill()
        _server_process.wait()
    
    _server_process = None
    logger.info("Server stopped")

def check_server_status(host: str = "127.0.0.1", port: int = 8000) -> bool:
    """
    Check if the server is running and responsive.
    
    Args:
        host: Server hostname
        port: Server port
        
    Returns:
        bool: True if server is running and responsive, False otherwise
    """
    try:
        response = requests.get(f"http://{host}:{port}/v1/models", timeout=2)
        return response.status_code == 200
    except (requests.RequestException, ConnectionError):
        return False