#!/bin/bash
# Script to help install all emulator dependencies for EmuVLM
# Note: For complete dependencies, install the package with pip install -e .

set -e # Exit on any error

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    # Check if we're on Debian/Ubuntu
    if [ -f /etc/debian_version ]; then
        OS_VARIANT="debian"
    elif [ -f /etc/redhat-release ]; then
        OS_VARIANT="redhat"
    else
        OS_VARIANT="unknown"
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    # Check if Homebrew is installed
    if ! command -v brew &> /dev/null; then
        echo "Homebrew not found. Please install it first:"
        echo "/bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
else
    echo "Unsupported operating system: $OSTYPE"
    echo "This script supports Linux (Debian/Ubuntu) and macOS."
    exit 1
fi

echo "===== EmuVLM Emulator Dependencies Installation ====="
echo "Detected OS: $OS $([ -n "$OS_VARIANT" ] && echo "($OS_VARIANT)")"
echo "This script will help you install the dependencies for various emulators used by EmuVLM."
echo

# Function to install dependencies for a specific emulator
install_emulator_deps() {
    local emulator=$1
    echo
    echo "===== Installing dependencies for $emulator ====="
    
    case $emulator in
        "pyboy")
            echo "Installing PyBoy (Game Boy/Game Boy Color) dependencies..."
            if [ "$OS" == "linux" ]; then
                if [ "$OS_VARIANT" == "debian" ]; then
                    sudo apt-get update
                    sudo apt-get install -y libsdl2-dev libsdl2-ttf-dev
                elif [ "$OS_VARIANT" == "redhat" ]; then
                    sudo dnf install -y SDL2-devel SDL2_ttf-devel
                fi
            elif [ "$OS" == "macos" ]; then
                brew install sdl2 sdl2_ttf
            fi
            
            echo "Installing PyBoy package (v1.6.0)..."
            pip install pyboy==1.6.0
            ;;
            
        "mgba")
            echo "Installing mGBA (Game Boy Advance) dependencies..."
            if [ "$OS" == "linux" ]; then
                if [ "$OS_VARIANT" == "debian" ]; then
                    sudo apt-get update
                    sudo apt-get install -y build-essential cmake libzip-dev libsdl2-dev qtbase5-dev libqt5opengl5-dev
                elif [ "$OS_VARIANT" == "redhat" ]; then
                    sudo dnf install -y cmake libzip-devel SDL2-devel qt5-qtbase-devel
                fi
            elif [ "$OS" == "macos" ]; then
                brew install cmake qt@5 sdl2 libzip
                # Add Qt to PATH for build process
                export PATH="$(brew --prefix qt@5)/bin:$PATH"
            fi
            
            echo "Note: mGBA requires building from source. See the README for complete instructions."
            ;;
            
        "fceux")
            echo "Installing FCEUX (NES) dependencies..."
            if [ "$OS" == "linux" ]; then
                if [ "$OS_VARIANT" == "debian" ]; then
                    sudo apt-get update
                    sudo apt-get install -y fceux lua5.1 liblua5.1-dev
                elif [ "$OS_VARIANT" == "redhat" ]; then
                    sudo dnf install -y fceux lua lua-devel
                fi
            elif [ "$OS" == "macos" ]; then
                brew install fceux lua
            fi
            
            echo "Note: FCEUX should be available in your PATH after installation."
            ;;
            
        "snes9x")
            echo "Installing Snes9x (SNES) dependencies..."
            if [ "$OS" == "linux" ]; then
                if [ "$OS_VARIANT" == "debian" ]; then
                    sudo apt-get update
                    sudo apt-get install -y snes9x-gtk
                elif [ "$OS_VARIANT" == "redhat" ]; then
                    sudo dnf install -y snes9x
                fi
            elif [ "$OS" == "macos" ]; then
                brew install snes9x
            fi
            
            echo "Note: Snes9x should be available in your PATH after installation."
            ;;
            
        "genesis")
            echo "Installing Genesis Plus GX (Sega Genesis/Mega Drive) dependencies..."
            echo "Genesis Plus GX is a standalone emulator that may need to be built from source."
            echo "Please check the EmuVLM documentation for more details."
            ;;
            
        "mupen64plus")
            echo "Installing Mupen64Plus (Nintendo 64) dependencies..."
            if [ "$OS" == "linux" ]; then
                if [ "$OS_VARIANT" == "debian" ]; then
                    sudo apt-get update
                    sudo apt-get install -y mupen64plus-ui-console
                elif [ "$OS_VARIANT" == "redhat" ]; then
                    sudo dnf install -y mupen64plus
                fi
            elif [ "$OS" == "macos" ]; then
                brew install mupen64plus
            fi
            
            echo "Note: Mupen64Plus should be available in your PATH after installation."
            ;;
            
        "duckstation")
            echo "Installing DuckStation (PlayStation) dependencies..."
            echo "DuckStation is a standalone emulator that needs to be downloaded separately."
            echo "Please download from: https://github.com/stenzek/duckstation/releases"
            echo "After download, make sure the duckstation-nogui binary is in your PATH."
            ;;
            
        *)
            echo "Unknown emulator: $emulator"
            return 1
            ;;
    esac
    
    echo "Dependencies for $emulator installed successfully."
    return 0
}

# Install package with all dependencies (use pyproject.toml)
echo "Installing Python dependencies from package..."
pip install -e .

# Install emulator dependencies one by one
emulators=("pyboy" "mgba" "fceux" "snes9x" "genesis" "mupen64plus" "duckstation")

for emulator in "${emulators[@]}"; do
    read -p "Install dependencies for $emulator? (y/n) " choice
    case "$choice" in
        y|Y)
            install_emulator_deps "$emulator"
            ;;
        *)
            echo "Skipping $emulator"
            ;;
    esac
done

echo
echo "===== Installation Summary ====="
echo "Installed Python dependencies from pyproject.toml"
echo
echo "Next steps:"
echo "1. Some emulators may require additional configuration - check the EmuVLM documentation"
echo "2. Run 'emuvlm-test-emulators' to verify your emulator installations"
echo "3. Run 'test_emulator_example.sh' (after setting ROM paths) to test all emulators"
echo
echo "Installation completed!"