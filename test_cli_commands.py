#!/usr/bin/env python3
"""
Test script to verify that all EmuVLM CLI commands are working correctly.
This script checks that all entry points defined in pyproject.toml can be imported
and accessed, but doesn't actually execute the commands (which might require
ROMs or the VLM server).
"""

import importlib
import inspect
import os
import sys
import traceback
from importlib.util import find_spec

# Add the project root to the path if needed
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Define the CLI entry points from pyproject.toml
CLI_ENTRY_POINTS = {
    "emuvlm": "emuvlm.cli:main",
    "emuvlm-demo": "emuvlm.cli:demo",
    "emuvlm-monitor": "emuvlm.cli:monitor",
    "emuvlm-test-emulators": "emuvlm.cli:test_emulators",
    "emuvlm-test-model": "emuvlm.cli:test_model",
    "emuvlm-vllm-server": "emuvlm.cli:start_vllm_server",
}

# ANSI color codes for prettier output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"

def check_module_exists(module_name):
    """Check if a module exists and can be imported."""
    try:
        return find_spec(module_name) is not None
    except ModuleNotFoundError:
        return False

def test_cli_entry_point(command_name, entry_point):
    """Test a single CLI entry point."""
    print(f"{BOLD}Testing {command_name}{RESET} ({entry_point})...")
    
    # Parse the entry point
    module_path, function_name = entry_point.split(":")
    
    # Check if the module exists
    if not check_module_exists(module_path):
        print(f"  {RED}✗ Module {module_path} not found{RESET}")
        return False
    
    # Try to import the module
    try:
        module = importlib.import_module(module_path)
        print(f"  {GREEN}✓ Module {module_path} imported successfully{RESET}")
        
        # Check if the function exists
        if not hasattr(module, function_name):
            print(f"  {RED}✗ Function {function_name} not found in {module_path}{RESET}")
            return False
        
        # Get the function
        function = getattr(module, function_name)
        
        # Check if it's actually callable
        if not callable(function):
            print(f"  {RED}✗ {function_name} is not callable{RESET}")
            return False
        
        print(f"  {GREEN}✓ Function {function_name} is callable{RESET}")
        
        # Additional checks on the function
        if hasattr(function, "__doc__") and function.__doc__:
            print(f"  {GREEN}✓ Function has documentation{RESET}")
        else:
            print(f"  {YELLOW}! Function lacks documentation{RESET}")
        
        # Check the imported modules that the function depends on
        try:
            source_code = inspect.getsource(function)
            deps = []
            for line in source_code.split("\n"):
                if "import" in line and "from" in line:
                    deps.append(line.strip())
            
            if deps:
                print(f"  {YELLOW}! Function imports:{RESET}")
                for dep in deps:
                    print(f"    - {dep}")
            
            # Check if the function attempts to import modules that might be 
            # optional dependencies
            print(f"  {GREEN}✓ Entry point {command_name} is accessible{RESET}")
            return True
            
        except Exception as e:
            print(f"  {YELLOW}! Could not inspect function source: {e}{RESET}")
            return True
            
    except Exception as e:
        print(f"  {RED}✗ Error importing {module_path}: {e}{RESET}")
        traceback.print_exc()
        return False

def main():
    """Test all CLI entry points."""
    print(f"{BOLD}EmuVLM CLI Command Verification{RESET}")
    print("=" * 60)
    print(f"This script verifies that all CLI commands defined in {BOLD}pyproject.toml{RESET}")
    print(f"are accessible and can be imported correctly.\n")
    
    success_count = 0
    failure_count = 0
    
    for command, entry_point in CLI_ENTRY_POINTS.items():
        print("-" * 60)
        result = test_cli_entry_point(command, entry_point)
        if result:
            success_count += 1
        else:
            failure_count += 1
    
    print("=" * 60)
    print(f"{BOLD}Summary:{RESET}")
    print(f"  {GREEN}✓ {success_count} commands verified successfully{RESET}")
    if failure_count > 0:
        print(f"  {RED}✗ {failure_count} commands have issues{RESET}")
    else:
        print(f"  {GREEN}All CLI commands are accessible!{RESET}")
    
    return 0 if failure_count == 0 else 1

if __name__ == "__main__":
    sys.exit(main())