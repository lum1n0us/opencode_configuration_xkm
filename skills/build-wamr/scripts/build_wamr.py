#!/usr/bin/env python3
"""
Build WAMR script - Builds WebAssembly Micro Runtime components
Focuses purely on build execution with explicit parameters
"""

import os
import sys
import subprocess
import argparse
import tempfile
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


def write_status_report(build_dir, success, error_msg=None):
    """Write status report in specified format"""
    status_file = Path(build_dir) / "build-wamr_status.md"

    if success:
        content = "SUCCESS"
    else:
        content = f"FAIL\n{error_msg}"

    status_file.write_text(content)
    return status_file


def get_current_branch():
    """Get current git branch name, fallback to 'default' if not in git repo"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        branch_name = result.stdout.strip()
        # Sanitize branch name for directory usage
        branch_name = branch_name.replace("/", "-").replace("\\", "-")
        return branch_name
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "default"


def validate_wamr_repository(repo_path):
    """Validate that the repository is a WAMR project"""
    repo_path = Path(repo_path)

    # Check for key WAMR directories/files based on target
    required_paths = [
        repo_path / "core" / "iwasm",  # Always check for core
    ]

    missing_paths = [path for path in required_paths if not path.exists()]

    if missing_paths:
        missing_str = ", ".join(str(p.relative_to(repo_path)) for p in missing_paths)
        raise Exception(
            f"Repository does not appear to be a WAMR project. "
            f"Missing required paths: {missing_str}"
        )

    print("WAMR repository structure validated successfully")


def get_source_directory(repo_path, target):
    """Get source directory based on build target"""
    repo_path = Path(repo_path)

    source_dirs = {
        "iwasm": repo_path / "product-mini" / "platforms" / "linux",
        "wamrc": repo_path / "wamr-compiler",
        "unit-test": repo_path / "tests" / "unit",
    }

    source_dir = source_dirs.get(target)
    if not source_dir:
        raise Exception(
            f"Unknown target: {target}. Valid targets: {', '.join(source_dirs.keys())}"
        )

    if not source_dir.exists():
        raise Exception(
            f"Source directory for target '{target}' not found: {source_dir}"
        )

    return source_dir


def find_clang_toolchain_file(repo_path):
    """Find the clang toolchain file - STRICT: Only build-scripts/clang_toolchain.cmake"""
    repo_path = Path(repo_path)
    toolchain_path = repo_path / "build-scripts" / "clang_toolchain.cmake"

    if toolchain_path.exists():
        print(f"✅ Found clang toolchain file: {toolchain_path.relative_to(repo_path)}")
        return toolchain_path

    return None


def validate_toolchain_file(toolchain_path):
    """Validate that toolchain file exists - simple file path check only"""
    if not toolchain_path or not Path(toolchain_path).exists():
        raise Exception(
            "❌ MANDATORY REQUIREMENT FAILED: build-scripts/clang_toolchain.cmake not found.\n"
            "   This is the exclusive location required for the clang toolchain file.\n"
            "   Please ensure clang_toolchain.cmake exists at: build-scripts/clang_toolchain.cmake"
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


def build_target(repo_path, target, build_dir, cmake_options, toolchain_file):
    """Build the specified target"""
    print(f"\n=== Building {target} ===")

    repo_path = Path(repo_path)
    build_dir = Path(build_dir)

    # Get source directory for target
    source_dir = get_source_directory(repo_path, target)

    # Create target-specific build directory
    target_build_dir = build_dir / target
    target_build_dir.mkdir(parents=True, exist_ok=True)

    # Configure with cmake (always include compile commands export)
    configure_cmd = (
        f"cmake -S {source_dir} -B {target_build_dir} "
        f"-DCMAKE_EXPORT_COMPILE_COMMANDS=ON"
    )

    # Add clang toolchain
    if toolchain_file:
        configure_cmd += f" -DCMAKE_TOOLCHAIN_FILE={toolchain_file}"
        print(f"Using clang toolchain: {toolchain_file}")

    # Add any additional cmake options
    if cmake_options:
        configure_cmd += f" {' '.join(cmake_options)}"
        print(f"Applying cmake options: {' '.join(cmake_options)}")

    run_command(configure_cmd)

    # Build with cmake
    build_cmd = f"cmake --build {target_build_dir}"
    run_command(build_cmd)

    print(f"✅ {target} build completed successfully")
    return target_build_dir


def main():
    parser = argparse.ArgumentParser(
        description="Build WAMR (WebAssembly Micro Runtime) components with explicit parameters",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build iwasm (default) with JIT support
  python build_wamr.py --repo_path /path/to/wamr -DWAMR_BUILD_JIT=1

  # Build wamrc in specific directory
  python build_wamr.py --target wamrc --build_dir /tmp/my_build

  # Build unit tests with multiple flags
  python build_wamr.py --target unit-test -DWAMR_BUILD_AOT=1 -DWAMR_BUILD_SIMD=1
        """,
    )

    parser.add_argument(
        "--repo_path",
        default=".",
        help="Path to WAMR git repository (default: current directory)",
    )

    parser.add_argument(
        "--target",
        choices=["iwasm", "wamrc", "unit-test"],
        default="iwasm",
        help="Build target (default: iwasm)",
    )

    parser.add_argument(
        "--build_dir",
        help="Build directory (default: build-<branch-name> in current directory)",
    )

    # Allow arbitrary cmake options to be passed through
    parser.add_argument(
        "cmake_options",
        nargs="*",
        help="Additional cmake options (e.g., -DWAMR_BUILD_JIT=1 -DWAMR_BUILD_AOT=1)",
    )

    args = parser.parse_args()

    # Initialize build_dir early to avoid unbound variable issues
    build_dir = None

    try:
        repo_path = Path(args.repo_path).resolve()

        # Determine build directory
        if args.build_dir:
            build_dir = Path(args.build_dir).resolve()
        else:
            branch_name = get_current_branch()
            build_dir = Path.cwd() / f"build-{branch_name}"

        # Ensure build_dir exists
        build_dir.mkdir(parents=True, exist_ok=True)

        print(f"Building WAMR from repository: {repo_path}")
        print(f"Target: {args.target}")
        print(f"Build directory: {build_dir}")

        # Validate WAMR repository structure
        validate_wamr_repository(repo_path)

        # STRICT: Enforce mandatory clang availability
        print("\n=== Enforcing strict clang requirements ===")
        check_clang_availability()

        # STRICT: Enforce mandatory toolchain file with validation
        toolchain_file = find_and_validate_clang_toolchain(repo_path)

        # Execute build
        target_build_dir = build_target(
            repo_path, args.target, build_dir, args.cmake_options, toolchain_file
        )

        # Write success status
        status_file = write_status_report(build_dir, True)

        print(
            f"\n🔥 WAMR {args.target} build completed successfully with STRICT clang requirements!"
        )
        if args.cmake_options:
            print(f"   CMake options applied: {' '.join(args.cmake_options)}")
        toolchain_name = Path(toolchain_file).name
        print(f"   ✅ VALIDATED clang toolchain: {toolchain_name}")
        print(f"   Status: {status_file}")
        print(f"   Build output: {target_build_dir}")

    except Exception as e:
        # Try to write status file if build_dir was determined
        try:
            if "build_dir" in locals() and build_dir:
                build_dir.mkdir(parents=True, exist_ok=True)
                status_file = write_status_report(build_dir, False, str(e))
                print(f"\n❌ WAMR build failed: {e}")
                print(f"   Status: {status_file}")
            else:
                print(f"\n❌ WAMR build failed: {e}")
        except Exception:
            # If status file writing fails, just print the error
            print(f"\n❌ WAMR build failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
