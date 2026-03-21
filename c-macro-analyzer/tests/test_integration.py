import pytest
import json
import tempfile
import os
from macro_analyzer.processor import FileProcessor


def test_integration_complex_file():
    # Create complex test file
    test_content = """#define PLATFORM "linux"
#define VERSION 3

#ifdef DEBUG
  #if VERSION > 2
    advanced_debug();
  #endif
#endif

#if PLATFORM == "windows"
  windows_code();
#elif PLATFORM == "linux"
  linux_code();
#else
  other_code();
#endif
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".c", delete=False) as f:
        f.write(test_content)
        test_file = f.name

    try:
        processor = FileProcessor()

        # Test line 5 (advanced_debug) - DEBUG not defined
        result = processor.analyze_file(test_file, 5)
        assert result["line"] == 5
        assert result["combined_expression"] == ""

        # Test line 12 (linux_code) - PLATFORM == "linux" is true
        result = processor.analyze_file(test_file, 12)
        assert result["line"] == 12
        assert "PLATFORM" in result["combined_expression"]
        assert "linux" in result["combined_expression"]

    finally:
        os.unlink(test_file)
