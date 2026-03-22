# PCPP-based Macro Analyzer Refactor Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor c-macro-analyzer to use pcpp library for preprocessor parsing and add three-level logging system while maintaining CLI compatibility.

**Architecture:** Replace custom expression parser and preprocessor logic with pcpp library, add configurable logging with -v/-vv/-vvv levels, keep existing JSON output format and CLI interface.

**Tech Stack:** Python 3.8+, pcpp>=1.30, pytest for testing

---

## Chunk 1: Project Setup and Dependencies

### Task 1: Update project dependencies

**Files:**
- Modify: `c-macro-analyzer/requirements.txt`
- Modify: `c-macro-analyzer/pyproject.toml`

- [ ] **Step 1: Add pcpp to requirements.txt**

```txt
# For development
pytest>=7.0
black>=23.0
ruff>=0.1.0
pcpp>=1.30
```

- [ ] **Step 2: Update pyproject.toml optional dependencies**

```toml
[project.optional-dependencies]
dev = ["pytest>=7.0", "black>=23.0", "ruff>=0.1.0", "pcpp>=1.30"]
```

- [ ] **Step 3: Commit dependencies update**

```bash
git add c-macro-analyzer/requirements.txt c-macro-analyzer/pyproject.toml
git commit -m "chore: add pcpp dependency"
```

### Task 2: Create logging system

**Files:**
- Create: `c-macro-analyzer/macro_analyzer/logging.py`

- [ ] **Step 1: Write failing test for logging levels**

```python
# tests/test_logging.py
import pytest
from macro_analyzer.logging import MacroLogger, LogLevel

def test_logger_levels():
    logger = MacroLogger(LogLevel.QUIET)
    assert logger.level == LogLevel.QUIET
    
    logger = MacroLogger(LogLevel.VERBOSE)
    assert logger.level == LogLevel.VERBOSE
    
    logger = MacroLogger(LogLevel.DEBUG)
    assert logger.level == LogLevel.DEBUG
    
    logger = MacroLogger(LogLevel.TRACE)
    assert logger.level == LogLevel.TRACE

def test_logger_methods():
    logger = MacroLogger(LogLevel.DEBUG)
    # Methods should exist
    assert hasattr(logger, 'verbose')
    assert hasattr(logger, 'debug')
    assert hasattr(logger, 'trace')
    assert hasattr(logger, 'error')
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd c-macro-analyzer && pytest tests/test_logging.py::test_logger_levels -v
```
Expected: FAIL with "ModuleNotFoundError: No module named 'macro_analyzer.logging'"

- [ ] **Step 3: Implement MacroLogger class**

```python
# c-macro-analyzer/macro_analyzer/logging.py
import logging
import sys
from enum import IntEnum

class LogLevel(IntEnum):
    """Three-level logging system."""
    QUIET = 0      # Default: errors only
    VERBOSE = 1    # -v: INFO level (major events)
    DEBUG = 2      # -vv: DEBUG level (detailed processing)
    TRACE = 3      # -vvv: TRACE level (internal state)

class MacroLogger:
    """Custom logger for macro analyzer with three verbosity levels."""
    
    def __init__(self, level: LogLevel = LogLevel.QUIET):
        self.level = level
        self._setup_logger()
    
    def _setup_logger(self):
        """Configure logging level and format."""
        # Map our levels to standard logging levels
        level_map = {
            LogLevel.QUIET: logging.WARNING,
            LogLevel.VERBOSE: logging.INFO,
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.TRACE: logging.DEBUG - 5  # Custom TRACE level
        }
        
        # Add TRACE level name
        logging.addLevelName(logging.DEBUG - 5, "TRACE")
        
        # Configure logger
        self.logger = logging.getLogger("macro_analyzer")
        self.logger.setLevel(level_map[self.level])
        
        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()
        
        # Add stderr handler with custom format
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter(
            '%(levelname)s:%(name)s:%(lineno)d - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def verbose(self, msg: str):
        """Log at VERBOSE level (-v)."""
        if self.level >= LogLevel.VERBOSE:
            self.logger.info(msg)
    
    def debug(self, msg: str):
        """Log at DEBUG level (-vv)."""
        if self.level >= LogLevel.DEBUG:
            self.logger.debug(msg)
    
    def trace(self, msg: str):
        """Log at TRACE level (-vvv)."""
        if self.level >= LogLevel.TRACE:
            self.logger.log(logging.DEBUG - 5, msg)
    
    def error(self, msg: str):
        """Log error (always shown)."""
        self.logger.error(msg)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd c-macro-analyzer && pytest tests/test_logging.py::test_logger_levels -v
```
Expected: PASS

- [ ] **Step 5: Commit logging system**

```bash
git add c-macro-analyzer/macro_analyzer/logging.py tests/test_logging.py
git commit -m "feat: add three-level logging system"
```

## Chunk 2: Core PCPP Analyzer

### Task 3: Create PCPP-based analyzer

**Files:**
- Create: `c-macro-analyzer/macro_analyzer/analyzer.py`

- [ ] **Step 1: Write failing test for basic analyzer**

```python
# tests/test_analyzer.py
import pytest
from macro_analyzer.analyzer import PCPPAnalyzer, LogLevel

def test_analyzer_initialization():
    analyzer = PCPPAnalyzer()
    assert analyzer is not None
    
    analyzer = PCPPAnalyzer(log_level=LogLevel.DEBUG)
    assert analyzer.logger.level == LogLevel.DEBUG

def test_analyzer_basic_analysis():
    analyzer = PCPPAnalyzer()
    
    # Create a simple test file
    import tempfile
    import os
    
    test_content = """#define DEBUG
#ifdef DEBUG
  test_function();
#endif
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
        f.write(test_content)
        test_file = f.name
    
    try:
        result = analyzer.analyze(test_file, 3)
        assert result['file'] == test_file
        assert result['line'] == 3
        assert 'DEBUG' in result['combined_expression']
    finally:
        os.unlink(test_file)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd c-macro-analyzer && pytest tests/test_analyzer.py::test_analyzer_initialization -v
```
Expected: FAIL with "ModuleNotFoundError: No module named 'macro_analyzer.analyzer'"

- [ ] **Step 3: Implement PCPPAnalyzer skeleton**

```python
# c-macro-analyzer/macro_analyzer/analyzer.py
import pcpp
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from .logging import MacroLogger, LogLevel

@dataclass
class ConditionContext:
    """Represents a conditional block context."""
    type: str  # 'if', 'ifdef', 'ifndef', 'elif', 'else'
    condition: str  # Original condition expression
    line: int  # Line number where directive appears
    active: bool  # Whether this branch is active
    is_else: bool = False

class PCPPAnalyzer(pcpp.Preprocessor):
    """PCPP-based macro analyzer with condition tracking."""
    
    def __init__(self, log_level: LogLevel = LogLevel.QUIET):
        super().__init__()
        self.logger = MacroLogger(log_level)
        self.condition_stack: List[ConditionContext] = []
        self.line_conditions: Dict[int, List[str]] = {}
        self.current_line = 0
        self.symbols: Dict[str, Optional[str]] = {}
        
        # Configure pcpp to preserve comments and whitespace for line tracking
        self.define("__LINE__")
        self.line_directive = None
    
    def analyze(self, filepath: str, target_line: int) -> Dict[str, Any]:
        """Analyze file and return macro control information.
        
        Args:
            filepath: Path to C/C++ source file
            target_line: Line number to analyze (1-indexed)
            
        Returns:
            Dictionary with analysis results matching existing format
        """
        # Reset state for new analysis
        self.condition_stack.clear()
        self.line_conditions.clear()
        self.symbols.clear()
        self.current_line = 0
        
        self.logger.verbose(f"Starting analysis of {filepath}")
        
        try:
            # Process the file
            with open(filepath, 'r') as f:
                content = f.read()
            
            # Parse with pcpp
            self.parse(content)
            
            # Get conditions for target line
            conditions = self.line_conditions.get(target_line, [])
            combined = self._combine_conditions(conditions)
            
            self.logger.verbose(f"Line {target_line} controlled by: {combined}")
            
            return {
                "file": filepath,
                "line": target_line,
                "macros": self._extract_macros(combined),
                "combined_expression": combined
            }
            
        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            raise
    
    def _combine_conditions(self, conditions: List[str]) -> str:
        """Combine multiple conditions with && operator."""
        if not conditions:
            return ""
        
        valid_conditions = [c for c in conditions if c]
        if not valid_conditions:
            return ""
        
        if len(valid_conditions) == 1:
            return valid_conditions[0]
        
        # Combine with &&, adding parentheses for complex expressions
        combined = valid_conditions[0]
        for condition in valid_conditions[1:]:
            if any(op in condition for op in ["&&", "||", "<", ">", "==", "!=", "!"]):
                condition = f"({condition})"
            combined = f"{combined} && {condition}"
        
        return combined
    
    def _extract_macros(self, expression: str) -> List[Dict[str, str]]:
        """Extract individual macros from combined expression."""
        import re
        macros = []
        
        # Look for defined(macro) patterns
        defined_pattern = r'defined\((\w+)\)'
        for match in re.finditer(defined_pattern, expression):
            macros.append({
                "name": match.group(1),
                "condition": "defined"
            })
        
        return macros
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd c-macro-analyzer && pytest tests/test_analyzer.py::test_analyzer_initialization -v
```
Expected: PASS

- [ ] **Step 5: Commit analyzer skeleton**

```bash
git add c-macro-analyzer/macro_analyzer/analyzer.py tests/test_analyzer.py
git commit -m "feat: add PCPPAnalyzer skeleton"
```

### Task 4: Implement pcpp callback handlers

**Files:**
- Modify: `c-macro-analyzer/macro_analyzer/analyzer.py`

- [ ] **Step 1: Write test for directive handling**

```python
# tests/test_analyzer.py
def test_directive_handling():
    analyzer = PCPPAnalyzer(log_level=LogLevel.QUIET)
    
    test_content = """#define VERSION 2
#if VERSION > 1
  // Line 3
#endif
"""
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
        f.write(test_content)
        test_file = f.name
    
    try:
        result = analyzer.analyze(test_file, 3)
        assert "VERSION > 1" in result['combined_expression']
    finally:
        os.unlink(test_file)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd c-macro-analyzer && pytest tests/test_analyzer.py::test_directive_handling -v
```
Expected: FAIL (no directive handling implemented)

- [ ] **Step 3: Implement pcpp callback methods**

```python
# c-macro-analyzer/macro_analyzer/analyzer.py (add to PCPPAnalyzer class)

    # Override pcpp callback methods
    def on_if(self, tokens):
        """Handle #if directive."""
        self._track_line()
        expr = self._extract_expression(tokens)
        self._push_condition('if', expr)
        self.logger.debug(f"#{self.current_line}: Processing #if {expr}")
        return super().on_if(tokens)
    
    def on_ifdef(self, tokens):
        """Handle #ifdef directive."""
        self._track_line()
        macro = self._extract_macro_name(tokens)
        expr = f"defined({macro})"
        self._push_condition('ifdef', expr)
        self.logger.debug(f"#{self.current_line}: Processing #ifdef {macro}")
        return super().on_ifdef(tokens)
    
    def on_ifndef(self, tokens):
        """Handle #ifndef directive."""
        self._track_line()
        macro = self._extract_macro_name(tokens)
        expr = f"!defined({macro})"
        self._push_condition('ifndef', expr)
        self.logger.debug(f"#{self.current_line}: Processing #ifndef {macro}")
        return super().on_ifndef(tokens)
    
    def on_elif(self, tokens):
        """Handle #elif directive."""
        self._track_line()
        expr = self._extract_expression(tokens)
        self._pop_condition()  # Remove previous if/elif
        self._push_condition('elif', expr)
        self.logger.debug(f"#{self.current_line}: Processing #elif {expr}")
        return super().on_elif(tokens)
    
    def on_else(self):
        """Handle #else directive."""
        self._track_line()
        self._pop_condition()  # Remove previous if/elif
        self._push_condition('else', '', is_else=True)
        self.logger.debug(f"#{self.current_line}: Processing #else")
        return super().on_else()
    
    def on_endif(self):
        """Handle #endif directive."""
        self._track_line()
        if self.condition_stack:
            self.condition_stack.pop()
        self.logger.debug(f"#{self.current_line}: Processing #endif")
        return super().on_endif()
    
    def on_define(self, tokens):
        """Handle #define directive."""
        self._track_line()
        # Extract macro name and value
        if tokens and len(tokens) > 1:
            macro = tokens[1].value
            value = ' '.join(t.value for t in tokens[2:]) if len(tokens) > 2 else None
            self.symbols[macro] = value
            self.logger.debug(f"#{self.current_line}: Defined {macro} = {value}")
        return super().on_define(tokens)
    
    def on_undef(self, tokens):
        """Handle #undef directive."""
        self._track_line()
        if tokens and len(tokens) > 1:
            macro = tokens[1].value
            if macro in self.symbols:
                del self.symbols[macro]
            self.logger.debug(f"#{self.current_line}: Undefined {macro}")
        return super().on_undef(tokens)
    
    def on_line_change(self, line, col):
        """Track line number changes."""
        self.current_line = line
    
    # Helper methods
    def _track_line(self):
        """Record current line's active conditions."""
        if self.current_line > 0:
            active_conditions = []
            for ctx in self.condition_stack:
                if ctx.active and ctx.condition:
                    active_conditions.append(ctx.condition)
            self.line_conditions[self.current_line] = active_conditions
            self.logger.trace(f"Line {self.current_line} conditions: {active_conditions}")
    
    def _push_condition(self, cond_type: str, condition: str, is_else: bool = False):
        """Push a condition onto the stack."""
        # Determine if this condition is active
        active = True
        if not is_else and condition:
            # For non-else conditions, check if any true branch already taken in current block
            for ctx in reversed(self.condition_stack):
                if not ctx.is_else:
                    # Found the current block
                    if ctx.active:
                        active = False  # Already have an active branch
                    break
        
        ctx = ConditionContext(
            type=cond_type,
            condition=condition,
            line=self.current_line,
            active=active,
            is_else=is_else
        )
        self.condition_stack.append(ctx)
    
    def _pop_condition(self) -> Optional[ConditionContext]:
        """Pop a condition from the stack."""
        if self.condition_stack:
            return self.condition_stack.pop()
        return None
    
    def _extract_expression(self, tokens) -> str:
        """Extract expression string from tokens."""
        if not tokens or len(tokens) < 2:
            return ""
        # Skip the directive token (e.g., 'if', 'elif')
        return ' '.join(t.value for t in tokens[1:])
    
    def _extract_macro_name(self, tokens) -> str:
        """Extract macro name from tokens."""
        if not tokens or len(tokens) < 2:
            return ""
        return tokens[1].value
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd c-macro-analyzer && pytest tests/test_analyzer.py::test_directive_handling -v
```
Expected: PASS

- [ ] **Step 5: Commit directive handling**

```bash
git add c-macro-analyzer/macro_analyzer/analyzer.py
git commit -m "feat: implement pcpp directive callbacks"
```

## Chunk 3: CLI Integration and Testing

### Task 5: Update CLI with logging options

**Files:**
- Modify: `c-macro-analyzer/macro_analyzer/cli.py`

- [ ] **Step 1: Write test for CLI logging options**

```python
# tests/test_cli.py
def test_cli_verbose_option():
    import tempfile
    import os
    import subprocess
    
    test_content = """#define DEBUG
#ifdef DEBUG
  test_function();
#endif
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
        f.write(test_content)
        test_file = f.name
    
    try:
        # Test with -v option
        result = subprocess.run(
            ['python', '-m', 'macro_analyzer', test_file, '3', '-v'],
            capture_output=True,
            text=True,
            cwd='c-macro-analyzer'
        )
        assert result.returncode == 0
        # Should have JSON output
        import json
        output = json.loads(result.stdout)
        assert output['line'] == 3
        
        # Test with -vv option
        result = subprocess.run(
            ['python', '-m', 'macro_analyzer', test_file, '3', '-vv'],
            capture_output=True,
            text=True,
            cwd='c-macro-analyzer'
        )
        assert result.returncode == 0
        
    finally:
        os.unlink(test_file)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd c-macro-analyzer && pytest tests/test_cli.py::test_cli_verbose_option -v
```
Expected: FAIL (CLI doesn't have -v/-vv options yet)

- [ ] **Step 3: Update CLI with logging options**

```python
# c-macro-analyzer/macro_analyzer/cli.py
import argparse
import json
import sys
from .analyzer import PCPPAnalyzer
from .logging import LogLevel

def main():
    parser = argparse.ArgumentParser(
        description="Analyze C/C++ preprocessor macro control of source lines"
    )
    parser.add_argument("file", help="Path to C/C++ source file")
    parser.add_argument("line", type=int, help="Line number to analyze (1-indexed)")
    parser.add_argument(
        "--output",
        "-o",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )
    
    # Add verbosity options
    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show INFO level logs (major events)"
    )
    verbosity.add_argument(
        "-vv", "--debug",
        action="store_true",
        help="Show DEBUG level logs (detailed processing)"
    )
    verbosity.add_argument(
        "-vvv", "--trace",
        action="store_true",
        help="Show TRACE level logs (internal state)"
    )
    
    args = parser.parse_args()
    
    # Determine log level
    if args.trace:
        log_level = LogLevel.TRACE
    elif args.debug:
        log_level = LogLevel.DEBUG
    elif args.verbose:
        log_level = LogLevel.VERBOSE
    else:
        log_level = LogLevel.QUIET
    
    try:
        analyzer = PCPPAnalyzer(log_level=log_level)
        result = analyzer.analyze(args.file, args.line)
        
        if args.output == "json":
            print(json.dumps(result, indent=2))
        else:
            print(f"File: {result['file']}")
            print(f"Line: {result['line']}")
            print(f"Macros: {len(result['macros'])}")
            print(f"Expression: {result['combined_expression']}")
        
        return 0
    except FileNotFoundError:
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd c-macro-analyzer && pytest tests/test_cli.py::test_cli_verbose_option -v
```
Expected: PASS

- [ ] **Step 5: Commit CLI updates**

```bash
git add c-macro-analyzer/macro_analyzer/cli.py
git commit -m "feat: add -v/-vv/-vvv logging options to CLI"
```

### Task 6: Create comprehensive analyzer tests

**Files:**
- Modify: `tests/test_analyzer.py`

- [ ] **Step 1: Write test for nested conditions**

```python
# tests/test_analyzer.py
def test_nested_conditions():
    analyzer = PCPPAnalyzer(log_level=LogLevel.QUIET)
    
    test_content = """#define DEBUG
#define VERSION 3

#ifdef DEBUG
  #if VERSION > 2
    // Line 6
  #endif
#endif
"""
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
        f.write(test_content)
        test_file = f.name
    
    try:
        result = analyzer.analyze(test_file, 6)
        combined = result['combined_expression']
        assert "defined(DEBUG)" in combined
        assert "VERSION > 2" in combined
    finally:
        os.unlink(test_file)

def test_string_comparison():
    analyzer = PCPPAnalyzer(log_level=LogLevel.QUIET)
    
    test_content = """#define PLATFORM "linux"
#if PLATFORM == "linux"
  // Line 3
#endif
"""
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
        f.write(test_content)
        test_file = f.name
    
    try:
        result = analyzer.analyze(test_file, 3)
        assert 'PLATFORM == "linux"' in result['combined_expression']
    finally:
        os.unlink(test_file)

def test_elif_else_handling():
    analyzer = PCPPAnalyzer(log_level=LogLevel.QUIET)
    
    test_content = """#define VERSION 2
#if VERSION > 3
  // Line 3
#elif VERSION > 1
  // Line 5
#else
  // Line 7
#endif
"""
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
        f.write(test_content)
        test_file = f.name
    
    try:
        # Line 5 should be controlled by VERSION > 1
        result = analyzer.analyze(test_file, 5)
        assert "VERSION > 1" in result['combined_expression']
    finally:
        os.unlink(test_file)
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
cd c-macro-analyzer && pytest tests/test_analyzer.py::test_nested_conditions -v
```
Expected: PASS

```bash
cd c-macro-analyzer && pytest tests/test_analyzer.py::test_string_comparison -v
```
Expected: PASS

```bash
cd c-macro-analyzer && pytest tests/test_analyzer.py::test_elif_else_handling -v
```
Expected: PASS

- [ ] **Step 3: Commit analyzer tests**

```bash
git add tests/test_analyzer.py
git commit -m "test: add comprehensive analyzer tests"
```

## Chunk 4: Cleanup and Integration

### Task 7: Remove old implementation files

**Files:**
- Remove: `c-macro-analyzer/macro_analyzer/expression.py`
- Remove: `c-macro-analyzer/macro_analyzer/symbols.py`
- Remove: `c-macro-analyzer/macro_analyzer/processor.py`
- Remove: `tests/test_expression.py`
- Remove: `tests/test_symbols.py`
- Remove: `tests/test_processor.py`

- [ ] **Step 1: Remove expression.py and symbols.py**

```bash
rm c-macro-analyzer/macro_analyzer/expression.py
rm c-macro-analyzer/macro_analyzer/symbols.py
```

- [ ] **Step 2: Remove processor.py**

```bash
rm c-macro-analyzer/macro_analyzer/processor.py
```

- [ ] **Step 3: Remove old test files**

```bash
rm tests/test_expression.py
rm tests/test_symbols.py
rm tests/test_processor.py
```

- [ ] **Step 4: Update __init__.py imports**

```python
# c-macro-analyzer/macro_analyzer/__init__.py
"""C/C++ Macro Analyzer - Analyze preprocessor macro control of source lines."""

__version__ = "0.2.0"

# Export new API
from .analyzer import PCPPAnalyzer
from .logging import MacroLogger, LogLevel
```

- [ ] **Step 5: Commit cleanup**

```bash
git add c-macro-analyzer/macro_analyzer/__init__.py
git rm c-macro-analyzer/macro_analyzer/expression.py
git rm c-macro-analyzer/macro_analyzer/symbols.py
git rm c-macro-analyzer/macro_analyzer/processor.py
git rm tests/test_expression.py
git rm tests/test_symbols.py
git rm tests/test_processor.py
git commit -m "chore: remove old implementation files"
```

### Task 8: Update integration tests

**Files:**
- Modify: `tests/test_integration.py`

- [ ] **Step 1: Update integration test to use new analyzer**

```python
# tests/test_integration.py
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
        
        # Test line 5 (advanced_debug)
        result = analyzer.analyze(test_file, 5)
        assert result["line"] == 5
        assert "DEBUG" in result["combined_expression"]
        assert "VERSION > 2" in result["combined_expression"]
        
        # Test line 12 (linux_code)
        result = analyzer.analyze(test_file, 12)
        assert result["line"] == 12
        assert "PLATFORM" in result["combined_expression"]
        assert "linux" in result["combined_expression"]
        
    finally:
        os.unlink(test_file)
```

- [ ] **Step 2: Run integration test**

```bash
cd c-macro-analyzer && pytest tests/test_integration.py::test_integration_complex_file -v
```
Expected: PASS

- [ ] **Step 3: Commit updated integration tests**

```bash
git add tests/test_integration.py
git commit -m "test: update integration tests for new analyzer"
```

### Task 9: Final verification

**Files:**
- Test: All test files

- [ ] **Step 1: Run full test suite**

```bash
cd c-macro-analyzer && pytest -v
```
Expected: All tests pass

- [ ] **Step 2: Test CLI with sample files**

```bash
cd c-macro-analyzer && python -m macro_analyzer tests/samples/simple.c 6
```
Expected: JSON output with `"combined_expression": "defined(DEBUG)"`

```bash
cd c-macro-analyzer && python -m macro_analyzer tests/samples/simple.c 6 -v
```
Expected: Same JSON output plus INFO logs to stderr

```bash
cd c-macro-analyzer && python -m macro_analyzer tests/samples/simple.c 6 -vv
```
Expected: Same JSON output plus DEBUG logs to stderr

- [ ] **Step 3: Update README if needed**

Check if README needs updates for new logging features.

- [ ] **Step 4: Final commit**

```bash
git add .
git commit -m "chore: final verification and cleanup"
```

## Chunk 5: Plan Review and Execution

### Task 10: Plan review and execution handoff

- [ ] **Step 1: Review plan completeness**
- [ ] **Step 2: Save plan to docs**
- [ ] **Step 3: Create git worktree for implementation**
- [ ] **Step 4: Execute plan using subagent-driven-development**

**Plan complete and saved to `docs/superpowers/plans/2026-03-21-pcpp-macro-analyzer-refactor.md`. Ready to execute?**