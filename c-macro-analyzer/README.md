# C/C++ Macro Analyzer

A Python tool that analyzes C/C++ source files to determine which preprocessor macros control a specific line of code. Given a file path and line number, it outputs JSON with the combined logical expression of all controlling macros.

## Installation

```bash
pip install -e .
```

## Usage

```bash
macro-analyzer path/to/file.c 42
```

Example output:
```json
{
  "file": "example.c",
  "line": 42,
  "macros": [
    {"name": "DEBUG", "condition": "defined"},
    {"name": "VERSION", "condition": "> 1"}
  ],
  "combined_expression": "defined(DEBUG) && VERSION > 1"
}
```

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black macro_analyzer tests
ruff check --fix macro_analyzer tests
```

## License

MIT