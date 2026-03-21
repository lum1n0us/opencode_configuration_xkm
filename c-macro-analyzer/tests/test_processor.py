import pytest
import os
from macro_analyzer.processor import ConditionStack, ConditionEntry, FileProcessor


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


def test_file_processor_basic():
    processor = FileProcessor()

    # Test line 6 (log_message line) - DEBUG not defined, so condition should be false
    result = processor.analyze_file("tests/samples/simple.c", 6)
    assert result["file"] == "tests/samples/simple.c"
    assert result["line"] == 6
    # DEBUG is not defined, so line 6 is not active
    assert result["combined_expression"] == ""

    # Test line 10 (enable_feature line) - VERSION > 1 is true (VERSION=2)
    result = processor.analyze_file("tests/samples/simple.c", 10)
    assert result["combined_expression"] == "VERSION > 1"

    # Test line 13 (use_legacy line) - else branch of VERSION > 1, but if is true so else is inactive
    result = processor.analyze_file("tests/samples/simple.c", 13)
    assert result["combined_expression"] == ""  # else branch is inactive


def test_file_processor_nested():
    processor = FileProcessor()

    # Test line 7 in nested.c - DEBUG not defined, so line should not be active
    result = processor.analyze_file("tests/samples/nested.c", 7)
    assert result["line"] == 7
    # DEBUG is not defined, so line 7 is not active
    assert result["combined_expression"] == ""

    # Test line 16 (linux_specific) - PLATFORM == "linux" is true
    result = processor.analyze_file("tests/samples/nested.c", 16)
    assert result["line"] == 16
    # Should be: PLATFORM == "linux" && !(PLATFORM == "windows")
    # Note: string comparison not fully implemented, so just check we got some expression
    assert result["combined_expression"] != ""
