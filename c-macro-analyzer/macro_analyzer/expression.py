import re
from dataclasses import dataclass
from typing import List, Optional


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


@dataclass
class ASTNode:
    """Abstract Syntax Tree node for expressions."""

    type: str  # "operator", "identifier", "literal", "defined"
    value: str
    children: List["ASTNode"] = None

    def __post_init__(self):
        if self.children is None:
            self.children = []


def parse_expression(expr: str) -> ASTNode:
    """Parse expression string into an AST using Shunting Yard algorithm.

    Args:
        expr: Expression string

    Returns:
        Root ASTNode
    """
    tokens = tokenize_expression(expr)
    # Operator precedence (higher = tighter binding)
    PRECEDENCE = {
        "!": 4,
        "defined": 4,
        "*": 3,
        "/": 3,
        "%": 3,
        "+": 2,
        "-": 2,
        "<": 1,
        ">": 1,
        "<=": 1,
        ">=": 1,
        "==": 0,
        "!=": 0,
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
            if (
                i + 2 < len(tokens)
                and tokens[i + 1] == "("
                and tokens[i + 2].isidentifier()
            ):
                node = ASTNode("defined", tokens[i + 2])
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
            while (
                operators
                and operators[-1] != "("
                and PRECEDENCE.get(operators[-1], -10) >= PRECEDENCE[token]
            ):
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


def evaluate_expression(expr: str, symbols: dict) -> int:
    """Evaluate a C preprocessor expression.

    Args:
        expr: Expression string
        symbols: Dictionary of macro name -> value (None for defined without value)

    Returns:
        1 if true, 0 if false
    """
    tokens = tokenize_expression(expr)
    ast = parse_expression(expr)
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
