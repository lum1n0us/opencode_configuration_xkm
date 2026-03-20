import pytest
from macro_analyzer.processor import ConditionStack, ConditionEntry


def test_condition_stack_basic():
    stack = ConditionStack()
    assert stack.is_active() == True

    # Push an if condition
    stack.push_if("DEBUG", True)
    assert stack.is_active() == True
    assert len(stack._stack) == 1

    # Push another condition (simulating #elif after pop)
    stack.pop()  # Simulate #elif popping previous
    stack.push_if("VERSION > 1", True)
    assert stack.is_active() == True
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


def test_condition_combination():
    from macro_analyzer.processor import combine_conditions

    # Simple case
    result = combine_conditions(["DEBUG", "VERSION > 1"])
    assert result == "DEBUG && (VERSION > 1)"

    # Empty case
    result = combine_conditions([])
    assert result == ""

    # Single condition
    result = combine_conditions(["defined(FEATURE_X)"])
    assert result == "defined(FEATURE_X)"

    # Complex conditions
    result = combine_conditions(["(PLATFORM == 'linux')", "!RELEASE"])
    assert result == "(PLATFORM == 'linux') && (!RELEASE)"
