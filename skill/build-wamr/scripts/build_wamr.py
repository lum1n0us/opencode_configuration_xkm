#!/usr/bin/env python3
"""
Build WAMR script - Builds WebAssembly Micro Runtime based on detected modifications
"""

import os
import sys
import subprocess
import argparse
import re
from pathlib import Path
from datetime import datetime


def run_command(cmd, cwd=None):
    """Run a shell command and return the result"""
    try:
        print(f"Running: {cmd}")
        if cwd:
            print(f"Working directory: {cwd}")

        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )

        if result.stdout:
            print("Output:", result.stdout)

        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        error_msg = f"Command failed: {cmd}\nReturn code: {e.returncode}"
        if e.stdout:
            error_msg += f"\nStdout: {e.stdout}"
        if e.stderr:
            error_msg += f"\nStderr: {e.stderr}"
        raise Exception(error_msg)


def write_status_report(inter_dir, success, error_msg=None):
    """Write status report in specified format"""
    status_file = Path(inter_dir) / "build-wamr_status.md"

    if success:
        content = "SUCCESS"
    else:
        content = f"FAIL\n{error_msg}"

    status_file.write_text(content)
    return status_file


def read_analysis_file(inter_dir):
    """Read and analyze analysis.md file if it exists"""
    analysis_file = Path(inter_dir) / "analysis.md"

    if not analysis_file.exists():
        return None

    try:
        content = analysis_file.read_text()
        return content
    except Exception as e:
        print(f"Warning: Could not read analysis.md: {e}")
        return None


def read_changes_diff(inter_dir):
    """Read and analyze changes.diff file if it exists"""
    diff_file = Path(inter_dir) / "changes.diff"

    if not diff_file.exists():
        return None

    try:
        content = diff_file.read_text()
        return content
    except Exception as e:
        print(f"Warning: Could not read changes.diff: {e}")
        return None


def parse_diff_for_modified_lines(diff_content):
    """Parse diff content to extract modified files and their line numbers"""
    if not diff_content:
        return {}

    modified_files = {}
    current_file = None
    current_line_num = 0

    lines = diff_content.split("\n")

    for line in lines:
        # Match file headers like "diff --git a/path/file.c b/path/file.c"
        if line.startswith("diff --git"):
            match = re.search(r"diff --git a/(.*?) b/", line)
            if match:
                current_file = match.group(1)
                modified_files[current_file] = []

        # Match chunk headers like "@@ -123,7 +123,8 @@"
        elif line.startswith("@@"):
            match = re.search(r"@@ -\d+,?\d* \+(\d+),?\d* @@", line)
            if match:
                current_line_num = int(match.group(1))

        # Track added/modified lines (starting with '+' but not '+++')
        elif line.startswith("+") and not line.startswith("+++") and current_file:
            modified_files[current_file].append(current_line_num)
            current_line_num += 1

        # Track unchanged lines to maintain line numbering
        elif (
            not line.startswith("-")
            and not line.startswith("\\")
            and current_file
            and current_line_num > 0
        ):
            current_line_num += 1

    # Filter out files that aren't C/C++ source files
    c_cpp_files = {}
    for file_path, line_nums in modified_files.items():
        if file_path.endswith((".c", ".h", ".cc", ".cpp", ".cxx")):
            c_cpp_files[file_path] = line_nums

    return c_cpp_files


def analyze_file_for_compilation_flags(file_path, modified_lines, repo_path):
    """Analyze a file to detect compilation flags needed for modified lines"""
    full_path = Path(repo_path) / file_path
    if not full_path.exists():
        print(f"Warning: File {file_path} not found, skipping flag analysis")
        return set()

    try:
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            file_lines = f.readlines()
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}")
        return set()

    detected_flags = set()

    # For each modified line, check if it's within conditional compilation blocks
    for line_num in modified_lines:
        if line_num <= 0 or line_num > len(file_lines):
            continue

        # Search backwards and forwards from the modified line to find enclosing #if blocks
        flags_for_line = find_enclosing_compilation_flags(
            file_lines, line_num - 1
        )  # Convert to 0-based
        detected_flags.update(flags_for_line)

    return detected_flags


def find_enclosing_compilation_flags(file_lines, target_line_idx):
    """Find all WASM_ENABLE_* flags that enclose the target line"""
    flags = set()

    # Stack to track nested #if blocks
    if_stack = []

    # Scan from beginning of file to target line
    for i in range(target_line_idx + 1):
        line = file_lines[i].strip()

        # Check for #if WASM_ENABLE_* or #ifdef WASM_ENABLE_*
        if_match = re.match(r"#if(?:def)?\s+.*?(WASM_ENABLE_\w+)", line)
        if if_match:
            flag_name = if_match.group(1)
            if_stack.append(flag_name)
            continue

        # Check for #elif WASM_ENABLE_*
        elif_match = re.match(r"#elif\s+.*?(WASM_ENABLE_\w+)", line)
        if elif_match:
            # Pop the last condition and push new one
            if if_stack:
                if_stack.pop()
            flag_name = elif_match.group(1)
            if_stack.append(flag_name)
            continue

        # Check for #else (changes the condition)
        if line.startswith("#else"):
            if if_stack:
                # For #else, we're in the "not" condition, so we don't add the flag
                # But we keep the flag on stack to match with #endif
                pass
            continue

        # Check for #endif
        if line.startswith("#endif"):
            if if_stack:
                if_stack.pop()
            continue

    # All flags currently on the stack are enclosing our target line
    flags.update(if_stack)

    return flags


def map_wasm_enable_to_wamr_build(wasm_enable_flags):
    """Map WASM_ENABLE_* flags to corresponding WAMR_BUILD_* cmake flags"""
    flag_mapping = {
        "WASM_ENABLE_INTERP": "WAMR_BUILD_INTERP",
        "WASM_ENABLE_AOT": "WAMR_BUILD_AOT",
        "WASM_ENABLE_JIT": "WAMR_BUILD_JIT",
        "WASM_ENABLE_LIBC_BUILTIN": "WAMR_BUILD_LIBC_BUILTIN",
        "WASM_ENABLE_LIBC_WASI": "WAMR_BUILD_LIBC_WASI",
        "WASM_ENABLE_LIBC_EMCC": "WAMR_BUILD_LIBC_EMCC",
        "WASM_ENABLE_MULTI_MODULE": "WAMR_BUILD_MULTI_MODULE",
        "WASM_ENABLE_THREAD_MGR": "WAMR_BUILD_THREAD_MGR",
        "WASM_ENABLE_LIB_PTHREAD": "WAMR_BUILD_LIB_PTHREAD",
        "WASM_ENABLE_SHARED_MEMORY": "WAMR_BUILD_SHARED_MEMORY",
        "WASM_ENABLE_BULK_MEMORY": "WAMR_BUILD_BULK_MEMORY",
        "WASM_ENABLE_REF_TYPES": "WAMR_BUILD_REF_TYPES",
        "WASM_ENABLE_SIMD": "WAMR_BUILD_SIMD",
        "WASM_ENABLE_STRINGREF": "WAMR_BUILD_STRINGREF",
        "WASM_ENABLE_GC": "WAMR_BUILD_GC",
        "WASM_ENABLE_CUSTOM_SECTION": "WAMR_BUILD_CUSTOM_SECTION",
        "WASM_ENABLE_TAIL_CALL": "WAMR_BUILD_TAIL_CALL",
        "WASM_ENABLE_TAGS": "WAMR_BUILD_TAGS",
        "WASM_ENABLE_MINI_LOADER": "WAMR_BUILD_MINI_LOADER",
        "WASM_ENABLE_MEMORY_PROFILING": "WAMR_BUILD_MEMORY_PROFILING",
        "WASM_ENABLE_PERF_PROFILING": "WAMR_BUILD_PERF_PROFILING",
        "WASM_ENABLE_DUMP_CALL_STACK": "WAMR_BUILD_DUMP_CALL_STACK",
        "WASM_ENABLE_FAST_INTERP": "WAMR_BUILD_FAST_INTERP",
        "WASM_ENABLE_SPEC_TEST": "WAMR_BUILD_SPEC_TEST",
    }

    wamr_build_flags = set()
    for wasm_flag in wasm_enable_flags:
        if wasm_flag in flag_mapping:
            wamr_build_flags.add(flag_mapping[wasm_flag])
        else:
            # For unknown flags, try a generic mapping
            generic_flag = wasm_flag.replace("WASM_ENABLE_", "WAMR_BUILD_")
            wamr_build_flags.add(generic_flag)
            print(f"Warning: Using generic mapping {wasm_flag} -> {generic_flag}")

    return wamr_build_flags


def find_all_wasm_enable_flags_in_codebase(repo_path):
    """Scan entire codebase to find all WASM_ENABLE_* flags and their usage patterns"""
    repo_path = Path(repo_path)

    print("Scanning entire codebase for WASM_ENABLE flags...")

    # Find all C/C++ source and header files
    source_patterns = ["**/*.c", "**/*.h", "**/*.cc", "**/*.cpp", "**/*.cxx"]
    all_source_files = []

    for pattern in source_patterns:
        all_source_files.extend(repo_path.glob(pattern))

    # Dictionary to store flag -> list of (file, line_num, context) mappings
    flag_usage_map = {}
    flag_definitions = {}

    print(f"Found {len(all_source_files)} source files to analyze")

    for file_path in all_source_files:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                line_stripped = line.strip()

                # Look for WASM_ENABLE flags in various contexts
                wasm_flags = re.findall(r"WASM_ENABLE_\w+", line)

                for flag in wasm_flags:
                    relative_path = file_path.relative_to(repo_path)

                    if flag not in flag_usage_map:
                        flag_usage_map[flag] = []

                    # Determine the type of usage
                    usage_type = determine_flag_usage_type(line_stripped, flag)

                    flag_usage_map[flag].append(
                        {
                            "file": str(relative_path),
                            "line": line_num,
                            "context": line_stripped,
                            "usage_type": usage_type,
                        }
                    )

                    # Track definitions separately
                    if usage_type == "definition":
                        flag_definitions[flag] = {
                            "file": str(relative_path),
                            "line": line_num,
                            "context": line_stripped,
                        }

        except Exception as e:
            # Skip files that can't be read
            continue

    return flag_usage_map, flag_definitions


def determine_flag_usage_type(line, flag):
    """Determine how a WASM_ENABLE flag is being used in a line"""
    line_lower = line.lower()

    if re.match(r"#\s*define\s+" + flag, line):
        return "definition"
    elif re.match(r"#\s*if(?:n?def)?\s+", line):
        return "conditional"
    elif re.match(r"#\s*elif\s+", line):
        return "conditional"
    elif "cmake" in line_lower or "option(" in line_lower:
        return "cmake_option"
    elif line.startswith("//") or line.startswith("/*"):
        return "comment"
    else:
        return "usage"


def analyze_modified_functions_dependencies(diff_content, repo_path):
    """Analyze modified functions and find what flags might affect them"""
    if not diff_content:
        return set()

    print("\n=== Analyzing function dependencies for WASM_ENABLE flags ===")

    # Extract function names from diff
    modified_functions = extract_function_names_from_diff(diff_content)

    if not modified_functions:
        print("No function modifications detected in diff")
        return set()

    print(f"Found modified functions: {', '.join(modified_functions)}")

    # Search codebase for usage of these functions within conditional blocks
    dependent_flags = set()
    flag_usage_map, _ = find_all_wasm_enable_flags_in_codebase(repo_path)

    # For each WASM_ENABLE flag, check if it conditionally compiles code that uses our functions
    for flag, usages in flag_usage_map.items():
        for usage in usages:
            if usage["usage_type"] == "conditional":
                # Check if any modified functions are used within this conditional block
                if check_functions_in_conditional_block(
                    usage["file"], usage["line"], modified_functions, repo_path
                ):
                    dependent_flags.add(flag)
                    print(
                        f"  Found dependency: {flag} in {usage['file']}:{usage['line']}"
                    )

    return dependent_flags


def extract_function_names_from_diff(diff_content):
    """Extract function names that were modified in the diff"""
    function_names = set()
    lines = diff_content.split("\n")

    for line in lines:
        # Look for function definitions in added/modified lines
        if line.startswith("+") and not line.startswith("+++"):
            # Match C function definitions: type name(...) or name(...)
            func_matches = re.findall(r"\b([a-zA-Z_]\w*)\s*\(", line)
            for match in func_matches:
                # Filter out common keywords and macros
                if match not in [
                    "if",
                    "for",
                    "while",
                    "switch",
                    "return",
                    "sizeof",
                    "typeof",
                    "printf",
                    "malloc",
                    "free",
                ]:
                    function_names.add(match)

    return function_names


def check_functions_in_conditional_block(
    file_path, conditional_line, function_names, repo_path
):
    """Check if any of the function names appear within a conditional block"""
    full_path = Path(repo_path) / file_path

    if not full_path.exists():
        return False

    try:
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except:
        return False

    # Find the matching #endif for the conditional at conditional_line
    if conditional_line <= 0 or conditional_line > len(lines):
        return False

    # Start from the conditional line and find the matching endif
    if_stack = 0
    start_line = conditional_line - 1  # Convert to 0-based

    for i in range(start_line, len(lines)):
        line = lines[i].strip()

        if re.match(r"#\s*if", line):
            if_stack += 1
        elif line.startswith("#endif"):
            if_stack -= 1
            if if_stack == 0:
                # This is our matching endif, check the block
                block_content = "\n".join(lines[start_line : i + 1])

                # Check if any of our modified functions appear in this block
                for func_name in function_names:
                    if re.search(r"\b" + re.escape(func_name) + r"\b", block_content):
                        return True
                break

    return False


def search_for_flag_patterns_around_files(modified_files, repo_path):
    """Search for WASM_ENABLE patterns in files related to the modified files"""
    related_flags = set()

    print("\n=== Searching for WASM_ENABLE patterns in related files ===")

    for file_path in modified_files.keys():
        # Get directory of the modified file
        file_dir = Path(file_path).parent

        # Search in the same directory and parent directories for relevant patterns
        search_dirs = [file_dir]

        # Add parent directories (up to 2 levels)
        current_dir = file_dir
        for _ in range(2):
            current_dir = current_dir.parent
            if str(current_dir) != ".":
                search_dirs.append(current_dir)

        # Search for header files and CMake files in these directories
        for search_dir in search_dirs:
            full_search_path = Path(repo_path) / search_dir
            if not full_search_path.exists():
                continue

            # Search for relevant files
            patterns = ["*.h", "*.hpp", "CMakeLists.txt", "*.cmake", "*.in"]

            for pattern in patterns:
                for found_file in full_search_path.glob(pattern):
                    flags = extract_flags_from_file(found_file)
                    if flags:
                        relative_path = found_file.relative_to(Path(repo_path))
                        print(f"  Found flags in {relative_path}: {', '.join(flags)}")
                        related_flags.update(flags)

    return related_flags


def extract_flags_from_file(file_path):
    """Extract WASM_ENABLE flags from a single file"""
    flags = set()

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Find all WASM_ENABLE patterns
        wasm_flags = re.findall(r"WASM_ENABLE_\w+", content)
        flags.update(wasm_flags)

    except:
        pass

    return flags


def detect_compilation_flags(diff_content, repo_path):
    """Detect compilation flags needed based on comprehensive codebase analysis"""
    if not diff_content:
        return set()

    print("\n=== Detecting compilation flags with enhanced codebase analysis ===")

    all_detected_flags = set()

    # Method 1: Original diff-based analysis (for direct conditional compilation)
    print("Step 1: Analyzing modified lines in diff...")
    modified_files = parse_diff_for_modified_lines(diff_content)

    if modified_files:
        for file_path, line_numbers in modified_files.items():
            if not line_numbers:
                continue

            print(f"  Analyzing {file_path} (modified lines: {line_numbers})")

            # Analyze each file for compilation flags
            file_flags = analyze_file_for_compilation_flags(
                file_path, line_numbers, repo_path
            )

            if file_flags:
                print(f"    Direct flags: {', '.join(sorted(file_flags))}")
                all_detected_flags.update(file_flags)

    # Method 2: Search for patterns in related files (headers, CMake files)
    print("Step 2: Searching for WASM_ENABLE patterns in related files...")
    if modified_files:
        related_flags = search_for_flag_patterns_around_files(modified_files, repo_path)
        if related_flags:
            print(f"  Related file flags: {', '.join(sorted(related_flags))}")
            all_detected_flags.update(related_flags)

    # Method 3: Analyze function dependencies (modified functions used in conditional code)
    print("Step 3: Analyzing function dependencies...")
    function_dependent_flags = analyze_modified_functions_dependencies(
        diff_content, repo_path
    )
    if function_dependent_flags:
        print(
            f"  Function dependency flags: {', '.join(sorted(function_dependent_flags))}"
        )
        all_detected_flags.update(function_dependent_flags)

    # Method 4: Global codebase scan for commonly used flags (fallback/verification)
    print("Step 4: Performing global codebase verification...")
    global_flags, global_definitions = find_all_wasm_enable_flags_in_codebase(repo_path)

    # Filter global flags to only include those that are likely relevant
    relevant_global_flags = set()
    for flag in global_flags:
        # Include flags that have conditional usage (not just definitions/comments)
        conditional_usages = [
            usage
            for usage in global_flags[flag]
            if usage["usage_type"] in ["conditional", "usage"]
        ]
        if conditional_usages:
            relevant_global_flags.add(flag)

    # Report all available flags for reference
    if relevant_global_flags:
        print(
            f"  Available WASM_ENABLE flags in codebase: {len(relevant_global_flags)}"
        )
        print(f"    Most common: {', '.join(sorted(list(relevant_global_flags)[:10]))}")

    # Convert all detected WASM_ENABLE_* flags to WAMR_BUILD_* flags
    if all_detected_flags:
        wamr_build_flags = map_wasm_enable_to_wamr_build(all_detected_flags)
        print(
            f"\n✅ Final detected WAMR build flags: {', '.join(sorted(wamr_build_flags))}"
        )

        # Show detection summary
        print("Detection summary:")
        for flag in sorted(all_detected_flags):
            wamr_flag = flag.replace("WASM_ENABLE_", "WAMR_BUILD_")
            print(f"  {flag} → {wamr_flag}")

        return wamr_build_flags
    else:
        print("\n⚠️  No specific WASM_ENABLE flags detected")
        print("   Build will use default configuration")
        return set()


def validate_wamr_repository(repo_path):
    """Validate that the repository is a WAMR project"""
    repo_path = Path(repo_path)

    # Check for key WAMR directories/files
    required_paths = [
        repo_path / "core" / "iwasm",
        repo_path / "wamr-compiler",
        repo_path / "product-mini" / "platforms" / "linux",
    ]

    missing_paths = [path for path in required_paths if not path.exists()]

    if missing_paths:
        missing_str = ", ".join(str(p.relative_to(repo_path)) for p in missing_paths)
        raise Exception(
            f"Repository does not appear to be a WAMR project. "
            f"Missing required paths: {missing_str}"
        )

    print("WAMR repository structure validated successfully")


def detect_modifications(analysis_content, diff_content):
    """Detect what components were modified based on analysis and diff content"""
    iwasm_modified = False
    wamrc_modified = False

    # Check analysis.md for classification information
    if analysis_content:
        # Look for core/iwasm related modifications
        if any(
            keyword in analysis_content.lower()
            for keyword in ["core/iwasm", "iwasm", "core components", "runtime"]
        ):
            iwasm_modified = True
            print("Detected iwasm modifications from analysis.md")

        # Look for wamr-compiler related modifications
        if any(
            keyword in analysis_content.lower()
            for keyword in ["wamr-compiler", "wamrc", "compiler"]
        ):
            wamrc_modified = True
            print("Detected wamr-compiler modifications from analysis.md")

    # Check changes.diff for file paths
    if diff_content:
        # Look for core/iwasm file modifications
        if any(path in diff_content for path in ["core/iwasm", "core\\iwasm"]):
            iwasm_modified = True
            print("Detected core/iwasm file changes in diff")

        # Look for wamr-compiler file modifications
        if any(path in diff_content for path in ["wamr-compiler", "wamr_compiler"]):
            wamrc_modified = True
            print("Detected wamr-compiler file changes in diff")

    return iwasm_modified, wamrc_modified


def find_clang_toolchain_file(repo_path):
    """Find the clang toolchain file in the WAMR repository"""
    repo_path = Path(repo_path)

    # Look for the specific toolchain file mentioned
    toolchain_locations = [
        repo_path / "tests" / "fuzz" / "wasm-mutator-fuzz" / "clang_toolchain.cmake",
        repo_path / "build-scripts" / "clang_toolchain.cmake",
        repo_path / "cmake" / "clang_toolchain.cmake",
        repo_path / "toolchain" / "clang_toolchain.cmake",
    ]

    for toolchain_path in toolchain_locations:
        if toolchain_path.exists():
            print(
                f"Found clang toolchain file: {toolchain_path.relative_to(repo_path)}"
            )
            return toolchain_path

    # Search more broadly for any clang toolchain files
    for pattern in ["**/clang_toolchain.cmake", "**/*clang*.cmake"]:
        for found_file in repo_path.glob(pattern):
            if (
                "clang" in found_file.name.lower()
                and "toolchain" in found_file.name.lower()
            ):
                print(
                    f"Found alternative clang toolchain: {found_file.relative_to(repo_path)}"
                )
                return found_file

    return None


def validate_toolchain_file(toolchain_path):
    """Validate that toolchain file exists - simple file path check only"""
    if not toolchain_path or not Path(toolchain_path).exists():
        raise Exception(
            "❌ MANDATORY REQUIREMENT FAILED: Clang toolchain file is required but not found.\n"
            "   Expected locations:\n"
            "   - tests/fuzz/wasm-mutator-fuzz/clang_toolchain.cmake\n"
            "   - build-scripts/clang_toolchain.cmake\n"
            "   - cmake/clang_toolchain.cmake\n"
            "   - toolchain/clang_toolchain.cmake\n"
            "   Please ensure a valid clang toolchain file exists in one of these locations."
        )

    print(f"✅ Toolchain file found: {Path(toolchain_path).name}")
    return toolchain_path


def find_and_validate_clang_toolchain(repo_path):
    """Find clang toolchain file and perform simple validation (file existence only)"""
    print("\n=== Locating clang toolchain ===")

    # Find toolchain file
    toolchain_file = find_clang_toolchain_file(repo_path)

    # Validate it exists
    validated_toolchain = validate_toolchain_file(toolchain_file)

    return validated_toolchain


def check_clang_availability():
    """Check if clang/clang++ compilers are available - MANDATORY REQUIREMENT"""
    try:
        # Check clang
        result = subprocess.run(
            ["clang", "--version"], capture_output=True, text=True, check=True
        )
        clang_version = result.stdout.split("\n")[0]

        # Check clang++
        result = subprocess.run(
            ["clang++", "--version"], capture_output=True, text=True, check=True
        )
        clangpp_version = result.stdout.split("\n")[0]

        print(f"✅ Clang compiler available: {clang_version}")
        print(f"✅ Clang++ compiler available: {clangpp_version}")
        return True

    except (subprocess.CalledProcessError, FileNotFoundError):
        raise Exception(
            "❌ MANDATORY REQUIREMENT FAILED: Clang/clang++ compilers are required but not found in PATH.\n"
            "   Please install clang and ensure both 'clang' and 'clang++' are available in your system PATH.\n"
            "   On Ubuntu/Debian: sudo apt install clang\n"
            "   On CentOS/RHEL: sudo yum install clang\n"
            "   On macOS: xcode-select --install"
        )


def build_iwasm(repo_path, inter_dir, compilation_flags=None, toolchain_file=None):
    """Build iwasm (WebAssembly runtime)"""
    print("\n=== Building iwasm (WebAssembly runtime) ===")

    repo_path = Path(repo_path)
    inter_dir = Path(inter_dir)

    # Create build directory
    build_dir = inter_dir / "build" / "iwasm"
    build_dir.mkdir(parents=True, exist_ok=True)

    # Configure with cmake (including compile commands export and detected flags)
    source_dir = repo_path / "product-mini" / "platforms" / "linux"
    configure_cmd = (
        f"cmake -S {source_dir} -B {build_dir} -DCMAKE_EXPORT_COMPILE_COMMANDS=ON"
    )

    # Add clang toolchain if available
    if toolchain_file:
        configure_cmd += f" -DCMAKE_TOOLCHAIN_FILE={toolchain_file}"
        print(f"Using clang toolchain: {toolchain_file}")

    # Add detected compilation flags
    if compilation_flags:
        flag_args = " ".join(f"-D{flag}=1" for flag in compilation_flags)
        configure_cmd += f" {flag_args}"
        print(f"Applying compilation flags: {flag_args}")

    run_command(configure_cmd)

    # Build with cmake
    build_cmd = f"cmake --build {build_dir}"
    run_command(build_cmd)

    print("✅ iwasm build completed successfully")


def build_wamrc(repo_path, inter_dir, compilation_flags=None, toolchain_file=None):
    """Build wamrc (WebAssembly compiler)"""
    print("\n=== Building wamrc (WebAssembly compiler) ===")

    repo_path = Path(repo_path)
    inter_dir = Path(inter_dir)

    # Create build directory
    build_dir = inter_dir / "build" / "wamrc"
    build_dir.mkdir(parents=True, exist_ok=True)

    # Configure with cmake (including compile commands export and detected flags)
    source_dir = repo_path / "wamr-compiler"
    configure_cmd = (
        f"cmake -S {source_dir} -B {build_dir} -DCMAKE_EXPORT_COMPILE_COMMANDS=ON"
    )

    # Add clang toolchain if available
    if toolchain_file:
        configure_cmd += f" -DCMAKE_TOOLCHAIN_FILE={toolchain_file}"
        print(f"Using clang toolchain: {toolchain_file}")

    # Add detected compilation flags
    if compilation_flags:
        flag_args = " ".join(f"-D{flag}=1" for flag in compilation_flags)
        configure_cmd += f" {flag_args}"
        print(f"Applying compilation flags: {flag_args}")

    run_command(configure_cmd)

    # Build with cmake
    build_cmd = f"cmake --build {build_dir}"
    run_command(build_cmd)

    print("✅ wamrc build completed successfully")


def main():
    parser = argparse.ArgumentParser(
        description="Build WAMR (WebAssembly Micro Runtime) components based on detected modifications"
    )
    parser.add_argument(
        "inter_dir", help="Directory containing temporary files and build outputs"
    )
    parser.add_argument(
        "--repo_path",
        default=".",
        help="Path to WAMR git repository (default: current directory)",
    )

    args = parser.parse_args()

    # Ensure inter_dir exists
    inter_dir = Path(args.inter_dir)
    inter_dir.mkdir(parents=True, exist_ok=True)

    try:
        repo_path = Path(args.repo_path).resolve()

        print(f"Building WAMR from repository: {repo_path}")
        print(f"Output directory: {inter_dir}")

        # Validate WAMR repository structure
        validate_wamr_repository(repo_path)

        # STRICT: Enforce mandatory clang availability
        print("\n=== Enforcing strict clang requirements ===")
        check_clang_availability()  # This now throws exception if clang not available

        # STRICT: Enforce mandatory toolchain file with validation
        toolchain_file = find_and_validate_clang_toolchain(
            repo_path
        )  # This throws exception if no valid toolchain

        # Read analysis and diff files if they exist
        print("\n=== Analyzing modifications ===")
        analysis_content = read_analysis_file(inter_dir)
        diff_content = read_changes_diff(inter_dir)

        # Detect compilation flags needed for modified lines
        compilation_flags = detect_compilation_flags(diff_content, repo_path)

        # Detect what needs to be built
        iwasm_modified, wamrc_modified = detect_modifications(
            analysis_content, diff_content
        )

        # Determine build strategy
        if not iwasm_modified and not wamrc_modified:
            print("No specific modifications detected. Building both iwasm and wamrc.")
            iwasm_modified = True
            wamrc_modified = True

        # Execute builds with detected compilation flags and clang toolchain
        builds_completed = []

        if iwasm_modified:
            build_iwasm(repo_path, inter_dir, compilation_flags, toolchain_file)
            builds_completed.append("iwasm")

        if wamrc_modified:
            build_wamrc(repo_path, inter_dir, compilation_flags, toolchain_file)
            builds_completed.append("wamrc")

        # Write success status
        status_file = write_status_report(inter_dir, True)

        print(f"\n🔥 WAMR build completed successfully with STRICT clang requirements!")
        print(f"   Components built: {', '.join(builds_completed)}")
        if compilation_flags:
            print(
                f"   Compilation flags applied: {', '.join(sorted(compilation_flags))}"
            )
        # Toolchain is now always present due to strict validation
        toolchain_name = Path(toolchain_file).name
        print(f"   ✅ VALIDATED clang toolchain: {toolchain_name}")
        print(f"   Status: {status_file}")
        print(f"   Build outputs in: {inter_dir / 'build'}")

    except Exception as e:
        # Write failure status
        status_file = write_status_report(inter_dir, False, str(e))
        print(f"\n❌ WAMR build failed: {e}")
        print(f"   Status: {status_file}")
        sys.exit(1)


if __name__ == "__main__":
    main()
