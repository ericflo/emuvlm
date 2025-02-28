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
    parser = argparse.ArgumentParser(description="Start llama.cpp server with a vision language model")
    parser.add_argument("model_path", nargs='?', help="Path to GGUF model file (optional, will use config.yaml if not provided)")
    parser.add_argument("--host", default="0.0.0.0", help="Host address to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    parser.add_argument("--ctx", type=int, help="Context size (auto-configured by default)")
    parser.add_argument("--gpu-layers", type=int, default=-1, help="Number of layers to run on GPU (-1 for all)")
    parser.add_argument("--direct", action="store_true", help="Run Python server directly instead of using the shell script")
    from emuvlm.constants import VALID_MODEL_TYPES
    parser.add_argument("--model-type", choices=VALID_MODEL_TYPES, default="llava", 
                        help=f"Vision language model type ({', '.join(VALID_MODEL_TYPES)}). Default: llava")
    
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
                    
                    # Check if model_type is specified in config
                    config_model_type = config.get('model', {}).get('model_type')
                    if config_model_type and not args.model_type:
                        args.model_type = config_model_type
                        print(f"Using model type from config: {args.model_type}")
    
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
        
        # Add model-specific settings
        if args.model_type == "llava" or args.model_type == "qwen" or args.model_type == "minicpm":
            # Get model directory to locate mmproj file
            model_dir = os.path.dirname(os.path.dirname(__file__))
            mmproj_dir = os.path.join(model_dir, "models")

            # Select appropriate mmproj file based on model type
            if args.model_type == "llava":
                mmproj_file = os.path.join(mmproj_dir, "llava-v1.5-7b-mmproj-f16.gguf")
                if not os.path.exists(mmproj_file):
                    print(f"Warning: LLaVA multimodal projector file not found at {mmproj_file}")
                    print("You may need to download it manually from:")
                    print("https://huggingface.co/mys/ggml_llava-v1.5-7b/resolve/main/mmproj-model-f16.gguf")
            elif args.model_type == "qwen":
                mmproj_file = os.path.join(mmproj_dir, "mmproj-Qwen2-VL-7B-Instruct-f32.gguf")
                if not os.path.exists(mmproj_file):
                    print(f"Warning: Qwen2-VL multimodal projector file not found at {mmproj_file}")
                    print("You may need to download it manually from:")
                    print("https://huggingface.co/bartowski/Qwen2-VL-7B-Instruct-GGUF/resolve/main/mmproj-Qwen2-VL-7B-Instruct-f32.gguf")
            elif args.model_type == "minicpm":
                mmproj_file = os.path.join(mmproj_dir, "mmproj-model-f16.gguf")
                if not os.path.exists(mmproj_file):
                    print(f"Warning: MiniCPM multimodal projector file not found at {mmproj_file}")
                    print("You may need to download it manually from:")
                    print("https://huggingface.co/openbmb/MiniCPM-o-2_6-gguf/resolve/main/mmproj-model-f16.gguf")
            
            # Set clip_model_path if mmproj file exists
            if os.path.exists(mmproj_file):
                print(f"Using multimodal projector: {mmproj_file}")
                setattr(settings, "clip_model_path", mmproj_file)
        
        # Create app
        app = create_app(settings=settings)
        
        # Run the server
        print(f"Starting llama.cpp server with model: {model_path} (type: {args.model_type})")
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
        if args.model_type:
            cmd.extend(["--model-type", args.model_type])
        
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
    import argparse
    from pathlib import Path
    from tqdm import tqdm
    from emuvlm.constants import MODEL_PATHS, MODEL_URLS, MMPROJ_PATHS, MMPROJ_URLS, VALID_MODEL_TYPES
    
    # Parse arguments
    parser = argparse.ArgumentParser(description="Download a vision language model")
    parser.add_argument("--model-type", choices=VALID_MODEL_TYPES, default="llava", 
                       help=f"Vision language model type ({', '.join(VALID_MODEL_TYPES)}). Default: llava")
    args = parser.parse_args()
    
    model_type = args.model_type
    model_url = MODEL_URLS[model_type]
    mmproj_url = MMPROJ_URLS[model_type]
    model_path = MODEL_PATHS[model_type]
    mmproj_path = MMPROJ_PATHS[model_type]
    
    # Resolve relative paths if needed
    if not os.path.isabs(model_path):
        model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), model_path)
    
    if not os.path.isabs(mmproj_path):
        mmproj_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), mmproj_path)
    
    # Create model directory if it doesn't exist
    model_dir = os.path.dirname(model_path)
    if not os.path.exists(model_dir):
        print(f"Creating model directory: {model_dir}")
        os.makedirs(model_dir, exist_ok=True)
    
    # Download main model
    if os.path.exists(model_path):
        print(f"Model already exists at {model_path}")
        choice = input("Do you want to re-download it? (y/n): ").lower()
        if choice != 'y':
            print("Model download cancelled")
        else:
            download_file(model_url, model_path, f"Downloading {model_type} model")
    else:
        download_file(model_url, model_path, f"Downloading {model_type} model")
    
    # Download mmproj file
    if os.path.exists(mmproj_path):
        print(f"Multimodal projector already exists at {mmproj_path}")
        choice = input("Do you want to re-download it? (y/n): ").lower()
        if choice != 'y':
            print("Projector download cancelled")
        else:
            download_file(mmproj_url, mmproj_path, "Downloading multimodal projector")
    else:
        download_file(mmproj_url, mmproj_path, "Downloading multimodal projector")
    
    # Update config.yaml with the new model path
    update_config(model_path, model_url)
    
    print(f"Download complete! You can now run: emuvlm-llama-server --model-type {model_type}")

def download_file(url, path, desc):
    """Helper function to download a file with progress bar."""
    import requests
    from tqdm import tqdm
    
    print(f"{desc} from {url}")
    print(f"This may take a while as it's a large file")
    
    try:
        # Start the request with stream=True
        with requests.get(url, stream=True) as response:
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            
            # Create a progress bar
            with open(path, 'wb') as f, tqdm(
                desc=desc,
                total=total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
            ) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
        
        print(f"Downloaded successfully to {path}")
        return True
        
    except Exception as e:
        print(f"Error downloading file: {e}")
        if os.path.exists(path):
            print("Removing partial download...")
            os.remove(path)
        return False

def update_config(model_path, model_url):
    """Update config.yaml with new model path and URL."""
    import os
    import yaml
    
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    
    if not os.path.exists(config_path):
        print(f"Config file not found at {config_path}, skipping config update")
        return
    
    try:
        # Load existing config
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Update model path and URL
        if 'model' in config:
            config['model']['model_path'] = os.path.relpath(model_path, os.path.dirname(os.path.dirname(__file__)))
            config['model']['model_url'] = model_url
            
            # Save updated config
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            
            print(f"Updated config.yaml with new model settings")
    
    except Exception as e:
        print(f"Error updating config: {e}")
        print("You may need to manually update your config.yaml file")

if __name__ == "__main__":
    main()