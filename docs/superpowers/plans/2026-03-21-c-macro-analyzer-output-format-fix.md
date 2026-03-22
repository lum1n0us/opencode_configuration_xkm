# C-Macro-Analyzer Output Format Fix Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix c-macro-analyzer output format inconsistencies by implementing structured macro extraction and automatic header guard filtering.

**Architecture:** Modify `_extract_macros` method to extract all identifiers from combined expression, categorize them by usage pattern, filter header guard macros (*_H* pattern), and produce structured output matching README example.

**Tech Stack:** Python 3.8+, pcpp>=1.30, pytest, regex for pattern matching

---

## File Structure

**Files to modify:**
- `c-macro-analyzer/macro_analyzer/analyzer.py:122-139` - `_extract_macros` method
- `c-macro-analyzer/tests/test_analyzer.py` - Add tests for new functionality
- `c-macro-analyzer/README.md:60-70` - Update example output format

**Responsibilities:**
- `analyzer.py:_extract_macros` - Extract all identifiers, categorize by usage, filter header guards
- `test_analyzer.py` - Verify structured output and header guard filtering
- `README.md` - Update documentation to match actual behavior

## Chunk 1: Core Macro Extraction Logic

### Task 1: Write failing test for structured macro extraction

**Files:**
- Modify: `c-macro-analyzer/tests/test_analyzer.py`

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/test_analyzer.py after existing tests
def test_extract_macros_structured():
    """Test that _extract_macros extracts all identifiers with proper categorization."""
    from macro_analyzer.analyzer import PCPPAnalyzer
    
    analyzer = PCPPAnalyzer()
    
    # Test 1: defined() macros
    expression = "defined(DEBUG) && defined(TEST)"
    result = analyzer._extract_macros(expression)
    expected = [
        {"name": "DEBUG", "condition": "defined", "expression": "defined(DEBUG)"},
        {"name": "TEST", "condition": "defined", "expression": "defined(TEST)"}
    ]
    assert result == expected, f"Expected {expected}, got {result}"
    
    # Test 2: comparison macros
    expression = "VERSION > 1 && PLATFORM == \"linux\""
    result = analyzer._extract_macros(expression)
    expected = [
        {"name": "VERSION", "condition": "comparison", "expression": "VERSION > 1"},
        {"name": "PLATFORM", "condition": "comparison", "expression": "PLATFORM == \"linux\""}
    ]
    assert result == expected, f"Expected {expected}, got {result}"
    
    # Test 3: mixed expressions
    expression = "defined(DEBUG) && VERSION > 1 && !defined(OLD_API)"
    result = analyzer._extract_macros(expression)
    expected = [
        {"name": "DEBUG", "condition": "defined", "expression": "defined(DEBUG)"},
        {"name": "VERSION", "condition": "comparison", "expression": "VERSION > 1"},
        {"name": "OLD_API", "condition": "defined", "expression": "defined(OLD_API)"}
    ]
    # Note: !defined(OLD_API) should still be categorized as "defined"
    assert result == expected, f"Expected {expected}, got {result}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/liam/.config/opencode/.worktrees/pcpp-refactor/c-macro-analyzer && source venv/bin/activate && pytest tests/test_analyzer.py::test_extract_macros_structured -v`
Expected: FAIL with assertion error or method not returning expected format

- [ ] **Step 3: Write minimal implementation**

```python
# Modify c-macro-analyzer/macro_analyzer/analyzer.py _extract_macros method
def _extract_macros(self, expression: str) -> List[Dict[str, str]]:
    """Extract individual macros from combined expression with categorization.
    
    Args:
        expression: Combined logical expression
        
    Returns:
        List of dicts with name, condition, and expression for each macro
    """
    import re
    
    macros = []
    
    # Pattern to match defined(macro) with optional negation
    defined_pattern = re.compile(r'(!?\s*defined\s*\(\s*(\w+)\s*\))')
    for full_match, macro in defined_pattern.findall(expression):
        macros.append({
            "name": macro,
            "condition": "defined",
            "expression": full_match.strip()
        })
    
    # Pattern to match comparison expressions: MACRO OP value
    # where OP is >, <, ==, !=, >=, <=
    comparison_pattern = re.compile(r'(\w+)\s*(>|<|==|!=|>=|<=)\s*([^&\|\)]+)')
    for match in comparison_pattern.finditer(expression):
        macro = match.group(1)
        op = match.group(2)
        value = match.group(3).strip()
        # Check if this macro was already captured as defined()
        if not any(m['name'] == macro for m in macros):
            macros.append({
                "name": macro,
                "condition": "comparison",
                "expression": f"{macro} {op} {value}"
            })
    
    # Pattern to match simple macro usage (not in defined() or comparison)
    # This catches cases like "MACRO" or "MACRO && OTHER"
    simple_pattern = re.compile(r'\b([A-Z_][A-Z0-9_]*)\b')
    for match in simple_pattern.finditer(expression):
        macro = match.group(1)
        # Skip if already captured or is a logical operator
        if macro in ['defined', 'and', 'or', 'not', '&&', '||', '!']:
            continue
        if not any(m['name'] == macro for m in macros):
            # Find the context around this macro
            start = max(0, match.start() - 10)
            end = min(len(expression), match.end() + 10)
            context = expression[start:end]
            macros.append({
                "name": macro,
                "condition": "value",
                "expression": macro
            })
    
    return macros
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/liam/.config/opencode/.worktrees/pcpp-refactor/c-macro-analyzer && source venv/bin/activate && pytest tests/test_analyzer.py::test_extract_macros_structured -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/liam/.config/opencode/.worktrees/pcpp-refactor
git add c-macro-analyzer/macro_analyzer/analyzer.py c-macro-analyzer/tests/test_analyzer.py
git commit -m "feat: implement structured macro extraction with categorization"
```

### Task 2: Write failing test for header guard filtering

**Files:**
- Modify: `c-macro-analyzer/tests/test_analyzer.py`

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/test_analyzer.py after test_extract_macros_structured
def test_header_guard_filtering():
    """Test that header guard macros (*_H* pattern) are filtered out."""
    from macro_analyzer.analyzer import PCPPAnalyzer
    
    analyzer = PCPPAnalyzer()
    
    # Test various header guard patterns
    test_cases = [
        ("defined(MY_HEADER_H)", []),  # Should be filtered
        ("defined(PROJECT_HEADER_H_)", []),  # Should be filtered
        ("!defined(HEADER_H)", []),  # Negated should also be filtered
        ("defined(HEADER_H) && defined(DEBUG)", [  # Mixed: filter header, keep DEBUG
            {"name": "DEBUG", "condition": "defined", "expression": "defined(DEBUG)"}
        ]),
        ("VERSION > 1 && defined(API_H)", [  # Mixed: filter header, keep VERSION
            {"name": "VERSION", "condition": "comparison", "expression": "VERSION > 1"}
        ]),
        ("defined(NOT_A_HEADER)", [  # Not a header guard, should keep
            {"name": "NOT_A_HEADER", "condition": "defined", "expression": "defined(NOT_A_HEADER)"}
        ]),
        ("defined(SOME_H_FILE)", [  # _H_ in middle, should filter
            {"name": "SOME_H_FILE", "condition": "defined", "expression": "defined(SOME_H_FILE)"}
        ]),
    ]
    
    for expression, expected in test_cases:
        result = analyzer._extract_macros(expression)
        assert result == expected, f"For expression '{expression}': expected {expected}, got {result}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/liam/.config/opencode/.worktrees/pcpp-refactor/c-macro-analyzer && source venv/bin/activate && pytest tests/test_analyzer.py::test_header_guard_filtering -v`
Expected: FAIL (header guards not being filtered)

- [ ] **Step 3: Add header guard filtering to implementation**

```python
# Update c-macro-analyzer/macro_analyzer/analyzer.py _extract_macros method
def _extract_macros(self, expression: str) -> List[Dict[str, str]]:
    """Extract individual macros from combined expression with categorization.
    
    Args:
        expression: Combined logical expression
        
    Returns:
        List of dicts with name, condition, and expression for each macro
    """
    import re
    
    macros = []
    
    # Pattern to match defined(macro) with optional negation
    defined_pattern = re.compile(r'(!?\s*defined\s*\(\s*(\w+)\s*\))')
    for full_match, macro in defined_pattern.findall(expression):
        # Filter header guard macros (*_H* pattern)
        if re.match(r'.*_H(_[A-Z0-9_]*)?$', macro):
            continue
        macros.append({
            "name": macro,
            "condition": "defined",
            "expression": full_match.strip()
        })
    
    # Pattern to match comparison expressions: MACRO OP value
    # where OP is >, <, ==, !=, >=, <=
    comparison_pattern = re.compile(r'(\w+)\s*(>|<|==|!=|>=|<=)\s*([^&\|\)]+)')
    for match in comparison_pattern.finditer(expression):
        macro = match.group(1)
        op = match.group(2)
        value = match.group(3).strip()
        # Filter header guard macros
        if re.match(r'.*_H(_[A-Z0-9_]*)?$', macro):
            continue
        # Check if this macro was already captured as defined()
        if not any(m['name'] == macro for m in macros):
            macros.append({
                "name": macro,
                "condition": "comparison",
                "expression": f"{macro} {op} {value}"
            })
    
    # Pattern to match simple macro usage (not in defined() or comparison)
    simple_pattern = re.compile(r'\b([A-Z_][A-Z0-9_]*)\b')
    for match in simple_pattern.finditer(expression):
        macro = match.group(1)
        # Skip if already captured or is a logical operator
        if macro in ['defined', 'and', 'or', 'not', '&&', '||', '!']:
            continue
        # Filter header guard macros
        if re.match(r'.*_H(_[A-Z0-9_]*)?$', macro):
            continue
        if not any(m['name'] == macro for m in macros):
            macros.append({
                "name": macro,
                "condition": "value",
                "expression": macro
            })
    
    return macros
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/liam/.config/opencode/.worktrees/pcpp-refactor/c-macro-analyzer && source venv/bin/activate && pytest tests/test_analyzer.py::test_header_guard_filtering -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/liam/.config/opencode/.worktrees/pcpp-refactor
git add c-macro-analyzer/macro_analyzer/analyzer.py
git commit -m "feat: add automatic header guard macro filtering"
```

## Chunk 2: Integration and End-to-End Testing

### Task 3: Update existing tests for new output format

**Files:**
- Modify: `c-macro-analyzer/tests/test_analyzer.py`

- [ ] **Step 1: Check which existing tests need updating**

Run: `cd /Users/liam/.config/opencode/.worktrees/pcpp-refactor/c-macro-analyzer && source venv/bin/activate && pytest tests/test_analyzer.py -v`
Expected: Some tests may fail due to changed output format

- [ ] **Step 2: Update test_analyze_returns_combined_expression test**

```python
# Update in tests/test_analyzer.py test_analyze_returns_combined_expression
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
```

- [ ] **Step 3: Run updated test**

Run: `cd /Users/liam/.config/opencode/.worktrees/pcpp-refactor/c-macro-analyzer && source venv/bin/activate && pytest tests/test_analyzer.py::TestPCPPAnalyzerBasic::test_analyze_returns_combined_expression -v`
Expected: PASS

- [ ] **Step 4: Update test_directive_handling test**

```python
# Update in tests/test_analyzer.py test_directive_handling
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
```

- [ ] **Step 5: Run all tests to ensure they pass**

Run: `cd /Users/liam/.config/opencode/.worktrees/pcpp-refactor/c-macro-analyzer && source venv/bin/activate && pytest tests/test_analyzer.py -v`
Expected: ALL TESTS PASS (may need to update other tests similarly)

- [ ] **Step 6: Commit**

```bash
cd /Users/liam/.config/opencode/.worktrees/pcpp-refactor
git add c-macro-analyzer/tests/test_analyzer.py
git commit -m "test: update tests for structured macro output format"
```

### Task 4: Add integration test with real C files

**Files:**
- Create: `c-macro-analyzer/tests/samples/header_guard.c`
- Modify: `c-macro-analyzer/tests/test_integration.py`

- [ ] **Step 1: Create test sample with header guards**

```c
// c-macro-analyzer/tests/samples/header_guard.c
#ifndef HEADER_GUARD_H
#define HEADER_GUARD_H

#define VERSION 2
#define DEBUG

#ifdef DEBUG
  // Debug code
  log_message("Debug");
#endif

#if VERSION > 1
  // New feature
  enable_feature();
#endif

#endif // HEADER_GUARD_H
```

- [ ] **Step 2: Write integration test**

```python
# Add to c-macro-analyzer/tests/test_integration.py
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
```

- [ ] **Step 3: Run integration test**

Run: `cd /Users/liam/.config/opencode/.worktrees/pcpp-refactor/c-macro-analyzer && source venv/bin/activate && pytest tests/test_integration.py::test_header_guard_filtering_integration -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
cd /Users/liam/.config/opencode/.worktrees/pcpp-refactor
git add c-macro-analyzer/tests/samples/header_guard.c c-macro-analyzer/tests/test_integration.py
git commit -m "test: add integration test for header guard filtering"
```

## Chunk 3: Documentation and Final Verification

### Task 5: Update README documentation

**Files:**
- Modify: `c-macro-analyzer/README.md:60-70`

- [ ] **Step 1: Update example output in README**

```markdown
### Example output
```json
{
  "file": "example.c",
  "line": 42,
  "macros": [
    {
      "name": "DEBUG",
      "condition": "defined",
      "expression": "defined(DEBUG)"
    },
    {
      "name": "VERSION", 
      "condition": "comparison",
      "expression": "VERSION > 1"
    }
  ],
  "combined_expression": "defined(DEBUG) && VERSION > 1"
}
```

**Note:** Header guard macros (matching `*_H*` pattern) are automatically filtered from the output.
```

- [ ] **Step 2: Add section about output format**

```markdown
### Output Format Details

The analyzer returns a JSON object with the following structure:

- **file**: Path to the analyzed file
- **line**: Target line number (1-indexed)
- **macros**: Array of macro information objects, each containing:
  - **name**: Macro identifier
  - **condition**: Usage type: `"defined"`, `"comparison"`, or `"value"`
  - **expression**: The specific expression fragment containing this macro
- **combined_expression**: Full logical expression combining all active conditions

**Header Guard Filtering:** Macros matching the pattern `*_H*` (e.g., `HEADER_H`, `MY_HEADER_H_`) are automatically excluded from the output, as they typically represent include guards rather than configuration macros.
```

- [ ] **Step 3: Verify README formatting**

Run: `cd /Users/liam/.config/opencode/.worktrees/pcpp-refactor/c-macro-analyzer && cat README.md | grep -A 20 "### Example output"`
Expected: See updated JSON format with structured macros

- [ ] **Step 4: Commit**

```bash
cd /Users/liam/.config/opencode/.worktrees/pcpp-refactor
git add c-macro-analyzer/README.md
git commit -m "docs: update README with new output format and header guard filtering"
```

### Task 6: Final verification and cleanup

**Files:**
- Test: All test files

- [ ] **Step 1: Run full test suite**

Run: `cd /Users/liam/.config/opencode/.worktrees/pcpp-refactor/c-macro-analyzer && source venv/bin/activate && pytest -v`
Expected: ALL TESTS PASS (24+ tests)

- [ ] **Step 2: Test CLI with sample files**

```bash
cd /Users/liam/.config/opencode/.worktrees/pcpp-refactor/c-macro-analyzer && source venv/bin/activate && python -m macro_analyzer tests/samples/simple.c 6
```
Expected: JSON output with structured macros array

```bash
cd /Users/liam/.config/opencode/.worktrees/pcpp-refactor/c-macro-analyzer && source venv/bin/activate && python -m macro_analyzer tests/samples/header_guard.c 8
```
Expected: JSON output with DEBUG macro but no HEADER_GUARD_H

- [ ] **Step 3: Verify backward compatibility**

Check that CLI interface remains unchanged:
```bash
cd /Users/liam/.config/opencode/.worktrees/pcpp-refactor/c-macro-analyzer && source venv/bin/activate && python -m macro_analyzer --help
```
Expected: Same CLI options as before

- [ ] **Step 4: Final commit**

```bash
cd /Users/liam/.config/opencode/.worktrees/pcpp-refactor
git add .
git commit -m "chore: final verification of output format fixes"
```

## Chunk 4: Plan Review and Execution

### Task 7: Plan review and execution handoff

- [ ] **Step 1: Review plan completeness**
- [ ] **Step 2: Save plan to docs**
- [ ] **Step 3: Execute plan using subagent-driven-development**

**Plan complete and saved to `docs/superpowers/plans/2026-03-21-c-macro-analyzer-output-format-fix.md`. Ready to execute?**

(End of file - total 500 lines)
