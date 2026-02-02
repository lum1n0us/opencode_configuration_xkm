---
name: build-wamr
description: Build WebAssembly Micro Runtime (WAMR) components with explicit parameters. Supports building iwasm runtime, wamrc compiler, and unit tests with mandatory clang toolchain requirements. Pure build execution tool that accepts explicit targets and cmake options without modification analysis.
---

# Build WAMR

## Overview

This skill builds WebAssembly Micro Runtime (WAMR) components with explicit parameters and targets. It is a **pure build execution tool** that focuses solely on compiling WAMR components using CMake with **mandatory clang/clang++ compiler requirements**.

Unlike analysis-based build tools, this skill requires explicit specification of build targets and cmake options, making it ideal for integration with analysis pipelines or direct usage with known requirements.

## Quick Start

Build WAMR components with explicit parameters:

```bash
# Build iwasm (default target) 
python scripts/build_wamr.py --repo_path /path/to/wamr

# Build wamrc with custom options
python scripts/build_wamr.py --target wamrc -DWAMR_BUILD_AOT=1

# Build unit tests with multiple flags  
python scripts/build_wamr.py --target unit-test -DWAMR_BUILD_SIMD=1 -DWAMR_BUILD_JIT=1
```

## Parameters

### Required
- None (all parameters have defaults)

### Optional
- `--repo_path <path>`: Path to WAMR repository (default: current directory)
- `--target <target>`: Build target - `iwasm` (default), `wamrc`, or `unit-test`
- `--build_dir <path>`: Build directory (default: `build-<branch-name>` in current directory)
- `cmake_options...`: Arbitrary CMake flags (e.g., `-DWAMR_BUILD_JIT=1`)

## Build Targets

The skill maps targets to their respective source directories automatically:

| Target | Source Directory | Description |
|--------|-----------------|-------------|
| `iwasm` | `product-mini/platforms/linux` | WebAssembly runtime (default) |
| `wamrc` | `wamr-compiler` | WebAssembly compiler |
| `unit-test` | `tests/unit` | Unit test executables |

## Mandatory Requirements

### 🔥 Clang Toolchain (STRICT)
- **clang/clang++** compilers must be available in system PATH
- Valid clang toolchain file must exist in repository
- **NO fallbacks** - build fails immediately if requirements not met

### Expected Toolchain Location
The skill requires the clang toolchain file at this **exclusive** location:
- `build-scripts/clang_toolchain.cmake` (MANDATORY - no alternatives accepted)

### Automatic Configuration
- Always adds `-DCMAKE_EXPORT_COMPILE_COMMANDS=ON`
- Always uses clang toolchain file
- Build directory defaults to `build-<branch-name>`

## Usage Examples

### Basic Usage
```bash
# Default: Build iwasm in build-<branch> directory
python scripts/build_wamr.py

# Build specific target
python scripts/build_wamr.py --target wamrc

# Custom repository path
python scripts/build_wamr.py --repo_path /path/to/wamr-repo
```

### Advanced Usage
```bash
# Custom build directory with flags
python scripts/build_wamr.py --build_dir /tmp/wamr-build -DWAMR_BUILD_JIT=1

# Multiple cmake flags
python scripts/build_wamr.py --target iwasm -DWAMR_BUILD_SIMD=1 -DWAMR_BUILD_AOT=1 -DWAMR_BUILD_BULK_MEMORY=1

# Unit tests with debugging
python scripts/build_wamr.py --target unit-test -DCMAKE_BUILD_TYPE=Debug
```

### Integration with Analysis Pipeline
```bash
# Step 1: Analyze changes (separate tool/skill)
analyze_modifications.py pr-123 -> flags.txt

# Step 2: Build with detected flags
python scripts/build_wamr.py --target iwasm $(cat flags.txt)
```

## Build Process

For each target, the skill:

1. **Validates repository structure** - ensures WAMR directories exist
2. **Enforces clang requirements** - checks compiler availability and toolchain file
3. **Configures with CMake** - runs `cmake -S <source> -B <build> [options]`
4. **Builds with CMake** - runs `cmake --build <build>`
5. **Generates status report** - creates `build-wamr_status.md`

### Example Build Commands
```bash
# iwasm build
cmake -S product-mini/platforms/linux -B build-main/iwasm \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DCMAKE_TOOLCHAIN_FILE=build-scripts/clang_toolchain.cmake \
    -DWAMR_BUILD_JIT=1

cmake --build build-main/iwasm

# wamrc build  
cmake -S wamr-compiler -B build-main/wamrc \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DCMAKE_TOOLCHAIN_FILE=build-scripts/clang_toolchain.cmake \
    -DWAMR_BUILD_AOT=1

cmake --build build-main/wamrc

# unit-test build
cmake -S tests/unit -B build-main/unit-test \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DCMAKE_TOOLCHAIN_FILE=build-scripts/clang_toolchain.cmake

cmake --build build-main/unit-test
```

## Output Structure

After successful build:
```
<build_dir>/
├── build-wamr_status.md          # Success/failure status
├── iwasm/                        # iwasm build directory (if built)
│   ├── iwasm                     # Runtime executable  
│   ├── compile_commands.json     # IDE integration
│   └── [cmake artifacts]
├── wamrc/                        # wamrc build directory (if built)
│   ├── wamrc                     # Compiler executable
│   ├── compile_commands.json     # IDE integration  
│   └── [cmake artifacts]
└── unit-test/                    # unit tests directory (if built)
    ├── [test executables]
    ├── compile_commands.json     # IDE integration
    └── [cmake artifacts]
```

## Status Report Format

### Success
```
SUCCESS
```

### Failure
```
FAIL
<error message>
```

## Error Scenarios

### Missing Clang Compilers
```
❌ MANDATORY REQUIREMENT FAILED: Clang/clang++ compilers are required but not found in PATH.
   Please install clang and ensure both 'clang' and 'clang++' are available in your system PATH.
```

### Missing Toolchain File
```
❌ MANDATORY REQUIREMENT FAILED: build-scripts/clang_toolchain.cmake not found.
   This is the exclusive location required for the clang toolchain file.
   Please ensure clang_toolchain.cmake exists at: build-scripts/clang_toolchain.cmake
```

### Invalid Repository
```
FAIL
Repository does not appear to be a WAMR project. Missing required paths: core/iwasm
```

### Build Failure
```
FAIL
Command failed: cmake --build build-main/iwasm
Return code: 2
Stderr: [cmake error details]
```

## Installation Requirements

### System Dependencies
```bash
# Ubuntu/Debian
sudo apt install clang cmake

# CentOS/RHEL  
sudo yum install clang cmake

# macOS
xcode-select --install
brew install cmake
```

### Repository Requirements
- Valid WAMR repository with standard directory structure
- Clang toolchain file at `build-scripts/clang_toolchain.cmake` (mandatory location)
- CMakeLists.txt files in target source directories

## Integration Patterns

### With Analysis Skills
```bash
# 1. Detect modifications (separate skill)
analyze-pr -> analysis.md

# 2. Extract flags from analysis  
grep "WAMR_BUILD" analysis.md > flags.txt

# 3. Build with extracted flags
python scripts/build_wamr.py --target iwasm $(cat flags.txt)
```

### Standalone Usage
```bash
# Direct usage with known requirements
python scripts/build_wamr.py --target iwasm -DWAMR_BUILD_JIT=1 -DWAMR_BUILD_SIMD=1
```

### CI/CD Integration
```bash
# Pipeline step
- name: Build WAMR iwasm
  run: python scripts/build_wamr.py --target iwasm --build_dir ${{ runner.temp }}/wamr-build
```

## What This Skill Does NOT Do

This skill is **pure build execution** and does NOT:
- ❌ Analyze code modifications or diffs
- ❌ Auto-detect required compilation flags
- ❌ Parse `changes.diff` or `analysis.md` files  
- ❌ Determine what components to build based on file changes
- ❌ Run compiled executables or tests

For modification analysis and intelligent flag detection, use complementary analysis skills before invoking this build skill.

## Benefits of Pure Build Approach

### Predictability
- **Explicit parameters** - no hidden logic or assumptions
- **Deterministic builds** - same inputs always produce same outputs
- **Clear failure modes** - immediate feedback on missing requirements

### Integration Flexibility
- **Pipeline-friendly** - easily integrates with analysis tools
- **Composable** - combine with other skills for complex workflows
- **Testable** - simple to unit test and validate

### Performance
- **Fast execution** - no analysis overhead
- **Minimal dependencies** - only cmake and clang required
- **Efficient** - builds exactly what's requested

This skill provides reliable, fast WAMR component builds with strict quality requirements, making it ideal for both development workflows and CI/CD pipelines.