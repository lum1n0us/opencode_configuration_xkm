import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from .expression import evaluate_expression
from .symbols import SymbolTable


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
        # Check if parent conditions are active
        parent_active = self.is_active()
        entry = ConditionEntry(
            condition=condition,
            active=is_true
            and not self._has_true_branch_in_current_block()
            and parent_active,
            has_true_branch=is_true,
        )
        self._stack.append(entry)

    def push_else(
        self, previous_condition: str = "", previous_has_true_branch: bool = False
    ) -> None:
        """Push an else branch onto the stack.

        Args:
            previous_condition: The condition from the previous if/elif
            previous_has_true_branch: Whether the previous if/elif was true
        """
        # Else is active if no true branch was taken in current block
        entry = ConditionEntry(
            condition=f"!({previous_condition})" if previous_condition else "",
            active=not previous_has_true_branch,
            has_true_branch=True,
            is_else=True,
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
        # Look from top of stack downward
        # A block is defined as consecutive entries until we hit an entry
        # that is not an else and has a condition (start of new if block)
        found_non_else = False
        for entry in reversed(self._stack):
            if not entry.is_else:
                if not found_non_else:
                    # First non-else entry from top
                    found_non_else = True
                    if entry.condition:  # This is an if/elif (has condition)
                        return entry.has_true_branch
                else:
                    # We found another non-else entry above
                    # This is a parent block, not our block
                    break
        return False

    def __len__(self) -> int:
        return len(self._stack)


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
        if any(op in condition for op in ["&&", "||", "<", ">", "==", "!=", "!"]):
            condition = f"({condition})"
        combined = f"{combined} && {condition}"

    return combined


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

        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for i, line in enumerate(lines, 1):
            self._process_line(line.rstrip("\n"), i)

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
                    "combined_expression": combined,
                }

        # Line not found or beyond file
        return {
            "file": filepath,
            "line": target_line,
            "macros": [],
            "combined_expression": "",
        }

    def _process_line(self, line: str, line_num: int) -> None:
        """Process a single line of source code."""
        stripped = line.strip()

        # Check for preprocessor directives
        if stripped.startswith("#"):
            self._process_directive(stripped, line_num)

    def _process_directive(self, directive: str, line_num: int) -> None:
        """Process a preprocessor directive."""
        # Remove leading # and whitespace
        directive = directive[1:].strip()

        # Handle #define
        if directive.startswith("define "):
            parts = directive[7:].strip().split(maxsplit=1)
            if parts:
                macro = parts[0]
                value = parts[1] if len(parts) > 1 else None
                self.symbols.define(macro, value)

        # Handle #undef
        elif directive.startswith("undef "):
            macro = directive[6:].strip()
            self.symbols.undefine(macro)

        # Handle #ifdef
        elif directive.startswith("ifdef "):
            macro = directive[6:].strip()
            condition = f"defined({macro})"
            is_true = evaluate_expression(condition, self.symbols.get_all())
            self.stack.push_if(condition, is_true)

        # Handle #ifndef
        elif directive.startswith("ifndef "):
            macro = directive[7:].strip()
            condition = f"!defined({macro})"
            is_true = evaluate_expression(condition, self.symbols.get_all())
            self.stack.push_if(condition, is_true)

        # Handle #if
        elif directive.startswith("if "):
            condition = directive[3:].strip()
            is_true = evaluate_expression(condition, self.symbols.get_all())
            self.stack.push_if(condition, is_true)

        # Handle #elif
        elif directive.startswith("elif "):
            condition = directive[5:].strip()
            is_true = evaluate_expression(condition, self.symbols.get_all())
            self.stack.pop()  # Remove previous if/elif
            self.stack.push_if(condition, is_true)

        # Handle #else
        elif directive == "else":
            # Get previous condition from the popped entry
            popped = self.stack.pop()  # Remove previous if/elif
            previous_condition = popped.condition if popped else ""
            previous_has_true_branch = popped.has_true_branch if popped else False
            self.stack.push_else(previous_condition, previous_has_true_branch)

        # Handle #endif
        elif directive == "endif":
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
        defined_pattern = r"defined\((\w+)\)"
        for match in re.finditer(defined_pattern, expression):
            macros.append({"name": match.group(1), "condition": "defined"})

        # Look for simple identifier comparisons
        # This is simplified - real implementation would parse expression tree
        return macros
