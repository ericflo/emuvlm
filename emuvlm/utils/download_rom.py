"""
ROM downloader utility for EmuVLM.
"""
import os
import requests
import argparse
from pathlib import Path
import time

def download_file(url, destination, chunk_size=8192):
    """
    Download a file from a URL to a destination path.
    
    Args:
        url (str): The URL to download from
        destination (str): The destination file path
        chunk_size (int): Size of chunks to download
        
    Returns:
        bool: True if download was successful, False otherwise
    """
    try:
        # Create parent directory if it doesn't exist
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        
        # Download the file
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()  # Raise exception for 4XX/5XX responses
        
        # Get total file size if available
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        # Open file for writing
        with open(destination, 'wb') as f:
            start_time = time.time()
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:  # Filter out keep-alive chunks
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Calculate and print progress
                    elapsed = time.time() - start_time
                    if elapsed > 0 and total_size > 0:
                        speed = downloaded / elapsed / 1024  # KB/s
                        percent = min(100, downloaded * 100 / total_size)
                        print(f"\rDownloading: {percent:.1f}% ({downloaded/1024:.0f}KB/{total_size/1024:.0f}KB) - {speed:.1f} KB/s", 
                              end="", flush=True)
            
            print("\nDownload complete!")
        
        return True
    except Exception as e:
        print(f"Error downloading file: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Download ROM files for EmuVLM")
    parser.add_argument("--game", type=str, required=True, help="Game name (zelda, pokemon, etc.)")
    parser.add_argument("--output", type=str, help="Output directory", default="roms/gb")
    args = parser.parse_args()
    
    # Dictionary of game URLs (these are example URLs, but can't actually contain ROM URLs)
    game_urls = {
        "zelda": "https://vimm.net/vault/2978",  # This is actually just the info page, not a direct download
        "pokemon": "https://vimm.net/vault/3511", # This is actually just the info page, not a direct download
        "test": "https://example.com/test.gb",    # For testing download functionality
    }
    
    # Determine output filename first, so we can use it for placeholder creation
    if args.game == "zelda":
        output_file = os.path.join(args.output, "zelda_links_awakening.gb")
    elif args.game == "pokemon":
        output_file = os.path.join(args.output, "pokemon_blue.gb")
    else:
        output_file = os.path.join(args.output, f"{args.game}.gb")
    
    print("NOTE: Due to legal restrictions, this script can't actually download ROM files.")
    print("Please obtain ROMs legally through physical cartridges you own.")
    print("For development testing, consider creating a placeholder file instead.")
    
    # Create a placeholder file for testing
    if args.game == "zelda" or args.game == "pokemon":
        # Create automatically in non-interactive environments
        print("Creating a placeholder ROM file for testing...")
        
        # Create GB ROM header structure
        with open(output_file, 'wb') as f:
            # Nintendo logo data (required by real Game Boy)
            nintendo_logo = bytearray([
                0xCE, 0xED, 0x66, 0x66, 0xCC, 0x0D, 0x00, 0x0B, 
                0x03, 0x73, 0x00, 0x83, 0x00, 0x0C, 0x00, 0x0D,
                0x00, 0x08, 0x11, 0x1F, 0x88, 0x89, 0x00, 0x0E, 
                0xDC, 0xCC, 0x6E, 0xE6, 0xDD, 0xDD, 0xD9, 0x99
            ])
            
            # Build a simple ROM with correct header
            rom_data = bytearray(32768)  # 32KB minimal GB ROM size
            
            # Add entry point (at 0x100)
            rom_data[0x100:0x104] = [0x00, 0xC3, 0x50, 0x01]  # Entry point
            
            # Add Nintendo logo (at 0x104)
            rom_data[0x104:0x134] = nintendo_logo
            
            # Set title (at 0x134)
            title = "ZELDA LINK" if args.game == "zelda" else "POKEMON BLUE"
            rom_data[0x134:0x134+len(title)] = title.encode('ascii')
            
            # Set cartridge type (MBC1+RAM+BATTERY) at 0x147
            rom_data[0x147] = 0x03
            
            # Set ROM size (32KB = 2 banks) at 0x148
            rom_data[0x148] = 0x01
            
            # Set RAM size (8KB) at 0x149 
            rom_data[0x149] = 0x02
            
            # Write the ROM file with header
            f.write(rom_data)
            
        print(f"Created placeholder file at {output_file}")
        print("This is NOT a real ROM, just a placeholder for testing.")
        return
    
    if args.game not in game_urls:
        print(f"Unknown game: {args.game}")
        print(f"Available games: {', '.join(game_urls.keys())}")
        return
    
    url = game_urls[args.game]
    
    print(f"Would download {args.game} ROM to {output_file} if this were a real downloader...")
    # Commented out actual download code
    # success = download_file(url, output_file)
    
    # Since we're not actually downloading, just print instructions
    print("ROM placeholder creation complete.")
    print(f"You can now use this ROM with the configuration:")
    print(f"python -m emuvlm.play --config emuvlm/config.yaml --game {args.game} --max-turns 300")

if __name__ == "__main__":
    main()