# C/C++ Macro Analyzer

A Python tool that analyzes C/C++ source files to determine which preprocessor macros control a specific line of code. Given a file path and line number, it outputs JSON with the combined logical expression of all controlling macros.

## Features

- **PCPP-based preprocessor**: Uses Python C Preprocessor (pcpp) library for accurate C99 preprocessor simulation
- **Three-level logging**: `-v` (verbose), `-vv` (debug), `-vvv` (trace) for detailed debugging
- **Full condition tracking**: Handles nested `#if` blocks, `#elif`, `#else`, `#ifdef`, `#ifndef`
- **Expression parsing**: Supports `defined()`, comparisons (`==`, `>`, `<`), logical operators (`&&`, `||`, `!`)
- **String comparison**: Handles `PLATFORM == "linux"` style comparisons
- **Condition combination**: Outputs combined logical expression for all active conditions
- **JSON output**: Structured output with file, line, macros, and combined expression
- **Error handling**: Proper exit codes and error messages

## Installation

### Option 1: Install as package (recommended for frequent use)
```bash
# From local directory
pip install -e /path/to/c-macro-analyzer

# Or if already in the directory
pip install -e .
```

### Option 2: Direct module execution (no installation needed)
```bash
# Run directly using python -m
python -m macro_analyzer path/to/file.c 42
```

## Usage

### Basic usage
```bash
macro-analyzer path/to/file.c 42
```

Or without installation:
```bash
python -m macro_analyzer path/to/file.c 42
```

### Output format
```bash
# JSON output (default)
macro-analyzer src/main.c 123

# Text output
macro-analyzer src/main.c 123 --output text

# Verbose logging (-v = INFO, -vv = DEBUG, -vvv = TRACE)
macro-analyzer src/main.c 123 -v
macro-analyzer src/main.c 123 -vv
macro-analyzer src/main.c 123 -vvv
```

### Example output
```json
{
  "file": "example.c",
  "line": 42,
  "macros": [
    {
      "name": "DEBUG",
      "condition": "defined",
      "expression": "defined(DEBUG)"
    },
    {
      "name": "VERSION",
      "condition": "comparison",
      "expression": "VERSION > 1"
    }
  ],
  "combined_expression": "defined(DEBUG) && VERSION > 1"
}
```

**Note:** Header guard macros (matching `*_H*` pattern) are automatically filtered from the output.

### Output Format Details

The analyzer returns a JSON object with the following structure:

- **file**: Path to the analyzed file
- **line**: Target line number (1-indexed)
- **macros**: Array of macro information objects, each containing:
  - **name**: Macro identifier
  - **condition**: Usage type: `"defined"`, `"comparison"`, or `"value"`
  - **expression**: The specific expression fragment containing this macro
- **combined_expression**: Full logical expression combining all active conditions

**Header Guard Filtering:** Macros matching the pattern `*_H*` (e.g., `HEADER_H`, `MY_HEADER_H_`) are automatically excluded from the output, as they typically represent include guards rather than configuration macros.

## Using in Other Repositories

### Method 1: Direct python -m execution (simplest)
You can run the tool directly from any location without installation:

```bash
# From any directory, using absolute path
python -m macro_analyzer /path/to/your/file.c 42

# Or navigate to the tool directory first
cd /path/to/c-macro-analyzer
python -m macro_analyzer /path/to/your/file.c 42
```

### Method 2: Create a wrapper script
Create a simple script in your repository:

```bash
#!/usr/bin/env bash
# analyze-macros.sh
TOOL_DIR="/path/to/c-macro-analyzer"
python -m macro_analyzer "$@"
```

### Method 3: Git submodule integration
```bash
# Add as submodule
git submodule add https://github.com/your-username/macro-analyzer.git tools/macro-analyzer

# Create wrapper
echo '#!/usr/bin/env bash
cd "$(dirname "$0")/tools/macro-analyzer"
python -m macro_analyzer "$@"
' > analyze-macros.sh
chmod +x analyze-macros.sh
```

### Method 4: CI/CD integration (GitHub Actions example)
```yaml
- name: Analyze macros
  run: |
    cd /path/to/c-macro-analyzer
    python -m macro_analyzer src/critical.c 123 > analysis.json
    # Process the JSON output...
```

## How It Works

The tool simulates C preprocessor behavior:

1. **Processes file line by line**
2. **Tracks macro definitions** (`#define`, `#undef`)
3. **Evaluates conditions** (`#if`, `#ifdef`, `#ifndef`, `#elif`, `#else`)
4. **Maintains condition stack** for nested blocks
5. **Combines active conditions** with `&&` operators
6. **Outputs JSON** with analysis results

### Supported Directives
- `#define MACRO value` / `#define MACRO`
- `#undef MACRO`
- `#if expression`
- `#ifdef MACRO`
- `#ifndef MACRO`
- `#elif expression`
- `#else`
- `#endif`

### Expression Support
- Arithmetic: `+`, `-`, `*`, `/`, `%`
- Comparison: `==`, `!=`, `<`, `>`, `<=`, `>=`
- Logical: `&&`, `||`, `!`
- Defined check: `defined(MACRO)`
- String literals: `"value"`

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run specific test file
pytest tests/test_analyzer.py -v

# Format code
black macro_analyzer tests
ruff check --fix macro_analyzer tests
```

### Project Structure
```
c-macro-analyzer/
├── macro_analyzer/
│   ├── __init__.py
│   ├── analyzer.py      # PCPP-based analyzer with condition tracking
│   ├── logging.py       # Three-level logging system
│   ├── cli.py           # Command-line interface with -v/-vv/-vvv options
│   └── __main__.py      # Module entry point
├── tests/
│   ├── test_analyzer.py
│   ├── test_logging.py
│   ├── test_cli.py
│   ├── test_integration.py
│   └── samples/         # Test C files
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Troubleshooting

### Common Issues

1. **"ModuleNotFoundError: No module named 'macro_analyzer'"**
   - Ensure you're in the correct directory or have installed the package
   - Use `python -m macro_analyzer` from the project root

2. **String comparison not working**
   - Make sure string values are quoted: `#define PLATFORM "linux"`
   - The tool supports `PLATFORM == "linux"` comparisons

3. **Line not found or empty output**
   - Line number is 1-indexed (first line = 1)
   - Check if the line is inside an inactive `#if` block

4. **File not found errors**
   - Use absolute paths or ensure relative paths are correct
   - The tool returns exit code 1 for file errors

## License

MIT