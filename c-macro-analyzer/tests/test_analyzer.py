import os
import tempfile
import pytest
from macro_analyzer.analyzer import PCPPAnalyzer, ConditionContext
from macro_analyzer.logging import LogLevel


class TestConditionContext:
    def test_condition_context_creation(self):
        ctx = ConditionContext(
            type="if",
            condition="DEBUG",
            line=10,
            active=True,
            is_else=False,
        )
        assert ctx.type == "if"
        assert ctx.condition == "DEBUG"
        assert ctx.line == 10
        assert ctx.active is True
        assert ctx.is_else is False


class TestPCPPAnalyzerInit:
    def test_analyzer_initialization_default(self):
        analyzer = PCPPAnalyzer()
        # log_level is stored in logger, not as separate attribute
        assert analyzer.logger.level == LogLevel.QUIET

    def test_analyzer_initialization_with_verbose_level(self):
        analyzer = PCPPAnalyzer(log_level=LogLevel.VERBOSE)
        assert analyzer.logger.level == LogLevel.VERBOSE

    def test_analyzer_initialization_with_debug_level(self):
        analyzer = PCPPAnalyzer(log_level=LogLevel.DEBUG)
        assert analyzer.logger.level == LogLevel.DEBUG

    def test_analyzer_has_condition_stack(self):
        analyzer = PCPPAnalyzer()
        assert hasattr(analyzer, "condition_stack")
        assert analyzer.condition_stack == []

    def test_analyzer_has_line_conditions(self):
        analyzer = PCPPAnalyzer()
        assert hasattr(analyzer, "line_conditions")
        assert analyzer.line_conditions == {}  # Changed from [] to {}

    def test_analyzer_has_symbols(self):
        analyzer = PCPPAnalyzer()
        assert hasattr(analyzer, "symbols")

    def test_analyzer_has_current_line(self):
        analyzer = PCPPAnalyzer()
        assert hasattr(analyzer, "current_line")
        assert analyzer.current_line == 0


class TestPCPPAnalyzerBasic:
    def test_analyze_simple_file(self):
        code = """
#define DEBUG
#ifdef DEBUG
int x = 1;
#endif
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".c", delete=False) as f:
            f.write(code)
            f.flush()
            filepath = f.name

        try:
            analyzer = PCPPAnalyzer()
            result = analyzer.analyze(filepath, 4)
            assert result["file"] == filepath
            assert result["line"] == 4
            assert "macros" in result
            assert isinstance(result["macros"], list)
        finally:
            os.unlink(filepath)

    def test_analyze_returns_combined_expression(self):
        code = """
#define A
#define B
#if defined(A) && defined(B)
int x = 1;
#endif
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".c", delete=False) as f:
            f.write(code)
            f.flush()
            filepath = f.name

        try:
            analyzer = PCPPAnalyzer()
            result = analyzer.analyze(filepath, 5)
            assert "combined_expression" in result
            # Also verify macros array has structured format
            assert "macros" in result
            assert isinstance(result["macros"], list)
            # Should contain both A and B with structured info
            assert len(result["macros"]) == 2
            for macro in result["macros"]:
                assert "name" in macro
                assert "condition" in macro
                assert "expression" in macro
                assert macro["condition"] == "defined"
        finally:
            os.unlink(filepath)


def test_directive_handling():
    analyzer = PCPPAnalyzer(log_level=LogLevel.TRACE)

    test_content = """#define VERSION 2
#if VERSION > 1
  // Line 3
#endif
"""
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(mode="w", suffix=".c", delete=False) as f:
        f.write(test_content)
        test_file = f.name

    try:
        result = analyzer.analyze(test_file, 3)
        assert "VERSION > 1" in result["combined_expression"]
        # Verify structured macros output
        assert len(result["macros"]) == 1
        assert result["macros"][0]["name"] == "VERSION"
        assert result["macros"][0]["condition"] == "comparison"
        assert result["macros"][0]["expression"] == "VERSION > 1"
    finally:
        os.unlink(test_file)


def test_extract_macros_structured():
    """Test that _extract_macros extracts all identifiers with proper categorization."""
    from macro_analyzer.analyzer import PCPPAnalyzer

    analyzer = PCPPAnalyzer()

    # Test 1: defined() macros
    expression = "defined(DEBUG) && defined(TEST)"
    result = analyzer._extract_macros(expression)
    expected = [
        {"name": "DEBUG", "condition": "defined", "expression": "defined(DEBUG)"},
        {"name": "TEST", "condition": "defined", "expression": "defined(TEST)"},
    ]
    assert result == expected, f"Expected {expected}, got {result}"

    # Test 2: comparison macros
    expression = 'VERSION > 1 && PLATFORM == "linux"'
    result = analyzer._extract_macros(expression)
    expected = [
        {"name": "VERSION", "condition": "comparison", "expression": "VERSION > 1"},
        {
            "name": "PLATFORM",
            "condition": "comparison",
            "expression": 'PLATFORM == "linux"',
        },
    ]
    assert result == expected, f"Expected {expected}, got {result}"

    # Test 3: mixed expressions
    expression = "defined(DEBUG) && VERSION > 1 && !defined(OLD_API)"
    result = analyzer._extract_macros(expression)
    expected = [
        {"name": "DEBUG", "condition": "defined", "expression": "defined(DEBUG)"},
        {"name": "VERSION", "condition": "comparison", "expression": "VERSION > 1"},
        {"name": "OLD_API", "condition": "defined", "expression": "defined(OLD_API)"},
    ]
    # Note: !defined(OLD_API) should still be categorized as "defined"
    assert result == expected, f"Expected {expected}, got {result}"

    # Test 4: Negation handling
    expression = "!defined(DISABLED)"
    result = analyzer._extract_macros(expression)
    expected = [
        {"name": "DISABLED", "condition": "defined", "expression": "defined(DISABLED)"}
    ]
    assert result == expected, f"Expected {expected}, got {result}"

    # Test 5: Edge cases
    # Empty string
    assert analyzer._extract_macros("") == [], "Expected empty list for empty string"

    # String literal (should not match content inside quotes)
    expression = 'PLATFORM == "LINUX_VERSION"'
    result = analyzer._extract_macros(expression)
    expected = [
        {
            "name": "PLATFORM",
            "condition": "comparison",
            "expression": 'PLATFORM == "LINUX_VERSION"',
        }
    ]
    assert result == expected, f"Expected {expected}, got {result}"


def test_header_guard_filtering():
    """Test that header guard macros (*_H* pattern) are filtered out."""
    from macro_analyzer.analyzer import PCPPAnalyzer

    analyzer = PCPPAnalyzer()

    test_cases = [
        ("defined(MY_HEADER_H)", []),
        ("defined(PROJECT_HEADER_H_)", []),
        ("!defined(HEADER_H)", []),
        (
            "defined(HEADER_H) && defined(DEBUG)",
            [
                {
                    "name": "DEBUG",
                    "condition": "defined",
                    "expression": "defined(DEBUG)",
                }
            ],
        ),
        (
            "VERSION > 1 && defined(API_H)",
            [
                {
                    "name": "VERSION",
                    "condition": "comparison",
                    "expression": "VERSION > 1",
                }
            ],
        ),
        (
            "defined(NOT_A_HEADER)",
            [
                {
                    "name": "NOT_A_HEADER",
                    "condition": "defined",
                    "expression": "defined(NOT_A_HEADER)",
                }
            ],
        ),
        (
            "defined(SOME_H_FILE)",
            [],
        ),
    ]

    for expression, expected in test_cases:
        result = analyzer._extract_macros(expression)
        assert result == expected, (
            f"For expression '{expression}': expected {expected}, got {result}"
        )
