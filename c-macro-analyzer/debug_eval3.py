from macro_analyzer.expression import (
    evaluate_expression,
    tokenize_expression,
    parse_expression,
    _evaluate_ast,
    ASTNode,
)

symbols = {"PLATFORM": '"linux"', "VERSION": "3"}

# Test identifier evaluation
from macro_analyzer.expression import _evaluate_ast

# Create identifier node
ident_node = ASTNode("identifier", "PLATFORM")
result = _evaluate_ast(ident_node, symbols)
print(f"Identifier PLATFORM evaluates to: {result} (type: {type(result)})")

# Create string node
string_node = ASTNode("string", '"linux"')
result = _evaluate_ast(string_node, symbols)
print(f'String "linux" evaluates to: {result} (type: {type(result)})')

# Test full expression
result = evaluate_expression('PLATFORM == "linux"', symbols)
print(f"Full expression result: {result}")
