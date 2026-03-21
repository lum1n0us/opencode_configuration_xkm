import pytest
import subprocess
import json
import tempfile
import os


def test_cli_basic_usage():
    # Create a simple test file
    test_content = """#define DEBUG
#ifdef DEBUG
  test_function();
#endif
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".c", delete=False) as f:
        f.write(test_content)
        test_file = f.name

    try:
        # Run CLI on line 3
        result = subprocess.run(
            ["python", "-m", "macro_analyzer", test_file, "3"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

        # Parse JSON output
        output = json.loads(result.stdout)
        assert output["file"] == test_file
        assert output["line"] == 3
        assert "DEBUG" in output["combined_expression"]
    finally:
        os.unlink(test_file)


def test_cli_missing_file():
    result = subprocess.run(
        ["python", "-m", "macro_analyzer", "nonexistent.c", "1"],
        capture_output=True,
        text=True,
    )
    # CLI should return non-zero exit code for file not found
    # Note: stderr contains error message
    print(f"Return code: {result.returncode}")
    print(f"Stderr: {result.stderr}")
    assert result.returncode != 0
    assert "error" in result.stderr.lower() or "not found" in result.stderr.lower()
