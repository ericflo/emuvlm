"""
Utility functions for loading ROM files, including support for ZIP files.
"""
import os
import logging
import tempfile
import zipfile
import shutil
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# Global cache to store extracted ROM file paths
_ROM_CACHE: Dict[str, str] = {}

def load_rom(rom_path: str) -> str:
    """
    Load a ROM file, extracting it from ZIP if necessary.
    
    Args:
        rom_path: Path to the ROM file or ZIP archive
        
    Returns:
        Path to the actual ROM file (extracted if needed)
    """
    # Check if we've already processed this ROM
    if rom_path in _ROM_CACHE:
        # Verify the cached file still exists
        if os.path.exists(_ROM_CACHE[rom_path]):
            logger.debug(f"Using cached ROM file: {_ROM_CACHE[rom_path]}")
            return _ROM_CACHE[rom_path]
        else:
            # Remove invalid cache entry
            del _ROM_CACHE[rom_path]
    
    # If the file doesn't exist, report an error
    if not os.path.exists(rom_path):
        raise FileNotFoundError(f"ROM file not found: {rom_path}")
    
    # Handle different file types
    if rom_path.lower().endswith('.zip'):
        extracted_path = _extract_from_zip(rom_path)
        if extracted_path:
            _ROM_CACHE[rom_path] = extracted_path
            return extracted_path
        else:
            raise ValueError(f"Failed to extract ROM from ZIP: {rom_path}")
    else:
        # Direct ROM file, just return the path
        return rom_path

def _extract_from_zip(zip_path: str) -> Optional[str]:
    """
    Extract a ROM file from a ZIP archive.
    
    Args:
        zip_path: Path to the ZIP archive
        
    Returns:
        Path to the extracted ROM file, or None if extraction failed
    """
    try:
        # Create a temp directory for extracted files
        temp_dir = os.path.join(tempfile.gettempdir(), "emuvlm_roms")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Create a subdirectory based on the ZIP filename to avoid conflicts
        zip_basename = os.path.basename(zip_path).replace('.zip', '')
        extract_dir = os.path.join(temp_dir, zip_basename)
        os.makedirs(extract_dir, exist_ok=True)
        
        logger.info(f"Extracting {zip_path} to {extract_dir}")
        
        # Extract the ZIP contents
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Get a list of files in the ZIP
            file_list = zip_ref.namelist()
            
            # First, look for ROM file extensions
            rom_extensions = ['.gb', '.gbc', '.gba', '.nes', '.smc', '.sfc', 
                             '.md', '.bin', '.smd', '.n64', '.z64', '.v64', 
                             '.gg', '.sms', '.iso', '.cue']
            
            # Find the first file with a valid ROM extension
            rom_file = None
            for file in file_list:
                file_lower = file.lower()
                if any(file_lower.endswith(ext) for ext in rom_extensions):
                    rom_file = file
                    break
            
            # If no ROM files found, try using the largest file
            if not rom_file and file_list:
                # Get file info for all entries
                file_info = [(f, zip_ref.getinfo(f).file_size) for f in file_list 
                             if not f.endswith('/')]  # Skip directories
                
                if file_info:
                    # Sort by file size (descending)
                    file_info.sort(key=lambda x: x[1], reverse=True)
                    rom_file = file_info[0][0]
            
            if not rom_file:
                logger.error(f"No ROM file found in ZIP: {zip_path}")
                return None
            
            # Extract just the ROM file
            logger.info(f"Extracting ROM file: {rom_file}")
            zip_ref.extract(rom_file, extract_dir)
            
            # Return the full path to the extracted ROM
            extracted_path = os.path.join(extract_dir, rom_file)
            return extracted_path
            
    except Exception as e:
        logger.error(f"Error extracting ROM from ZIP: {e}")
        return None

def cleanup_rom_cache():
    """
    Clean up temporary extracted ROM files.
    Call this when shutting down the application.
    """
    temp_dir = os.path.join(tempfile.gettempdir(), "emuvlm_roms")
    if os.path.exists(temp_dir):
        logger.info(f"Cleaning up temporary ROM files in {temp_dir}")
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            logger.error(f"Error cleaning up ROM cache: {e}")