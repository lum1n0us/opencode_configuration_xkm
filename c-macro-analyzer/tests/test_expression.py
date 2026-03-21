import pytest
from macro_analyzer.expression import tokenize_expression


def test_tokenize_simple_expression():
    tokens = tokenize_expression("defined(DEBUG)")
    assert tokens == ["defined", "(", "DEBUG", ")"]


def test_tokenize_complex_expression():
    tokens = tokenize_expression("(VERSION > 2) && defined(FEATURE_X)")
    assert tokens == [
        "(",
        "VERSION",
        ">",
        "2",
        ")",
        "&&",
        "defined",
        "(",
        "FEATURE_X",
        ")",
    ]


def test_tokenize_with_spaces():
    tokens = tokenize_expression("  DEBUG  &&  !RELEASE  ")
    assert tokens == ["DEBUG", "&&", "!", "RELEASE"]


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
