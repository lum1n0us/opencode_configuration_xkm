---
name: build-wamr
description: Build WebAssembly Micro Runtime (WAMR) components based on detected modifications. Intelligently builds iwasm (runtime) and/or wamrc (compiler) depending on changes detected in analysis.md or changes.diff files. Use after analyze-pr skill or when building WAMR projects with targeted component builds.
---

# Build WAMR

## Overview

This skill builds WebAssembly Micro Runtime (WAMR) components intelligently based on detected code modifications. It analyzes changes to determine whether to build the iwasm runtime, wamrc compiler, or both, then executes the appropriate CMake build commands.

## Quick Start

Build WAMR components based on detected modifications:

```bash
python scripts/build_wamr.py <inter_dir> [--repo_path <path>]
```

**Parameters:**
- `inter_dir`: Directory for temporary files and build outputs
- `--repo_path`: Path to WAMR git repository (defaults to current directory)

**Requirements:**
- CMake installed and available in PATH
- Valid WAMR repository structure
- Build dependencies for target platform

## Build Decision Logic

The skill follows this decision tree for determining what to build:

### 1. Analysis-Based Detection
If `analysis.md` exists in inter_dir, scans for keywords:
- **iwasm build triggers**: `core/iwasm`, `iwasm`, `core components`, `runtime`
- **wamrc build triggers**: `wamr-compiler`, `wamrc`, `compiler`

### 2. Diff-Based Detection  
If `changes.diff` exists in inter_dir, scans for file paths:
- **iwasm build triggers**: `core/iwasm/`, `core\\iwasm\\`
- **wamrc build triggers**: `wamr-compiler/`, `wamr_compiler/`

### 3. Fallback Strategy
If no reference files exist or no modifications detected:
- Builds **both** iwasm and wamrc components

## Build Components

### iwasm (WebAssembly Runtime)
When `core/iwasm` modifications are detected:

```bash
# Configure (with compile commands export)
cmake -S product-mini/platforms/linux -B ${inter_dir}/build/iwasm -DCMAKE_EXPORT_COMPILE_COMMANDS=ON

# Build  
cmake --build ${inter_dir}/build/iwasm
```

**Output**: 
- Runtime executable in `${inter_dir}/build/iwasm/`
- `compile_commands.json` for IDE integration and static analysis

### wamrc (WebAssembly Compiler)
When `wamr-compiler` modifications are detected:

```bash
# Configure (with compile commands export)
cmake -S wamr-compiler -B ${inter_dir}/build/wamrc -DCMAKE_EXPORT_COMPILE_COMMANDS=ON

# Build
cmake --build ${inter_dir}/build/wamrc  
```

**Output**: 
- Compiler executable in `${inter_dir}/build/wamrc/`
- `compile_commands.json` for IDE integration and static analysis

## Repository Validation

The skill validates WAMR repository structure by checking for:
- `core/iwasm/` - Runtime source directory
- `wamr-compiler/` - Compiler source directory  
- `product-mini/platforms/linux/` - Linux platform build files

Missing directories will cause build failure with descriptive error message.

## Output Files

### Status Report (`build-wamr_status.md`)
**Success format:**
```
SUCCESS
```

**Failure format:**
```
FAIL
Repository does not appear to be a WAMR project. Missing required paths: core/iwasm
```

### Build Artifacts
- `${inter_dir}/build/iwasm/` - iwasm runtime build outputs
- `${inter_dir}/build/wamrc/` - wamrc compiler build outputs

## Integration Examples

**With analyze-pr workflow:**
```bash
# 1. Fetch PR data
python scripts/fetch_pr.py 123 ./pr_data

# 2. Analyze modifications  
python scripts/analyze_pr.py 123 ./pr_data

# 3. Build based on analysis
python scripts/build_wamr.py ./pr_data --repo_path /path/to/wamr
```

**Standalone usage:**
```bash
# Build all components (no analysis files)
python scripts/build_wamr.py ./build_output

# Build with existing diff
cp changes.diff ./build_data/
python scripts/build_wamr.py ./build_data
```

**Custom repository path:**
```bash
python scripts/build_wamr.py ./outputs --repo_path /path/to/wamr-repo
```

## Error Handling

Common failure scenarios:
- **Invalid repository**: Validates WAMR directory structure
- **Missing CMake**: Clear error if cmake command not found
- **Build failures**: Captures cmake output and error details
- **Permission issues**: Handles directory creation and access errors

### Typical Error Messages
```
FAIL
Repository does not appear to be a WAMR project. Missing required paths: wamr-compiler

FAIL  
Command failed: cmake -S wamr-compiler -B /tmp/build/wamrc
Return code: 1
Stderr: CMake Error: The source directory does not exist.
```

## Build Output Structure

After successful build:
```
${inter_dir}/
├── build-wamr_status.md          # Success/failure status
├── build/
│   ├── iwasm/                     # iwasm build directory
│   │   ├── iwasm                  # Runtime executable  
│   │   ├── compile_commands.json  # IDE integration file
│   │   └── [cmake artifacts]      # Build files
│   └── wamrc/                     # wamrc build directory
│       ├── wamrc                  # Compiler executable
│       ├── compile_commands.json  # IDE integration file
│       └── [cmake artifacts]      # Build files
└── [analysis.md/changes.diff]     # Input analysis files
```

The `compile_commands.json` files generated by the `-DCMAKE_EXPORT_COMPILE_COMMANDS=ON` flag provide:
- IDE integration for code completion and navigation
- Static analysis tool support (clang-tidy, etc.)
- Language server protocol (LSP) compatibility

The skill provides targeted, efficient building of WAMR components based on intelligent modification detection, making it ideal for CI/CD pipelines and development workflows.
