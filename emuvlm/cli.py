"""
Command-line interface for EmuVLM.
"""
import argparse
import os
import logging
import importlib
import sys
import subprocess
import platform
from emuvlm.utils.download_rom import main as download_rom_main

logger = logging.getLogger(__name__)

def main():
    """Main entry point for the emuvlm command."""
    from emuvlm.play import main as play_main
    play_main()

def demo():
    """Entry point for the emuvlm-demo command."""
    # Import here to avoid circular imports
    demo_spec = importlib.util.find_spec("emuvlm.demo_game")
    if demo_spec is None:
        print("Demo module not found. Make sure the package is installed correctly.")
        sys.exit(1)
    
    from emuvlm.demo_game import main as demo_main
    demo_main()

def monitor():
    """Entry point for the emuvlm-monitor command."""
    # Import here to avoid circular imports
    from emuvlm.monitor import main as monitor_main
    monitor_main()

def test_emulators():
    """Entry point for the emuvlm-test-emulators command."""
    # Import here to avoid circular imports
    from emuvlm.test_emulators import main as test_emulators_main
    test_emulators_main()

def test_model():
    """Entry point for the emuvlm-test-model command."""
    # Import here to avoid circular imports
    from emuvlm.test_model import main as test_model_main
    test_model_main()

def start_vllm_server():
    """Entry point for the emuvlm-vllm-server command."""
    # Check if we're on macOS where vLLM is not supported
    if platform.system() == 'Darwin':
        print("vLLM is not supported on macOS. Please use the llama.cpp server instead with:")
        print("emuvlm-llama-server /path/to/model.gguf")
        sys.exit(1)
    
    # Get the path to the start_vllm_server.sh script
    script_path = os.path.join(os.path.dirname(__file__), "start_vllm_server.sh")
    
    # Make sure the script exists and is executable
    if not os.path.exists(script_path):
        print(f"vLLM server script not found at {script_path}")
        sys.exit(1)
    
    # Make the script executable if it's not already
    if not os.access(script_path, os.X_OK):
        os.chmod(script_path, 0o755)
    
    # Execute the script
    subprocess.run([script_path], check=True)

def start_llama_server():
    """Entry point for the emuvlm-llama-server command."""
    # Parse arguments properly
    parser = argparse.ArgumentParser(description="Start llama.cpp server with Qwen2-VL model")
    parser.add_argument("model_path", nargs='?', help="Path to GGUF model file (optional, will use config.yaml if not provided)")
    parser.add_argument("--host", default="0.0.0.0", help="Host address to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    parser.add_argument("--ctx", type=int, help="Context size (auto-configured by default)")
    parser.add_argument("--gpu-layers", type=int, default=-1, help="Number of layers to run on GPU (-1 for all)")
    parser.add_argument("--direct", action="store_true", help="Run Python server directly instead of using the shell script")
    
    # Parse arguments
    args, unknown_args = parser.parse_known_args()
    
    # Get model path from config if not provided
    model_path = args.model_path
    if not model_path:
        # Load config to get model path
        import yaml
        config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                config_model_path = config.get('model', {}).get('model_path')
                if config_model_path:
                    # Resolve relative path if needed
                    if not os.path.isabs(config_model_path):
                        model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), config_model_path)
                    else:
                        model_path = config_model_path
                    print(f"Using model path from config: {model_path}")
    
    # Check if we have a model path now
    if not model_path:
        print("Error: No model path provided and could not find one in config.yaml")
        print("Please specify a model path or run emuvlm-download-model first")
        parser.print_help()
        sys.exit(1)
        
    # Check if model path exists
    if not os.path.exists(model_path):
        print(f"Error: Model file not found: {model_path}")
        print("Please run emuvlm-download-model to download the default model")
        sys.exit(1)
    
    # If direct mode is requested, run the server directly
    if args.direct:
        # Set environment variables for Metal acceleration on macOS
        if platform.system() == 'Darwin':
            os.environ["LLAMA_METAL"] = "1"
            print("Enabling Metal acceleration for macOS")
            
        # Import after setting environment variables
        try:
            from llama_cpp.server.app import create_app
            from llama_cpp.server.settings import Settings
            import uvicorn
        except ImportError:
            print("Error: Required packages not found. Please install them with:")
            print("pip install -e \".[macos]\"")
            sys.exit(1)
            
        # Create settings
        settings = Settings(
            model=model_path,
            n_gpu_layers=args.gpu_layers,
            n_ctx=args.ctx or 4096,  # Default to 4096 if not specified
            chat_format="chatml"
        )
        
        # Create app
        app = create_app(settings=settings)
        
        # Run the server
        print(f"Starting llama.cpp server with model: {model_path}")
        print(f"Server will be available at http://{args.host}:{args.port}")
        
        try:
            uvicorn.run(app, host=args.host, port=args.port)
        except KeyboardInterrupt:
            print("\nServer stopped by user")
        
    else:
        # Get the path to the start_llama_server.sh script
        script_path = os.path.join(os.path.dirname(__file__), "start_llama_server.sh")
        
        # Make sure the script exists and is executable
        if not os.path.exists(script_path):
            print(f"llama.cpp server script not found at {script_path}")
            sys.exit(1)
        
        # Make the script executable if it's not already
        if not os.access(script_path, os.X_OK):
            os.chmod(script_path, 0o755)
    
        # Additional arguments to pass to the script
        cmd = [script_path, model_path]
        
        # Add any custom parameters
        if args.ctx:
            cmd.extend(["--n-ctx", str(args.ctx)])
        if args.gpu_layers != -1:
            cmd.extend(["--n-gpu-layers", str(args.gpu_layers)])
        if args.host != "0.0.0.0":
            cmd.extend(["--host", args.host])
        if args.port != 8000:
            cmd.extend(["--port", str(args.port)])
        
        # Add any remaining unknown arguments
        if unknown_args:
            cmd.extend(unknown_args)
        
        try:
            # Execute the script with the model path and arguments
            subprocess.run(cmd, check=True)
        except KeyboardInterrupt:
            print("\nServer stopped by user")
        except subprocess.CalledProcessError as e:
            print(f"Error starting server: {e}")
            print("\nTrying direct mode instead...")
            # Recursively call ourselves with direct mode
            sys.argv.append("--direct")
            start_llama_server()
            sys.exit(1)

def test_llama():
    """Entry point for the emuvlm-test-llama command."""
    # Import here to avoid circular imports
    from emuvlm.test_llama import main as test_llama_main
    test_llama_main()
    
def download_rom():
    """Entry point for download_rom utility."""
    download_rom_main()

def download_model():
    """Entry point for downloading the GGUF model."""
    import os
    import sys
    import yaml
    import requests
    from pathlib import Path
    from tqdm import tqdm
    
    # Load config to get model info
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    if not os.path.exists(config_path):
        print(f"Config file not found at {config_path}")
        sys.exit(1)
        
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    model_url = config.get('model', {}).get('model_url')
    model_path = config.get('model', {}).get('model_path')
    
    if not model_url:
        print("No model_url found in config.yaml")
        sys.exit(1)
    
    if not model_path:
        print("No model_path found in config.yaml")
        sys.exit(1)
        
    # Resolve relative path if needed
    if not os.path.isabs(model_path):
        model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), model_path)
    
    model_dir = os.path.dirname(model_path)
    if not os.path.exists(model_dir):
        print(f"Creating model directory: {model_dir}")
        os.makedirs(model_dir, exist_ok=True)
        
    # Check if model already exists
    if os.path.exists(model_path):
        print(f"Model already exists at {model_path}")
        choice = input("Do you want to re-download it? (y/n): ").lower()
        if choice != 'y':
            print("Download cancelled")
            return
    
    print(f"Downloading Qwen2-VL model from {model_url}")
    print(f"This may take a while as it's a large file (~4-5GB)")
    
    try:
        # Start the request with stream=True
        with requests.get(model_url, stream=True) as response:
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            
            # Create a progress bar
            with open(model_path, 'wb') as f, tqdm(
                desc="Downloading model",
                total=total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
            ) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
        
        print(f"Download complete! Model saved to {model_path}")
        print("You can now run: emuvlm-llama-server")
        
    except Exception as e:
        print(f"Error downloading model: {e}")
        if os.path.exists(model_path):
            print("Removing partial download...")
            os.remove(model_path)
        sys.exit(1)

if __name__ == "__main__":
    main()