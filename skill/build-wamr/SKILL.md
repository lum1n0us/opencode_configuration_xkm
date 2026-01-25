---
name: build-wamr
description: Build WebAssembly Micro Runtime (WAMR) components based on detected modifications with MANDATORY clang/toolchain requirements. Intelligently builds iwasm (runtime) and/or wamrc (compiler) depending on changes detected in analysis.md or changes.diff files. Automatically detects and enables compilation flags needed for modified lines. REQUIRES clang/clang++ compilers and valid toolchain configuration. Use after analyze-pr skill or when building WAMR projects with targeted component builds.
---

# Build WAMR

## Overview

This skill builds WebAssembly Micro Runtime (WAMR) components intelligently based on detected code modifications. It analyzes changes to determine whether to build the iwasm runtime, wamrc compiler, or both, then executes the appropriate CMake build commands with **MANDATORY clang/clang++ compiler requirements** and **comprehensive toolchain validation**.

## Quick Start

Build WAMR components based on detected modifications:

```bash
python scripts/build_wamr.py <inter_dir> [--repo_path <path>]
```

**Parameters:**
- `inter_dir`: Directory for temporary files and build outputs
- `--repo_path`: Path to WAMR git repository (defaults to current directory)

**MANDATORY Requirements:**
- CMake installed and available in PATH
- **🔥 CLANG/CLANG++ COMPILERS REQUIRED** - No fallback to system compilers
- **🔥 VALID CLANG TOOLCHAIN FILE REQUIRED** - No automatic generation
- Valid WAMR repository structure
- Build dependencies for target platform

## 🔥 STRICT: Mandatory Clang Compiler Integration

The skill now ENFORCES **clang/clang++** compilers for all WAMR builds with **zero tolerance for missing requirements**:

### Mandatory Toolchain Requirements
1. **🔥 STRICT SEARCH**: Searches for existing toolchain in required locations:
   - `tests/fuzz/wasm-mutator-fuzz/clang_toolchain.cmake`
   - `build-scripts/clang_toolchain.cmake`  
   - `cmake/clang_toolchain.cmake`
   - `toolchain/clang_toolchain.cmake`
2. **❌ NO FALLBACKS**: Build FAILS immediately if no toolchain file found
3. **📁 FILE VALIDATION**: Validates toolchain file exists (no content inspection)
4. **⚡ CLANG REQUIREMENT**: Clang/clang++ must be available in system PATH

### Clang Toolchain Configuration
```cmake
# Automatically configured clang toolchain
set(CMAKE_C_COMPILER clang)
set(CMAKE_CXX_COMPILER clang++)

# Optimized build flags
set(CMAKE_C_FLAGS_DEBUG "-g -O0 -fno-omit-frame-pointer")
set(CMAKE_C_FLAGS_RELEASE "-O3 -DNDEBUG")

# Enhanced warnings and analysis
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wall -Wextra")

# Fuzzing support (if enabled)
if(WAMR_BUILD_FUZZ_TEST)
    set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -fsanitize=fuzzer,address")
endif()
```

### Build Integration Examples

#### **With Repository Toolchain:**
```bash
# Uses tests/fuzz/wasm-mutator-fuzz/clang_toolchain.cmake
cmake -S product-mini/platforms/linux -B build/iwasm \
    -DCMAKE_TOOLCHAIN_FILE=tests/fuzz/wasm-mutator-fuzz/clang_toolchain.cmake \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DWAMR_BUILD_SIMD=1
```

#### **With Fallback Toolchain:**
```bash
# Creates and uses fallback_clang_toolchain.cmake
cmake -S product-mini/platforms/linux -B build/iwasm \
    -DCMAKE_TOOLCHAIN_FILE=fallback_clang_toolchain.cmake \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DWAMR_BUILD_JIT=1
```

## ⚡ OPTIMIZED: Fast WASM_ENABLE Flag Detection

The skill now uses **focused analysis** for speed and simplicity, concentrating only on modified lines:

### Simple Detection Process

#### **Single Step: Modified Line Analysis**
- Analyzes only modified lines in changed C/C++ files
- **💬 Ignores comment lines** - skips `//` and `/* */` style comments
- Looks for `#if WASM_ENABLE_XXX` blocks that enclose non-comment modifications
- Maps detected WASM_ENABLE_* flags to WAMR_BUILD_* using generic rule

### Generic Flag Mapping Rule

**Primary Rule**: `WASM_ENABLE_XYZ` → `WAMR_BUILD_XYZ`

The skill applies this simple transformation first, with special cases handled only when needed:

```python
# Generic mapping (used for all flags)
WASM_ENABLE_SIMD → WAMR_BUILD_SIMD
WASM_ENABLE_BULK_MEMORY → WAMR_BUILD_BULK_MEMORY  
WASM_ENABLE_NEW_FEATURE → WAMR_BUILD_NEW_FEATURE  # Future flags work automatically

# Special cases (only when generic rule doesn't apply)
# Currently: none needed - generic rule covers all known cases
```

### Focused Detection Examples

#### **Direct Detection with Comment Filtering**
```c
// In modified file: core/iwasm/aot/aot_runtime.c
// Diff shows modifications at lines 143, 145, 146

void aot_execute_function() {
#if WASM_ENABLE_BULK_MEMORY    // ← Line 140
+   // This is a comment         // ← Line 143 (IGNORED - comment)
+   bulk_memory_operation();     // ← Line 145 (ANALYZED - code)
+   /* Another comment */        // ← Line 146 (IGNORED - comment)
#endif
}

// Detection result: WASM_ENABLE_BULK_MEMORY → WAMR_BUILD_BULK_MEMORY
// Only line 145 (actual code) triggers flag detection
```

### ⚡ Performance Benefits

**Speed Improvements:**
- **No codebase-wide scanning** - only analyzes modified files
- **No function dependency analysis** - focuses on direct conditional compilation
- **No header file searching** - trusts diff analysis only
- **💬 Comment filtering** - skips comment-only modifications for faster processing
- **Reduced complexity** - single-step detection process

**Reliability:**
- **Generic flag mapping** - works with future WASM_ENABLE_* flags automatically
- **Focused analysis** - detects flags that actually control modified code (not comments)
- **Fast execution** - suitable for CI/CD pipelines with time constraints

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
# Configure (with clang toolchain + compile commands export + detected flags)
cmake -S product-mini/platforms/linux -B ${inter_dir}/build/iwasm \
    -DCMAKE_TOOLCHAIN_FILE=tests/fuzz/wasm-mutator-fuzz/clang_toolchain.cmake \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DWAMR_BUILD_SIMD=1 \
    -DWAMR_BUILD_BULK_MEMORY=1

# Build
cmake --build ${inter_dir}/build/iwasm
```

**Output**:
- Runtime executable in `${inter_dir}/build/iwasm/`
- `compile_commands.json` for IDE integration and static analysis

### wamrc (WebAssembly Compiler)
When `wamr-compiler` modifications are detected:

```bash
# Configure (with clang toolchain + compile commands export + detected flags)
cmake -S wamr-compiler -B ${inter_dir}/build/wamrc \
    -DCMAKE_TOOLCHAIN_FILE=tests/fuzz/wasm-mutator-fuzz/clang_toolchain.cmake \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DWAMR_BUILD_AOT=1

# Build
cmake --build ${inter_dir}/build/wamrc
```

**Output**:
- Compiler executable in `${inter_dir}/build/wamrc/`
- `compile_commands.json` for IDE integration and static analysis

## Clang Compiler Benefits

Using clang/clang++ provides several advantages for WAMR builds:

### **Better Optimization**
- Advanced optimization passes for WebAssembly code generation
- Superior cross-platform compatibility
- Consistent behavior across different host platforms

### **Enhanced Analysis**
- Better static analysis capabilities
- Improved warning messages and error diagnostics
- Support for sanitizers (AddressSanitizer, UndefinedBehaviorSanitizer)

### **Fuzzing Support**
- Built-in fuzzing capabilities with `-fsanitize=fuzzer`
- Integration with WAMR's existing fuzz testing infrastructure
- Better coverage analysis and bug detection

### **Development Tools**
- Excellent integration with clang-tidy static analyzer
- Support for clang-format code formatting
- Compatible with LLVM toolchain ecosystem

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

**🔥 NEW STRICT FAILURE SCENARIOS:**
- **❌ Missing Clang**: Build stops immediately if clang/clang++ not in PATH
- **❌ No Toolchain File**: Build stops immediately if no valid toolchain found

**Traditional failure scenarios:**
- **Invalid repository**: Validates WAMR directory structure
- **Missing CMake**: Clear error if cmake command not found
- **Build failures**: Captures cmake output and error details
- **Permission issues**: Handles directory creation and access errors

### New Strict Error Messages
```
❌ MANDATORY REQUIREMENT FAILED: Clang/clang++ compilers are required but not found in PATH.
   Please install clang and ensure both 'clang' and 'clang++' are available in your system PATH.
   On Ubuntu/Debian: sudo apt install clang
   On CentOS/RHEL: sudo yum install clang  
   On macOS: xcode-select --install

❌ MANDATORY REQUIREMENT FAILED: Clang toolchain file is required but not found.
   Expected locations:
   - tests/fuzz/wasm-mutator-fuzz/clang_toolchain.cmake
   - build-scripts/clang_toolchain.cmake
   - cmake/clang_toolchain.cmake
   - toolchain/clang_toolchain.cmake
```

### Traditional Error Messages
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

## 🔥 STRICT MODE: What Changed

This skill now operates with **ZERO TOLERANCE** for missing requirements:

### ❌ **REMOVED FEATURES:**
- ~~Fallback to system compilers~~ → **MANDATORY clang/clang++**
- ~~Auto-generation of toolchain files~~ → **MANDATORY existing toolchain**
- ~~Graceful degradation~~ → **FAIL FAST on missing requirements**

### ✅ **NEW ENFORCEMENT:**
- **Clang availability check** → Exception thrown if not found
- **Toolchain file existence** → File must exist in expected locations
- **Build reliability** → Guaranteed clang-based builds or immediate failure

### 🎯 **Benefits of Strict Mode:**
- **Consistent builds**: All WAMR builds use identical clang toolchain
- **Early failure detection**: Problems caught before build starts
- **Reproducible results**: Eliminates compiler variation issues
- **CI/CD reliability**: Predictable behavior in automated environments

The skill provides targeted, efficient building of WAMR components based on intelligent modification detection with **guaranteed clang toolchain compliance**, making it ideal for strict CI/CD pipelines and development workflows.
