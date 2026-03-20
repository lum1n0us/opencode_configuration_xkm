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
