# C Macro Analyzer Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enhance C macro analyzer to fix empty parentheses issue and add condition block tracking with line numbers

**Architecture:** Modify PCPPAnalyzer to track condition contexts per line, add condition_blocks output field, and improve header guard filtering to remove empty parentheses

**Tech Stack:** Python 3.14, pcpp library, pytest for testing

---

## File Structure

**Modified files:**
- `c-macro-analyzer/macro_analyzer/analyzer.py` - Main analyzer logic with condition tracking
- `c-macro-analyzer/tests/test_analyzer.py` - Test cases for new functionality
- `c-macro-analyzer/tests/test_integration.py` - Integration tests

**New files:**
- `c-macro-analyzer/tests/test_condition_blocks.py` - Tests for condition block tracking

---

### Task 1: Setup Development Environment

**Files:**
- Create: `.worktrees/macro-analyzer-enhancements/c-macro-analyzer/venv/`
- Modify: `.worktrees/macro-analyzer-enhancements/c-macro-analyzer/requirements.txt`
- Test: `.worktrees/macro-analyzer-enhancements/c-macro-analyzer/tests/test_analyzer.py`

- [ ] **Step 1: Create virtual environment**

```bash
cd .worktrees/macro-analyzer-enhancements/c-macro-analyzer
python -m venv venv
```

- [ ] **Step 2: Activate virtual environment and install dependencies**

```bash
source venv/bin/activate
pip install -e .
```

- [ ] **Step 3: Verify installation**

```bash
python -c "import pcpp; import macro_analyzer; print('Dependencies installed')"
```

Expected: "Dependencies installed"

- [ ] **Step 4: Run existing tests to verify baseline**

```bash
pytest tests/test_analyzer.py -v
```

Expected: All tests pass

- [ ] **Step 5: Commit environment setup**

```bash
git add .gitignore
git commit -m "chore: setup virtual environment for development"
```

---

### Task 2: Fix Empty Parentheses Issue in Header Guard Filtering

**Files:**
- Modify: `c-macro-analyzer/macro_analyzer/analyzer.py:205-222` - `_filter_header_guards` method
- Test: `c-macro-analyzer/tests/test_analyzer.py` - Add test cases

- [ ] **Step 1: Write failing test for empty parentheses**

```python
def test_filter_header_guards_removes_empty_parentheses():
    """Test that empty parentheses are removed after header guard filtering."""
    analyzer = PCPPAnalyzer()
    
    # Test cases: (input, expected_output)
    test_cases = [
        ("()", ""),
        ("( )", ""),
        ("(  )", ""),
        ("() && DEBUG", "DEBUG"),
        ("DEBUG && ()", "DEBUG"),
        ("() && ()", ""),
        ("(defined(HEADER_H))", ""),
        ("(defined(HEADER_H) && DEBUG)", "DEBUG"),
        ("DEBUG && (defined(HEADER_H))", "DEBUG"),
        ("(defined(HEADER_H)) && (defined(OTHER_H))", ""),
    ]
    
    for input_expr, expected in test_cases:
        result = analyzer._filter_header_guards(input_expr)
        assert result == expected, f"Failed for '{input_expr}': got '{result}', expected '{expected}'"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_analyzer.py::test_filter_header_guards_removes_empty_parentheses -v
```

Expected: FAIL with assertion errors

- [ ] **Step 3: Modify _filter_header_guards method**

```python
def _filter_header_guards(self, expression: str) -> str:
    """Remove header guard defined() calls from expression.

    Args:
        expression: Combined logical expression

    Returns:
        Expression with header guard defined() calls removed
    """
    # 1. Remove header guard defined() calls
    filtered = re.sub(
        r"!?defined\s*\(\s*(\w+)\s*\)",
        lambda m: "" if self._is_header_guard(m.group(1)) else m.group(0),
        expression,
    )
    
    # 2. Remove empty parentheses pairs
    filtered = re.sub(r"\(\s*\)", "", filtered)
    
    # 3. Clean up extra logical operators
    filtered = re.sub(r"\s*(&&|\|\|)\s*$", "", filtered)
    filtered = re.sub(r"^\s*(&&|\|\|)\s*", "", filtered)
    filtered = re.sub(r"\s*(&&|\|\|)\s*(&&|\|\|)\s*", " ", filtered)
    
    # 4. Clean up extra spaces
    filtered = re.sub(r"\s+", " ", filtered)
    
    return filtered.strip()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_analyzer.py::test_filter_header_guards_removes_empty_parentheses -v
```

Expected: PASS

- [ ] **Step 5: Run all existing tests to ensure no regression**

```bash
pytest tests/test_analyzer.py -v
```

Expected: All tests pass

- [ ] **Step 6: Commit empty parentheses fix**

```bash
git add macro_analyzer/analyzer.py tests/test_analyzer.py
git commit -m "fix: remove empty parentheses after header guard filtering"
```

---

### Task 3: Add Condition Context Tracking

**Files:**
- Modify: `c-macro-analyzer/macro_analyzer/analyzer.py` - Add `line_contexts` field and update `_track_line`
- Test: `c-macro-analyzer/tests/test_condition_blocks.py` - New test file

- [ ] **Step 1: Create test file for condition block tracking**

```python
import os
import tempfile
import pytest
from macro_analyzer.analyzer import PCPPAnalyzer

def test_condition_context_tracking():
    """Test that condition contexts are tracked per line."""
    analyzer = PCPPAnalyzer()
    
    # Test nested conditions
    code = """
#define FOO 1
#define BAR 0
#if FOO == 1            // line 3
#if BAR == 0            // line 4
int x = 42;             // line 5 - target
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
    
    code = """
#define DEBUG 1
#if DEBUG == 1          // line 3
int x = 1;              // line 4 - target
#elif DEBUG == 2        // line 5
int x = 2;
#else                   // line 7
int x = 3;
#endif
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".c", delete=False) as f:
        f.write(code)
        filepath = f.name
    
    try:
        result = analyzer.analyze(filepath, 4)
        
        assert "condition_blocks" in result
        condition_blocks = result["condition_blocks"]
        
        # Should have 1 condition block (only the active if branch)
        # Note: Inactive elif/else branches are NOT included in condition_blocks
        assert len(condition_blocks) == 1
        assert condition_blocks[0]["line"] == 3
        assert condition_blocks[0]["expression"] == "DEBUG == 1"
        assert condition_blocks[0]["type"] == "if"
        
    finally:
        os.unlink(filepath)

def test_condition_blocks_with_header_guards():
    """Test that header guard conditions are excluded from condition_blocks."""
    analyzer = PCPPAnalyzer()
    
    code = """
#define HEADER_H
#if defined(HEADER_H)    // line 3
int x = 42;              // line 4 - target
#endif
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".c", delete=False) as f:
        f.write(code)
        filepath = f.name
    
    try:
        result = analyzer.analyze(filepath, 4)
        
        assert "condition_blocks" in result
        condition_blocks = result["condition_blocks"]
        
        # Header guard condition should be filtered out
        assert len(condition_blocks) == 0
        
    finally:
        os.unlink(filepath)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_condition_blocks.py -v
```

Expected: FAIL with "condition_blocks not in result" or similar

- [ ] **Step 3: Add line_contexts field to PCPPAnalyzer**

**Note:** `ConditionContext` is already defined in the codebase (line 12-21 in analyzer.py). It has fields: `type`, `condition`, `line`, `active`, `is_else`.

In `analyzer.py`, modify `__init__` method to add `line_contexts` field:

```python
def __init__(self, log_level: LogLevel = LogLevel.QUIET):
    super().__init__()
    self.logger = MacroLogger(log_level)
    self.condition_stack: List[ConditionContext] = []
    self.line_conditions: Dict[int, List[str]] = {}
    self.line_contexts: Dict[int, List[ConditionContext]] = {}  # NEW - tracks full context objects
    self.current_line = 0
    self.symbols: Dict[str, Optional[str]] = {}
    self.last_directive_line = 0
    self.last_directive_conditions: List[str] = []
    self.block_stack: List[Tuple[int, str]] = []  # (start_line, condition)
    self.block_ranges: List[Tuple[int, int, str]] = []  # (start, end, condition)
```

**Data model clarification:**
- `condition_stack`: Current active condition contexts during parsing
- `line_conditions`: Maps line numbers → condition expression strings (existing)
- `line_contexts`: Maps line numbers → full ConditionContext objects (new, for detailed tracking)

- [ ] **Step 4: Update _track_line method to track contexts**

```python
def _track_line(self):
    """Record current line's active conditions."""
    if self.current_line > 0:
        # Only record if not already recorded for this line
        if self.current_line not in self.line_contexts:
            active_conditions = []
            active_contexts = []
            for ctx in self.condition_stack:
                if ctx.active and ctx.condition:
                    active_conditions.append(ctx.condition)
                    active_contexts.append(ctx)
            self.line_conditions[self.current_line] = active_conditions
            self.line_contexts[self.current_line] = active_contexts
            self.logger.trace(
                f"Line {self.current_line} conditions: {active_conditions} (stack size: {len(self.condition_stack)})"
            )
```

- [ ] **Step 5: Update analyze method to include condition_blocks**

**Important:** This is a diff showing changes to the existing `analyze` method. The existing method (lines 56-111 in analyzer.py) must be modified, not replaced entirely.

```python
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
    self.line_contexts.clear()  # NEW - added this line
    self.symbols.clear()
    self.current_line = 0
    self.block_stack.clear()
    self.block_ranges.clear()

    self.logger.verbose(f"Starting analysis of {filepath}")

    try:
        # Process the file
        with open(filepath, "r") as f:
            content = f.read()

        # Parse with pcpp
        self.parse(content, filepath)

        # Process through preprocessor to trigger callbacks
        import io

        output = io.StringIO()
        self.write(output)

        # After processing, apply block ranges to lines
        self._apply_block_ranges()

        # Get conditions for target line
        conditions = self.line_conditions.get(target_line, [])
        combined = self._combine_conditions(conditions)
        filtered_combined = self._filter_header_guards(combined)
        
        # NEW: Get condition contexts for target line
        contexts = self.line_contexts.get(target_line, [])
        condition_blocks = []
        for ctx in contexts:
            # Filter out header guard conditions
            if ctx.condition and not self._is_header_guard_in_expression(ctx.condition):
                condition_blocks.append({
                    "line": ctx.line,
                    "expression": ctx.condition,
                    "type": ctx.type  # ctx.type comes from ConditionContext.type field
                })

        self.logger.verbose(
            f"Line {target_line} controlled by: {filtered_combined}"
        )

        return {
            "file": filepath,
            "line": target_line,
            "macros": self._extract_macros(filtered_combined),
            "combined_expression": filtered_combined,
            "condition_blocks": condition_blocks,  # NEW field
        }

    except Exception as e:
        self.logger.error(f"Analysis failed: {e}")
        raise

def _is_header_guard_in_expression(self, expression: str) -> bool:
    """Check if expression contains only header guard macros."""
    # Extract all macro names from expression
    import re
    macro_names = re.findall(r"defined\s*\(\s*(\w+)\s*\)", expression)
    if not macro_names:
        return False
    # Check if all macros are header guards
    return all(self._is_header_guard(name) for name in macro_names)
```

**Note about `ctx.type`:** The `ConditionContext.type` field is populated in `_push_condition` method (lines 350-370) based on directive type: 'if', 'ifdef', 'ifndef', 'elif', or 'else'.

- [ ] **Step 6: Run test to verify it passes**

```bash
pytest tests/test_condition_blocks.py -v
```

Expected: PASS

- [ ] **Step 7: Run all existing tests**

```bash
pytest tests/ -v
```

Expected: All tests pass

- [ ] **Step 8: Commit condition block tracking**

```bash
git add macro_analyzer/analyzer.py tests/test_condition_blocks.py
git commit -m "feat: add condition_blocks with line numbers to output"
```

---

### Task 4: Integration Test with Real Example

**Files:**
- Test: `c-macro-analyzer/tests/test_integration.py` - Add integration test
- Create: `c-macro-analyzer/tests/samples/real_example.c` - Test file

- [ ] **Step 1: Create test sample file**

```c
// tests/samples/real_example.c
#define WASM_ENABLE_REF_TYPES 1
#define WASM_ENABLE_EXTENDED_CONST_EXPR 0
#define WASM_ENABLE_GC 1

#if WASM_ENABLE_GC != 0
  #if WASM_ENABLE_EXTENDED_CONST_EXPR != 0
    #define EXTRA_PARAM NULL
  #else
    #define EXTRA_PARAM
  #endif
  
  void process_gc() {
    // Line 13 - target
    some_function(EXTRA_PARAM);
  }
#endif
```

- [ ] **Step 2: Write integration test**

```python
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
```

- [ ] **Step 3: Run integration test**

```bash
pytest tests/test_integration.py::test_real_world_example_with_condition_blocks -v
```

Expected: PASS

- [ ] **Step 4: Test with the original wasm_loader.c example**

```bash
cd .worktrees/macro-analyzer-enhancements/c-macro-analyzer
python -m macro_analyzer "/Users/liam/warehouse/wasm-micro-runtime/core/iwasm/interpreter/wasm_loader.c" 1223 --output json | python -m json.tool
```

Check that:
1. No empty parentheses `()` in combined_expression
2. condition_blocks field exists with line numbers
3. Output is valid JSON

- [ ] **Step 5: Commit integration tests**

```bash
git add tests/test_integration.py tests/samples/real_example.c
git commit -m "test: add integration tests for condition blocks"
```

---

### Task 5: Update Documentation

**Files:**
- Modify: `c-macro-analyzer/README.md` - Update output format documentation

- [ ] **Step 1: Update README with new output format**

Add to README.md after the existing output format section:

```markdown
### Enhanced Output Format (v1.1+)

The analyzer now includes a `condition_blocks` field that provides detailed information about each conditional block controlling the target line:

```json
{
  "file": "example.c",
  "line": 42,
  "macros": [...],
  "combined_expression": "FOO == 1 && BAR == 0",
  "condition_blocks": [
    {
      "line": 3,
      "expression": "FOO == 1",
      "type": "if"
    },
    {
      "line": 4,
      "expression": "BAR == 0",
      "type": "if"
    }
  ]
}
```

**condition_blocks fields:**
- **line**: The source file line number where the conditional directive appears
- **expression**: The original condition expression
- **type**: Type of conditional directive: `"if"`, `"ifdef"`, `"ifndef"`, `"elif"`, or `"else"`

**Note:** Header guard conditions (macros matching `*_H*` pattern) are automatically excluded from `condition_blocks`.

### Empty Parentheses Fix

Empty parentheses `()` that could appear in `combined_expression` after header guard filtering are now automatically removed.
```

- [ ] **Step 2: Verify documentation**

```bash
cd .worktrees/macro-analyzer-enhancements/c-macro-analyzer
python -m macro_analyzer --help | grep -A5 "condition_blocks"
```

Expected: Help text mentions condition_blocks or shows updated usage

- [ ] **Step 3: Commit documentation updates**

```bash
git add README.md
git commit -m "docs: update README with condition_blocks and empty parentheses fix"
```

---

### Task 6: Final Verification

**Files:**
- Test: All test files

- [ ] **Step 1: Run complete test suite**

```bash
cd .worktrees/macro-analyzer-enhancements/c-macro-analyzer
pytest tests/ -v
```

Expected: All tests pass

- [ ] **Step 2: Test with command-line interface**

```bash
python -m macro_analyzer tests/samples/simple.c 3 --output json | python -m json.tool
```

Check that output includes condition_blocks field

- [ ] **Step 3: Test with text output format**

```bash
python -m macro_analyzer tests/samples/simple.c 3 --output text
```

Check that text output still works (condition_blocks may not be shown in text mode)

- [ ] **Step 4: Create final summary**

```bash
cd .worktrees/macro-analyzer-enhancements
git log --oneline -10
```

Expected: Shows all commits from this implementation

- [ ] **Step 5: Final commit if any changes**

```bash
git add -A
git commit -m "chore: final verification and cleanup"
```

---

## Plan Review

**Summary of changes:**
1. Fixed empty parentheses issue in header guard filtering
2. Added condition block tracking with line numbers
3. Added `condition_blocks` field to JSON output
4. Updated documentation
5. Added comprehensive tests

**Backward compatibility:** 
- Existing `macros` and `combined_expression` fields unchanged
- New `condition_blocks` field is additive
- Text output format unchanged

**Ready for execution using @superpowers:subagent-driven-development or @superpowers:executing-plans**