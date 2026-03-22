import os
import tempfile
import pytest
from macro_analyzer.analyzer import PCPPAnalyzer


def test_condition_context_tracking():
    """Test that condition contexts are tracked per line."""
    analyzer = PCPPAnalyzer()

    # Test nested conditions - no leading empty line to keep line numbers correct
    code = """#define FOO 1
#define BAR 0
#if FOO == 1
#if BAR == 0
int x = 42;
#endif
#endif
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".c", delete=False) as f:
        f.write(code)
        filepath = f.name

    try:
        result = analyzer.analyze(filepath, 5)

        # Verify condition_blocks field exists
        assert "condition_blocks" in result
        condition_blocks = result["condition_blocks"]

        # Should have 2 condition blocks
        assert len(condition_blocks) == 2

        # First block: FOO == 1 at line 3
        assert condition_blocks[0]["line"] == 3
        assert condition_blocks[0]["expression"] == "FOO == 1"
        assert condition_blocks[0]["type"] == "if"

        # Second block: BAR == 0 at line 4 (nested)
        assert condition_blocks[1]["line"] == 4
        assert condition_blocks[1]["expression"] == "BAR == 0"
        assert condition_blocks[1]["type"] == "if"

    finally:
        os.unlink(filepath)


def test_condition_blocks_with_elif_else():
    """Test condition blocks with elif and else branches."""
    analyzer = PCPPAnalyzer()

    code = """#define DEBUG 1
#if DEBUG == 1
int x = 1;
#elif DEBUG == 2
int x = 2;
#else
int x = 3;
#endif
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".c", delete=False) as f:
        f.write(code)
        filepath = f.name

    try:
        result = analyzer.analyze(filepath, 3)

        assert "condition_blocks" in result
        condition_blocks = result["condition_blocks"]

        # Should have 1 condition block (only the active if branch)
        # Note: Inactive elif/else branches are NOT included in condition_blocks
        assert len(condition_blocks) == 1
        assert condition_blocks[0]["line"] == 2
        assert condition_blocks[0]["expression"] == "DEBUG == 1"
        assert condition_blocks[0]["type"] == "if"

    finally:
        os.unlink(filepath)


def test_condition_blocks_with_header_guards():
    """Test that header guard conditions are excluded from condition_blocks."""
    analyzer = PCPPAnalyzer()

    code = """#define HEADER_H
#if defined(HEADER_H)
int x = 42;
#endif
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".c", delete=False) as f:
        f.write(code)
        filepath = f.name

    try:
        result = analyzer.analyze(filepath, 3)

        assert "condition_blocks" in result
        condition_blocks = result["condition_blocks"]

        # Header guard condition should be filtered out
        assert len(condition_blocks) == 0

    finally:
        os.unlink(filepath)


def test_condition_blocks_with_active_elif():
    """Test condition blocks when an elif branch is active."""
    analyzer = PCPPAnalyzer()

    code = """#define DEBUG 2
#if DEBUG == 1
int x = 1;
#elif DEBUG == 2
int x = 2;
#else
int x = 3;
#endif
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".c", delete=False) as f:
        f.write(code)
        filepath = f.name

    try:
        result = analyzer.analyze(filepath, 5)

        assert "condition_blocks" in result
        condition_blocks = result["condition_blocks"]

        assert len(condition_blocks) == 1
        assert condition_blocks[0]["line"] == 4
        assert condition_blocks[0]["expression"] == "DEBUG == 2"
        assert condition_blocks[0]["type"] == "elif"

    finally:
        os.unlink(filepath)
