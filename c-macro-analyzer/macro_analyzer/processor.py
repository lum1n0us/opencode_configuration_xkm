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
            has_true_branch=is_true,
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
