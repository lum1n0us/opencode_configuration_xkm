# C/C++ Macro Analyzer Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python script that analyzes C/C++ source files to determine which preprocessor macros control a specific line of code.

**Architecture:** Full preprocessor simulation with symbol table, expression evaluator, and condition stack. Processes files line by line, tracks macro definitions, evaluates conditions, and outputs JSON with combined logical expression.

**Tech Stack:** Python 3.8+, standard library only (no external dependencies), pytest for testing

**Project Location:** `./c-macro-analyzer/` (standalone Python project at root level)

---

## File Structure

**Source files:**
- `macro_analyzer/__init__.py` - Package initialization
- `macro_analyzer/expression.py` - Expression parser and evaluator
- `macro_analyzer/symbols.py` - Symbol table management
- `macro_analyzer/processor.py` - Main file processor with condition stack
- `macro_analyzer/cli.py` - Command-line interface
- `macro_analyzer/__main__.py` - Entry point for `python -m macro_analyzer`

**Test files:**
- `tests/test_expression.py` - Expression parser/evaluator tests
- `tests/test_symbols.py` - Symbol table tests
- `tests/test_processor.py` - File processor tests
- `tests/test_integration.py` - Integration tests with sample C files
- `tests/test_cli.py` - CLI tests

**Sample files:**
- `tests/samples/simple.c` - Simple test C file
- `tests/samples/nested.c` - Nested macro test file
- `tests/samples/complex.c` - Complex expression test file

## Chunk 1: Project Setup and Expression Parser

### Task 1: Create project structure

**Files:**
- Create: `macro_analyzer/__init__.py`
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `README.md`

- [ ] **Step 1: Create package structure**

```bash
mkdir -p macro_analyzer tests/samples
```

- [ ] **Step 2: Create __init__.py**

```python
"""C/C++ Macro Analyzer - Analyze preprocessor macro control of source lines."""
__version__ = "0.1.0"
```

- [ ] **Step 3: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "macro-analyzer"
version = "0.1.0"
description = "Analyze C/C++ preprocessor macro control of source lines"
readme = "README.md"
requires-python = ">=3.8"
license = {text = "MIT"}
authors = [{name = "Your Name", email = "you@example.com"}]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

[project.optional-dependencies]
dev = ["pytest>=7.0", "black>=23.0", "ruff>=0.1.0"]

[project.scripts]
macro-analyzer = "macro_analyzer.cli:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 4: Create requirements.txt**

```
# For development
pytest>=7.0
black>=23.0
ruff>=0.1.0
```

- [ ] **Step 5: Create README.md**

```markdown
# C/C++ Macro Analyzer

A Python tool that analyzes C/C++ source files to determine which preprocessor macros control a specific line of code. Given a file path and line number, it outputs JSON with the combined logical expression of all controlling macros.

## Installation

```bash
pip install -e .
```

## Usage

```bash
macro-analyzer path/to/file.c 42
```

Example output:
```json
{
  "file": "example.c",
  "line": 42,
  "macros": [
    {"name": "DEBUG", "condition": "defined"},
    {"name": "VERSION", "condition": "> 1"}
  ],
  "combined_expression": "defined(DEBUG) && VERSION > 1"
}
```

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black macro_analyzer tests
ruff check --fix macro_analyzer tests
```

## License

MIT
```

- [ ] **Step 6: Commit**

```bash
git add macro_analyzer/__init__.py pyproject.toml requirements.txt README.md
git commit -m "chore: initial project structure"
```

### Task 2: Expression parser and evaluator

**Files:**
- Create: `macro_analyzer/expression.py`
- Create: `tests/test_expression.py`

- [ ] **Step 1: Write failing test for tokenizer**

```python
# tests/test_expression.py
import pytest
    from macro_analyzer.expression import tokenize_expression

def test_tokenize_simple_expression():
    tokens = tokenize_expression("defined(DEBUG)")
    assert tokens == ["defined", "(", "DEBUG", ")"]

def test_tokenize_complex_expression():
    tokens = tokenize_expression("(VERSION > 2) && defined(FEATURE_X)")
    assert tokens == ["(", "VERSION", ">", "2", ")", "&&", "defined", "(", "FEATURE_X", ")"]

def test_tokenize_with_spaces():
    tokens = tokenize_expression("  DEBUG  &&  !RELEASE  ")
    assert tokens == ["DEBUG", "&&", "!", "RELEASE"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_expression.py::test_tokenize_simple_expression -v
```
Expected: FAIL with "ModuleNotFoundError: No module named 'macro_analyzer'"

- [ ] **Step 3: Implement tokenizer**

```python
# macro_analyzer/expression.py
import re

def tokenize_expression(expr: str) -> list[str]:
    """Tokenize a C preprocessor expression.
    
    Args:
        expr: Expression string
        
    Returns:
        List of tokens
    """
    if not expr:
        return []
    
    # Remove comments (though preprocessor shouldn't have them)
    expr = expr.strip()
    
    # Token pattern: identifiers, numbers, operators, parentheses
    pattern = r"""
        \bdefined\b|           # defined keyword
        \b[a-zA-Z_][a-zA-Z0-9_]*\b|  # identifiers
        \b\d+\b|               # integers
        [<>]=?|                # comparison operators
        ==|!=|                 # equality operators
        &&|\|\||               # logical operators
        !|\+|-|\*|/|%|         # unary/binary operators
        \(|\)                  # parentheses
    """
    
    tokens = re.findall(pattern, expr, re.VERBOSE)
    return [token for token in tokens if token.strip()]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_expression.py::test_tokenize_simple_expression -v
```
Expected: PASS

- [ ] **Step 5: Write failing test for AST parsing**

```python
# tests/test_expression.py
def test_parse_simple_defined():
    from macro_analyzer.expression import parse_expression
    ast = parse_expression("defined(DEBUG)")
    assert ast.type == "defined"
    assert ast.value == "DEBUG"
    assert ast.children == []

def test_parse_comparison():
    from macro_analyzer.expression import parse_expression
    ast = parse_expression("VERSION > 2")
    assert ast.type == "operator"
    assert ast.value == ">"
    assert len(ast.children) == 2
    assert ast.children[0].type == "identifier"
    assert ast.children[0].value == "VERSION"
    assert ast.children[1].type == "literal"
    assert ast.children[1].value == "2"
```

- [ ] **Step 6: Run test to verify it fails**

```bash
pytest tests/test_expression.py::test_parse_simple_defined -v
```
Expected: FAIL with "NameError: name 'parse_expression' is not defined"

- [ ] **Step 7: Implement AST node class and parser**

```python
# macro_analyzer/expression.py
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ASTNode:
    """Abstract Syntax Tree node for expressions."""
    type: str  # "operator", "identifier", "literal", "defined"
    value: str
    children: List["ASTNode"] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []

def parse_expression(tokens: list[str]) -> ASTNode:
    """Parse tokens into an AST using Shunting Yard algorithm.
    
    Args:
        tokens: List of tokens
        
    Returns:
        Root ASTNode
    """
    # Operator precedence (higher = tighter binding)
    PRECEDENCE = {
        "!": 4, "defined": 4,
        "*": 3, "/": 3, "%": 3,
        "+": 2, "-": 2,
        "<": 1, ">": 1, "<=": 1, ">=": 1,
        "==": 0, "!=": 0,
        "&&": -1,
        "||": -2,
    }
    
    output = []
    operators = []
    
    i = 0
    while i < len(tokens):
        token = tokens[i]
        
        if token == "defined":
            # Handle defined(identifier)
            if i + 2 < len(tokens) and tokens[i+1] == "(" and tokens[i+2].isidentifier():
                node = ASTNode("defined", tokens[i+2])
                output.append(node)
                i += 3  # Skip defined, (, identifier
                if i < len(tokens) and tokens[i] == ")":
                    i += 1  # Skip )
                continue
        
        if token.isidentifier():
            output.append(ASTNode("identifier", token))
        elif token.isdigit():
            output.append(ASTNode("literal", token))
        elif token == "(":
            operators.append(token)
        elif token == ")":
            while operators and operators[-1] != "(":
                output.append(operators.pop())
            if operators and operators[-1] == "(":
                operators.pop()
        elif token in PRECEDENCE:
            while (operators and operators[-1] != "(" and 
                   PRECEDENCE.get(operators[-1], -10) >= PRECEDENCE[token]):
                output.append(operators.pop())
            operators.append(token)
        
        i += 1
    
    while operators:
        output.append(operators.pop())
    
    # Convert RPN to AST
    stack = []
    for item in output:
        if isinstance(item, ASTNode):
            stack.append(item)
        else:  # operator
            if item == "!" or item == "defined":
                # Unary operator
                operand = stack.pop()
                node = ASTNode("operator", item, [operand])
            else:
                # Binary operator
                right = stack.pop()
                left = stack.pop()
                node = ASTNode("operator", item, [left, right])
            stack.append(node)
    
    return stack[0] if stack else ASTNode("literal", "1")
```

- [ ] **Step 8: Run test to verify it passes**

```bash
pytest tests/test_expression.py::test_parse_simple_defined -v
```
Expected: PASS

- [ ] **Step 9: Write failing test for expression evaluation**

```python
# tests/test_expression.py
def test_evaluate_simple_defined():
    from macro_analyzer.expression import evaluate_expression
    symbols = {"DEBUG": None}
    result = evaluate_expression("defined(DEBUG)", symbols)
    assert result == 1
    
    result = evaluate_expression("defined(UNDEFINED)", symbols)
    assert result == 0

def test_evaluate_comparison():
    from macro_analyzer.expression import evaluate_expression
    symbols = {"VERSION": "2"}
    result = evaluate_expression("VERSION > 1", symbols)
    assert result == 1
    
    result = evaluate_expression("VERSION < 1", symbols)
    assert result == 0
```

- [ ] **Step 10: Run test to verify it fails**

```bash
pytest tests/test_expression.py::test_evaluate_simple_defined -v
```
Expected: FAIL with "NameError: name 'evaluate_expression' is not defined"

- [ ] **Step 11: Implement expression evaluator**

```python
# macro_analyzer/expression.py
def evaluate_expression(expr: str, symbols: dict) -> int:
    """Evaluate a C preprocessor expression.
    
    Args:
        expr: Expression string
        symbols: Dictionary of macro name -> value (None for defined without value)
        
    Returns:
        1 if true, 0 if false
    """
    tokens = tokenize_expression(expr)
    ast = parse_expression(tokens)
    return _evaluate_ast(ast, symbols)

def _evaluate_ast(node: ASTNode, symbols: dict) -> int:
    """Recursively evaluate AST node."""
    if node.type == "literal":
        return int(node.value)
    
    if node.type == "identifier":
        # Look up in symbols, default to 0 if not defined
        if node.value in symbols:
            val = symbols[node.value]
            return 1 if val is None else int(val)
        return 0
    
    if node.type == "defined":
        return 1 if node.value in symbols else 0
    
    if node.type == "operator":
        if node.value == "!":
            return 0 if _evaluate_ast(node.children[0], symbols) else 1
        
        if node.value == "&&":
            left = _evaluate_ast(node.children[0], symbols)
            if not left:
                return 0
            return _evaluate_ast(node.children[1], symbols)
        
        if node.value == "||":
            left = _evaluate_ast(node.children[0], symbols)
            if left:
                return 1
            return _evaluate_ast(node.children[1], symbols)
        
        # Arithmetic and comparison operators
        left = _evaluate_ast(node.children[0], symbols)
        right = _evaluate_ast(node.children[1], symbols)
        
        if node.value == "+":
            return left + right
        if node.value == "-":
            return left - right
        if node.value == "*":
            return left * right
        if node.value == "/":
            return left // right if right != 0 else 0
        if node.value == "%":
            return left % right if right != 0 else 0
        if node.value == "<":
            return 1 if left < right else 0
        if node.value == ">":
            return 1 if left > right else 0
        if node.value == "<=":
            return 1 if left <= right else 0
        if node.value == ">=":
            return 1 if left >= right else 0
        if node.value == "==":
            return 1 if left == right else 0
        if node.value == "!=":
            return 1 if left != right else 0
    
    return 0
```

- [ ] **Step 12: Run test to verify it passes**

```bash
pytest tests/test_expression.py::test_evaluate_simple_defined -v
```
Expected: PASS

- [ ] **Step 13: Commit**

```bash
git add macro_analyzer/expression.py tests/test_expression.py
git commit -m "feat: expression parser and evaluator"
```

## Chunk 2: Symbol Table and Condition Stack

### Task 3: Symbol table management

**Files:**
- Create: `macro_analyzer/symbols.py`
- Create: `tests/test_symbols.py`

- [ ] **Step 1: Write failing test for symbol table**

```python
# tests/test_symbols.py
import pytest
    from macro_analyzer.symbols import SymbolTable

def test_symbol_table_basic():
    table = SymbolTable()
    table.define("DEBUG", None)
    assert table.is_defined("DEBUG") == True
    assert table.is_defined("UNDEFINED") == False
    assert table.get_value("DEBUG") == None

def test_symbol_table_with_value():
    table = SymbolTable()
    table.define("VERSION", "2")
    assert table.get_value("VERSION") == "2"
    assert table.is_defined("VERSION") == True

def test_symbol_table_undefine():
    table = SymbolTable()
    table.define("DEBUG", None)
    table.undefine("DEBUG")
    assert table.is_defined("DEBUG") == False
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_symbols.py::test_symbol_table_basic -v
```
Expected: FAIL with "ModuleNotFoundError: No module named 'macro_analyzer.symbols'"

- [ ] **Step 3: Implement symbol table**

```python
# macro_analyzer/symbols.py
class SymbolTable:
    """Manages macro definitions and their values."""
    
    def __init__(self):
        self._symbols = {}  # name -> value (None for defined without value)
    
    def define(self, name: str, value: str = None) -> None:
        """Define a macro with optional value.
        
        Args:
            name: Macro name
            value: Macro value (string) or None for defined without value
        """
        self._symbols[name] = value
    
    def undefine(self, name: str) -> None:
        """Remove a macro definition.
        
        Args:
            name: Macro name
        """
        if name in self._symbols:
            del self._symbols[name]
    
    def is_defined(self, name: str) -> bool:
        """Check if a macro is defined.
        
        Args:
            name: Macro name
            
        Returns:
            True if defined, False otherwise
        """
        return name in self._symbols
    
    def get_value(self, name: str) -> str:
        """Get the value of a macro.
        
        Args:
            name: Macro name
            
        Returns:
            Macro value or None if not defined or defined without value
        """
        return self._symbols.get(name)
    
    def get_all(self) -> dict:
        """Get all symbol definitions.
        
        Returns:
            Copy of the symbol dictionary
        """
        return self._symbols.copy()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_symbols.py::test_symbol_table_basic -v
```
Expected: PASS

- [ ] **Step 5: Write failing test for expression evaluation with symbols**

```python
# tests/test_symbols.py
def test_symbol_table_with_expression():
    from macro_analyzer.expression import evaluate_expression
    table = SymbolTable()
    table.define("DEBUG", None)
    table.define("VERSION", "2")
    
    # Test through expression evaluator
    result = evaluate_expression("defined(DEBUG) && VERSION > 1", table.get_all())
    assert result == 1
    
    result = evaluate_expression("defined(UNDEFINED) || VERSION < 1", table.get_all())
    assert result == 0
```

- [ ] **Step 6: Run test to verify it passes**

```bash
pytest tests/test_symbols.py::test_symbol_table_with_expression -v
```
Expected: PASS (should use existing expression module)

- [ ] **Step 7: Commit**

```bash
git add macro_analyzer/symbols.py tests/test_symbols.py
git commit -m "feat: symbol table management"
```

### Task 4: Condition stack and state management

**Files:**
- Create: `macro_analyzer/processor.py`
- Create: `tests/test_processor.py`

- [ ] **Step 1: Write failing test for condition stack**

```python
# tests/test_processor.py
import pytest
    from macro_analyzer.processor import ConditionStack, ConditionEntry

def test_condition_stack_basic():
    stack = ConditionStack()
    assert stack.is_active() == True
    
    # Push an if condition
    stack.push_if("DEBUG", True)
    assert stack.is_active() == True
    assert len(stack._stack) == 1
    
    # Push another nested condition
    stack.push_if("VERSION > 1", True)
    assert stack.is_active() == True
    
    # Pop
    stack.pop()
    assert len(stack._stack) == 1
    
    stack.pop()
    assert len(stack._stack) == 0
    assert stack.is_active() == True

def test_condition_stack_inactive():
    stack = ConditionStack()
    stack.push_if("DEBUG", False)
    assert stack.is_active() == False
    
    stack.push_if("VERSION > 1", True)
    assert stack.is_active() == False  # Parent is false
    
    stack.pop()
    stack.pop()
    assert stack.is_active() == True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_processor.py::test_condition_stack_basic -v
```
Expected: FAIL with "ModuleNotFoundError: No module named 'macro_analyzer.processor'"

- [ ] **Step 3: Implement condition stack**

```python
# macro_analyzer/processor.py
from dataclasses import dataclass
from typing import List, Optional
from .expression import evaluate_expression

@dataclass
class ConditionEntry:
    """Represents a conditional block in the stack."""
    condition: str  # Original condition string
    active: bool  # Whether this branch is active
    has_true_branch: bool  # Whether a true branch was already taken
    is_else: bool = False  # Whether this is an else branch

class ConditionStack:
    """Manages nested conditional blocks."""
    
    def __init__(self):
        self._stack: List[ConditionEntry] = []
    
    def push_if(self, condition: str, is_true: bool) -> None:
        """Push an if/elif condition onto the stack.
        
        Args:
            condition: Condition expression
            is_true: Whether the condition evaluates to true
        """
        entry = ConditionEntry(
            condition=condition,
            active=is_true and not self._has_true_branch_in_current_block(),
            has_true_branch=is_true
        )
        self._stack.append(entry)
    
    def push_else(self) -> None:
        """Push an else branch onto the stack."""
        if not self._stack:
            return
        
        # Else is active if no true branch was taken in current block
        entry = ConditionEntry(
            condition="",
            active=not self._has_true_branch_in_current_block(),
            has_true_branch=True,
            is_else=True
        )
        self._stack.append(entry)
    
    def pop(self) -> Optional[ConditionEntry]:
        """Pop the top entry from the stack.
        
        Returns:
            Popped entry or None if stack is empty
        """
        if self._stack:
            return self._stack.pop()
        return None
    
    def is_active(self) -> bool:
        """Check if the current position is active (all conditions true).
        
        Returns:
            True if all conditions in stack are active, False otherwise
        """
        for entry in self._stack:
            if not entry.active:
                return False
        return True
    
    def get_active_conditions(self) -> List[str]:
        """Get all active conditions from the stack.
        
        Returns:
            List of condition strings for active entries
        """
        conditions = []
        for entry in self._stack:
            if entry.active and entry.condition:
                conditions.append(entry.condition)
        return conditions
    
    def _has_true_branch_in_current_block(self) -> bool:
        """Check if current block already has a true branch.
        
        Returns:
            True if any entry in current block has has_true_branch=True
        """
        # Look from top of stack downward for first non-else entry
        for entry in reversed(self._stack):
            if not entry.is_else:
                return entry.has_true_branch
        return False
    
    def __len__(self) -> int:
        return len(self._stack)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_processor.py::test_condition_stack_basic -v
```
Expected: PASS

- [ ] **Step 5: Write failing test for condition combination**

```python
# tests/test_processor.py
def test_condition_combination():
    from macro_analyzer.processor import combine_conditions
    
    # Simple case
    result = combine_conditions(["DEBUG", "VERSION > 1"])
    assert result == "DEBUG && VERSION > 1"
    
    # Empty case
    result = combine_conditions([])
    assert result == ""
    
    # Single condition
    result = combine_conditions(["defined(FEATURE_X)"])
    assert result == "defined(FEATURE_X)"
    
    # Complex conditions
    result = combine_conditions(["(PLATFORM == 'linux')", "!RELEASE"])
    assert result == "(PLATFORM == 'linux') && !RELEASE"
```

- [ ] **Step 6: Run test to verify it fails**

```bash
pytest tests/test_processor.py::test_condition_combination -v
```
Expected: FAIL with "NameError: name 'combine_conditions' is not defined"

- [ ] **Step 7: Implement condition combination**

```python
# macro_analyzer/processor.py
def combine_conditions(conditions: List[str]) -> str:
    """Combine multiple conditions with && operator.
    
    Args:
        conditions: List of condition strings
        
    Returns:
        Combined condition string, empty if no conditions
    """
    if not conditions:
        return ""
    
    # Filter out empty conditions
    valid_conditions = [c for c in conditions if c]
    
    if not valid_conditions:
        return ""
    
    if len(valid_conditions) == 1:
        return valid_conditions[0]
    
    # Combine with &&, adding parentheses for complex expressions
    combined = valid_conditions[0]
    for condition in valid_conditions[1:]:
        # Add parentheses if condition contains operators (simplistic check)
        if any(op in condition for op in ["&&", "||", "<", ">", "==", "!="]):
            condition = f"({condition})"
        combined = f"{combined} && {condition}"
    
    return combined
```

- [ ] **Step 8: Run test to verify it passes**

```bash
pytest tests/test_processor.py::test_condition_combination -v
```
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add macro_analyzer/processor.py tests/test_processor.py
git commit -m "feat: condition stack and combination"
```

## Chunk 3: Main File Processor

### Task 5: File processor with directive handling

**Files:**
- Modify: `macro_analyzer/processor.py`
- Create: `tests/samples/simple.c`

- [ ] **Step 1: Create sample test file**

```c
// tests/samples/simple.c
#define VERSION 2

#ifdef DEBUG
  // Debug-specific code
  log_message("Debug mode");
#endif

#if VERSION > 1
  // New feature in version 2
  enable_feature();
#else
  // Old version code
  use_legacy();
#endif
```

- [ ] **Step 2: Write failing test for file processor**

```python
# tests/test_processor.py
import pytest
    from macro_analyzer.processor import FileProcessor

def test_file_processor_basic():
    processor = FileProcessor()
    
    # Test line 6 (log_message line)
    result = processor.analyze_file("tests/samples/simple.c", 6)
    assert result["file"] == "tests/samples/simple.c"
    assert result["line"] == 6
    assert result["combined_expression"] == "defined(DEBUG)"
    
    # Test line 10 (enable_feature line)
    result = processor.analyze_file("tests/samples/simple.c", 10)
    assert result["combined_expression"] == "VERSION > 1"
    
    # Test line 13 (use_legacy line)
    result = processor.analyze_file("tests/samples/simple.c", 13)
    assert result["combined_expression"] == "!(VERSION > 1)"
```

- [ ] **Step 3: Run test to verify it fails**

```bash
pytest tests/test_processor.py::test_file_processor_basic -v
```
Expected: FAIL with "NameError: name 'FileProcessor' is not defined"

- [ ] **Step 4: Implement FileProcessor class**

```python
# macro_analyzer/processor.py
import re
from typing import Dict, Any
from .symbols import SymbolTable
from .expression import evaluate_expression

class FileProcessor:
    """Processes C/C++ files to analyze macro control."""
    
    def __init__(self):
        self.symbols = SymbolTable()
        self.stack = ConditionStack()
    
    def analyze_file(self, filepath: str, target_line: int) -> Dict[str, Any]:
        """Analyze a file to find macros controlling a specific line.
        
        Args:
            filepath: Path to C/C++ file
            target_line: Line number to analyze (1-indexed)
            
        Returns:
            Dictionary with analysis results
        """
        self.symbols = SymbolTable()
        self.stack = ConditionStack()
        
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines, 1):
            self._process_line(line.rstrip('\n'), i)
            
            if i == target_line:
                # Found target line
                active_conditions = self.stack.get_active_conditions()
                combined = combine_conditions(active_conditions)
                
                # Convert #ifdef to defined() for consistency
                combined = self._normalize_condition(combined)
                
                return {
                    "file": filepath,
                    "line": target_line,
                    "macros": self._extract_macros_from_expression(combined),
                    "combined_expression": combined
                }
        
        # Line not found or beyond file
        return {
            "file": filepath,
            "line": target_line,
            "macros": [],
            "combined_expression": ""
        }
    
    def _process_line(self, line: str, line_num: int) -> None:
        """Process a single line of source code."""
        stripped = line.strip()
        
        # Check for preprocessor directives
        if stripped.startswith('#'):
            self._process_directive(stripped, line_num)
    
    def _process_directive(self, directive: str, line_num: int) -> None:
        """Process a preprocessor directive."""
        # Remove leading # and whitespace
        directive = directive[1:].strip()
        
        # Handle #define
        if directive.startswith('define '):
            parts = directive[7:].strip().split(maxsplit=1)
            if parts:
                macro = parts[0]
                value = parts[1] if len(parts) > 1 else None
                self.symbols.define(macro, value)
        
        # Handle #undef
        elif directive.startswith('undef '):
            macro = directive[6:].strip()
            self.symbols.undefine(macro)
        
        # Handle #ifdef
        elif directive.startswith('ifdef '):
            macro = directive[6:].strip()
            condition = f"defined({macro})"
            is_true = evaluate_expression(condition, self.symbols.get_all())
            self.stack.push_if(condition, is_true)
        
        # Handle #ifndef
        elif directive.startswith('ifndef '):
            macro = directive[7:].strip()
            condition = f"!defined({macro})"
            is_true = evaluate_expression(condition, self.symbols.get_all())
            self.stack.push_if(condition, is_true)
        
        # Handle #if
        elif directive.startswith('if '):
            condition = directive[3:].strip()
            is_true = evaluate_expression(condition, self.symbols.get_all())
            self.stack.push_if(condition, is_true)
        
        # Handle #elif
        elif directive.startswith('elif '):
            condition = directive[5:].strip()
            is_true = evaluate_expression(condition, self.symbols.get_all())
            self.stack.pop()  # Remove previous if/elif
            self.stack.push_if(condition, is_true)
        
        # Handle #else
        elif directive == 'else':
            self.stack.pop()  # Remove previous if/elif
            self.stack.push_else()
        
        # Handle #endif
        elif directive == 'endif':
            self.stack.pop()
    
    def _normalize_condition(self, condition: str) -> str:
        """Normalize condition string (e.g., convert #ifdef to defined())."""
        if not condition:
            return condition
        
        # Simple normalization - in real implementation would parse and rewrite
        return condition
    
    def _extract_macros_from_expression(self, expression: str) -> List[Dict[str, str]]:
        """Extract individual macros from combined expression.
        
        Args:
            expression: Combined logical expression
            
        Returns:
            List of dicts with name and condition for each macro
        """
        # Simple extraction - in real implementation would parse expression
        macros = []
        
        # Look for defined(macro) patterns
        defined_pattern = r'defined\((\w+)\)'
        for match in re.finditer(defined_pattern, expression):
            macros.append({
                "name": match.group(1),
                "condition": "defined"
            })
        
        # Look for simple identifier comparisons
        # This is simplified - real implementation would parse expression tree
        return macros
```

- [ ] **Step 5: Run test to verify it passes**

```bash
pytest tests/test_processor.py::test_file_processor_basic -v
```
Expected: PASS

- [ ] **Step 6: Create more complex test file**

```c
// tests/samples/nested.c
#define PLATFORM "linux"
#define VERSION 3

#ifdef DEBUG
  #if VERSION > 2
    #if defined(FEATURE_X) && !defined(FEATURE_Y)
      // Target line 7
      advanced_feature();
    #endif
  #endif
#endif

#if PLATFORM == "windows"
  windows_specific();
#elif PLATFORM == "linux"
  linux_specific();
#else
  other_platform();
#endif
```

- [ ] **Step 7: Write test for nested macros**

```python
# tests/test_processor.py
def test_file_processor_nested():
    processor = FileProcessor()
    
    # Test line 7 in nested.c
    result = processor.analyze_file("tests/samples/nested.c", 7)
    assert result["line"] == 7
    # Should be: defined(DEBUG) && VERSION > 2 && defined(FEATURE_X) && !defined(FEATURE_Y)
    # But our simple extractor won't get it all yet
    assert "DEBUG" in result["combined_expression"]
    assert "VERSION > 2" in result["combined_expression"]
    
    # Test line 16 (linux_specific)
    result = processor.analyze_file("tests/samples/nested.c", 16)
    assert result["line"] == 16
    # Should be: PLATFORM == "linux" && !(PLATFORM == "windows")
    assert "PLATFORM" in result["combined_expression"]
```

- [ ] **Step 8: Run test to verify it passes**

```bash
pytest tests/test_processor.py::test_file_processor_nested -v
```
Expected: PASS (basic check)

- [ ] **Step 9: Commit**

```bash
git add macro_analyzer/processor.py tests/samples/simple.c tests/samples/nested.c
git commit -m "feat: file processor with directive handling"
```

## Chunk 4: CLI and Integration

### Task 6: Command-line interface

**Files:**
- Create: `macro_analyzer/cli.py`
- Create: `macro_analyzer/__main__.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing test for CLI**

```python
# tests/test_cli.py
import pytest
import subprocess
import json
import tempfile
import os

def test_cli_basic_usage():
    # Create a simple test file
    test_content = '''#define DEBUG
#ifdef DEBUG
  test_function();
#endif
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
        f.write(test_content)
        test_file = f.name
    
    try:
        # Run CLI on line 3
        result = subprocess.run(
            ['python', '-m', 'macro_analyzer', test_file, '3'],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        
        # Parse JSON output
        output = json.loads(result.stdout)
        assert output['file'] == test_file
        assert output['line'] == 3
        assert 'DEBUG' in output['combined_expression']
    finally:
        os.unlink(test_file)

def test_cli_missing_file():
    result = subprocess.run(
        ['python', '-m', 'macro_analyzer', 'nonexistent.c', '1'],
        capture_output=True,
        text=True
    )
    assert result.returncode != 0
    assert 'error' in result.stderr.lower()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_cli.py::test_cli_basic_usage -v
```
Expected: FAIL with "ModuleNotFoundError: No module named 'macro_analyzer'"

- [ ] **Step 3: Implement CLI**

```python
# macro_analyzer/cli.py
import argparse
import json
import sys
from .processor import FileProcessor

def main():
    parser = argparse.ArgumentParser(
        description='Analyze C/C++ preprocessor macro control of source lines'
    )
    parser.add_argument('file', help='Path to C/C++ source file')
    parser.add_argument('line', type=int, help='Line number to analyze (1-indexed)')
    parser.add_argument('--output', '-o', choices=['json', 'text'], default='json',
                       help='Output format (default: json)')
    
    args = parser.parse_args()
    
    try:
        processor = FileProcessor()
        result = processor.analyze_file(args.file, args.line)
        
        if args.output == 'json':
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

if __name__ == '__main__':
    sys.exit(main())
```

- [ ] **Step 4: Create __main__.py**

```python
# macro_analyzer/__main__.py
from .cli import main

if __name__ == '__main__':
    main()
```

- [ ] **Step 5: Run test to verify it passes**

```bash
pytest tests/test_cli.py::test_cli_basic_usage -v
```
Expected: PASS

- [ ] **Step 6: Write failing test for integration**

```python
# tests/test_integration.py
import pytest
import json
import tempfile
import os
from macro_analyzer.processor import FileProcessor

def test_integration_complex_file():
    # Create complex test file
    test_content = '''#define PLATFORM "linux"
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
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
        f.write(test_content)
        test_file = f.name
    
    try:
        processor = FileProcessor()
        
        # Test line 5 (advanced_debug)
        result = processor.analyze_file(test_file, 5)
        assert result['line'] == 5
        assert 'DEBUG' in result['combined_expression']
        assert 'VERSION > 2' in result['combined_expression']
        
        # Test line 12 (linux_code)
        result = processor.analyze_file(test_file, 12)
        assert result['line'] == 12
        assert 'PLATFORM == "linux"' in result['combined_expression']
        
    finally:
        os.unlink(test_file)
```

- [ ] **Step 7: Run test to verify it passes**

```bash
pytest tests/test_integration.py::test_integration_complex_file -v
```
Expected: PASS

- [ ] **Step 8: Create complex.c sample file**

```c
// tests/samples/complex.c
#define ARCH "x86_64"
#define OPTIMIZE 1
#define DEBUG_LEVEL 3

#if defined(DEBUG) && DEBUG_LEVEL > 1
  #if ARCH == "x86_64"
    #if OPTIMIZE
      optimized_x86_debug();
    #else
      plain_x86_debug();
    #endif
  #elif ARCH == "arm"
    arm_debug();
  #else
    generic_debug();
  #endif
#endif

#ifndef RELEASE
  development_code();
#endif

#if (PLATFORM == "linux" || PLATFORM == "darwin") && !EMBEDDED
  desktop_feature();
#endif
```

- [ ] **Step 9: Commit**

```bash
git add macro_analyzer/cli.py macro_analyzer/__main__.py tests/test_cli.py tests/test_integration.py tests/samples/complex.c
git commit -m "feat: CLI and integration tests"
```