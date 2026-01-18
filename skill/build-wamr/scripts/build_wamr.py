#!/usr/bin/env python3
"""
Build WAMR script - Builds WebAssembly Micro Runtime based on detected modifications
"""

import os
import sys
import subprocess
import argparse
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


def build_iwasm(repo_path, inter_dir):
    """Build iwasm (WebAssembly runtime)"""
    print("\n=== Building iwasm (WebAssembly runtime) ===")

    repo_path = Path(repo_path)
    inter_dir = Path(inter_dir)

    # Create build directory
    build_dir = inter_dir / "build" / "iwasm"
    build_dir.mkdir(parents=True, exist_ok=True)

    # Configure with cmake (including compile commands export)
    source_dir = repo_path / "product-mini" / "platforms" / "linux"
    configure_cmd = (
        f"cmake -S {source_dir} -B {build_dir} -DCMAKE_EXPORT_COMPILE_COMMANDS=ON"
    )
    run_command(configure_cmd)

    # Build with cmake
    build_cmd = f"cmake --build {build_dir}"
    run_command(build_cmd)

    print("✅ iwasm build completed successfully")


def build_wamrc(repo_path, inter_dir):
    """Build wamrc (WebAssembly compiler)"""
    print("\n=== Building wamrc (WebAssembly compiler) ===")

    repo_path = Path(repo_path)
    inter_dir = Path(inter_dir)

    # Create build directory
    build_dir = inter_dir / "build" / "wamrc"
    build_dir.mkdir(parents=True, exist_ok=True)

    # Configure with cmake (including compile commands export)
    source_dir = repo_path / "wamr-compiler"
    configure_cmd = (
        f"cmake -S {source_dir} -B {build_dir} -DCMAKE_EXPORT_COMPILE_COMMANDS=ON"
    )
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

        # Read analysis and diff files if they exist
        print("\n=== Analyzing modifications ===")
        analysis_content = read_analysis_file(inter_dir)
        diff_content = read_changes_diff(inter_dir)

        # Detect what needs to be built
        iwasm_modified, wamrc_modified = detect_modifications(
            analysis_content, diff_content
        )

        # Determine build strategy
        if not iwasm_modified and not wamrc_modified:
            print("No specific modifications detected. Building both iwasm and wamrc.")
            iwasm_modified = True
            wamrc_modified = True

        # Execute builds
        builds_completed = []

        if iwasm_modified:
            build_iwasm(repo_path, inter_dir)
            builds_completed.append("iwasm")

        if wamrc_modified:
            build_wamrc(repo_path, inter_dir)
            builds_completed.append("wamrc")

        # Write success status
        status_file = write_status_report(inter_dir, True)

        print(f"\n✅ WAMR build completed successfully!")
        print(f"   Components built: {', '.join(builds_completed)}")
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
