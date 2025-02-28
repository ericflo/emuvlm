# EmuVLM Development Guide

## Commands

### Build & Installation
```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Install with macOS dependencies 
pip install -e ".[macos]"
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_agent.py

# Run specific test function
pytest tests/test_agent.py::TestLLMAgent::test_initialization
```

### Linting & Formatting
```bash
# Format code
black .

# Sort imports
isort .
```

## Code Style Guidelines

- **Naming**: Use snake_case for functions/variables, PascalCase for classes
- **Imports**: Sort with isort (profile=black), group standard library first
- **Formatting**: Black with 100 line length
- **Documentation**: Docstrings for all public functions and classes
- **Type Hints**: Use Python type hints where appropriate
- **Error Handling**: Use proper exception handling with specific exceptions
- **Emulators**: All emulator classes should inherit from EmulatorBase
- **Tests**: Write unit tests for new features and bug fixes

## Repository Structure
- `emuvlm/`: Main package
- `emulators/`: Emulator implementations 
- `model/`: Vision-language model integration
- `tests/`: Test suite
- `scripts/`: Utility scripts