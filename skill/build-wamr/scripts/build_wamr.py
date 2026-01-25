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


def is_comment_or_empty_line(line_content, line_num, modified_lines):
    """Check if a line is a comment or empty, and if it's in the modified lines"""
    if line_num not in modified_lines:
        return False

    content = line_content.strip()

    # Skip empty lines
    if not content:
        return True

    # Check for C/C++ style comments
    is_comment = (
        content.startswith("//")  # Single-line comment
        or content.startswith("/*")  # Multi-line comment start
        or content.startswith("*")  # Multi-line comment continuation (common style)
        or content.endswith("*/")  # Multi-line comment end
        or content == "/*"
        or content == "*/"  # Standalone comment markers
    )

    return is_comment


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
    # BUT ignore lines that are comments
    for line_num in modified_lines:
        if line_num <= 0 or line_num > len(file_lines):
            continue

        # Skip comment lines - they don't affect compilation flags
        if is_comment_or_empty_line(file_lines[line_num - 1], line_num, modified_lines):
            print(f"    Skipping comment/empty line {line_num}")
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
    """Map WASM_ENABLE_* flags to corresponding WAMR_BUILD_* cmake flags using generic rule first"""

    # Special cases that don't follow the generic WASM_ENABLE_XYZ -> WAMR_BUILD_XYZ rule
    special_mappings = {
        # Add only exceptions to the generic rule here if needed
        # "WASM_ENABLE_SPECIAL_CASE": "WAMR_BUILD_DIFFERENT_NAME",
    }

    wamr_build_flags = set()
    for wasm_flag in wasm_enable_flags:
        # First, check if there's a special mapping
        if wasm_flag in special_mappings:
            wamr_build_flags.add(special_mappings[wasm_flag])
            print(f"Special mapping: {wasm_flag} -> {special_mappings[wasm_flag]}")
        else:
            # Use generic rule: WASM_ENABLE_XYZ -> WAMR_BUILD_XYZ
            generic_flag = wasm_flag.replace("WASM_ENABLE_", "WAMR_BUILD_")
            wamr_build_flags.add(generic_flag)
            print(f"Generic mapping: {wasm_flag} -> {generic_flag}")

    return wamr_build_flags


def detect_compilation_flags(diff_content, repo_path):
    """Detect compilation flags by analyzing modified lines for WASM_ENABLE macros"""
    if not diff_content:
        return set()

    print("\n=== Detecting WASM_ENABLE flags from modified lines ===")

    # Parse diff to find modified files and line numbers
    modified_files = parse_diff_for_modified_lines(diff_content)

    if not modified_files:
        print("No modified C/C++ files found in diff")
        return set()

    all_detected_flags = set()

    # Analyze each modified file for WASM_ENABLE flags around modified lines
    for file_path, line_numbers in modified_files.items():
        if not line_numbers:
            continue

        print(f"  Analyzing {file_path} (modified lines: {line_numbers})")

        # Check for WASM_ENABLE flags that control the modified lines
        file_flags = analyze_file_for_compilation_flags(
            file_path, line_numbers, repo_path
        )

        if file_flags:
            print(f"    Found flags: {', '.join(sorted(file_flags))}")
            all_detected_flags.update(file_flags)

    # Convert detected WASM_ENABLE_* flags to WAMR_BUILD_* flags
    if all_detected_flags:
        wamr_build_flags = map_wasm_enable_to_wamr_build(all_detected_flags)
        print(f"\n✅ Detected WAMR build flags: {', '.join(sorted(wamr_build_flags))}")
        return wamr_build_flags
    else:
        print("\n⚠️  No WASM_ENABLE flags detected for modified lines")
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
