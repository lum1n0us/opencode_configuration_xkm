import pytest
import json
import tempfile
import os
from macro_analyzer.analyzer import PCPPAnalyzer


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
        analyzer = PCPPAnalyzer()

        # Test line 5 (advanced_debug) - DEBUG not defined
        result = analyzer.analyze(test_file, 5)
        assert result["line"] == 5
        # Should show the condition chain even though DEBUG is not defined
        assert result["combined_expression"] == "defined(DEBUG) && (VERSION > 2)"

        # Test line 12 (linux_code) - PLATFORM == "linux" is true
        result = analyzer.analyze(test_file, 12)
        assert result["line"] == 12
        assert "PLATFORM" in result["combined_expression"]
        assert "linux" in result["combined_expression"]

    finally:
        os.unlink(test_file)


def test_header_guard_filtering_integration():
    """Test that header guards are filtered in real file analysis."""
    from macro_analyzer.analyzer import PCPPAnalyzer

    analyzer = PCPPAnalyzer()

    # Analyze header_guard.c
    test_file = "tests/samples/header_guard.c"
    result = analyzer.analyze(test_file, 8)  # Line 8: log_message("Debug")

    # Should have DEBUG but not HEADER_GUARD_H
    assert "defined(DEBUG)" in result["combined_expression"]
    assert "HEADER_GUARD_H" not in result["combined_expression"]

    # Check macros array
    macro_names = [m["name"] for m in result["macros"]]
    assert "DEBUG" in macro_names
    assert "HEADER_GUARD_H" not in macro_names
    assert "VERSION" not in macro_names  # VERSION not in this line's condition

    # Test another line
    result = analyzer.analyze(test_file, 12)  # Line 12: enable_feature()
    assert "VERSION > 1" in result["combined_expression"]
    macro_names = [m["name"] for m in result["macros"]]
    assert "VERSION" in macro_names
    assert "HEADER_GUARD_H" not in macro_names


def test_real_world_example_with_condition_blocks():
    """Test with real-world nested conditional structure."""
    analyzer = PCPPAnalyzer()

    result = analyzer.analyze("tests/samples/real_example.c", 13)

    # Verify all expected fields
    assert "file" in result
    assert "line" in result
    assert "macros" in result
    assert "combined_expression" in result
    assert "condition_blocks" in result

    # Check condition blocks
    condition_blocks = result["condition_blocks"]

    # Note: Inactive branches (else in this case) are NOT included in condition_blocks
    # Only active conditions that control the target line are included
    # So there should be only 1 condition block (the outer if)
    assert len(condition_blocks) == 1

    # Outer block: WASM_ENABLE_GC != 0
    assert condition_blocks[0]["line"] == 6  # Line of #if WASM_ENABLE_GC != 0
    assert "WASM_ENABLE_GC != 0" in condition_blocks[0]["expression"]
    assert condition_blocks[0]["type"] == "if"

    # Check combined expression
    combined = result["combined_expression"]
    assert "WASM_ENABLE_GC != 0" in combined

    # Check macros
    macros = result["macros"]
    macro_names = [m["name"] for m in macros]
    assert "WASM_ENABLE_GC" in macro_names
