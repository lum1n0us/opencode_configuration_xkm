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
        assert analyzer.log_level == LogLevel.QUIET

    def test_analyzer_initialization_with_verbose_level(self):
        analyzer = PCPPAnalyzer(log_level=LogLevel.VERBOSE)
        assert analyzer.log_level == LogLevel.VERBOSE

    def test_analyzer_initialization_with_debug_level(self):
        analyzer = PCPPAnalyzer(log_level=LogLevel.DEBUG)
        assert analyzer.log_level == LogLevel.DEBUG

    def test_analyzer_has_condition_stack(self):
        analyzer = PCPPAnalyzer()
        assert hasattr(analyzer, "condition_stack")
        assert analyzer.condition_stack == []

    def test_analyzer_has_line_conditions(self):
        analyzer = PCPPAnalyzer()
        assert hasattr(analyzer, "line_conditions")
        assert analyzer.line_conditions == []

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
        finally:
            os.unlink(filepath)
