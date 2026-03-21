from macro_analyzer.expression import (
    evaluate_expression,
    tokenize_expression,
    parse_expression,
    _evaluate_ast,
)

symbols = {"PLATFORM": '"linux"', "VERSION": "3"}

# Debug step by step
tokens = tokenize_expression('PLATFORM == "linux"')
print(f"Tokens: {tokens}")

ast = parse_expression(tokens)
print(f"AST type: {ast.type}, value: {ast.value}")
print(f"Children: {[(c.type, c.value) for c in ast.children]}")

# Evaluate manually
left_node = ast.children[0]
right_node = ast.children[1]
print(f"\nLeft node: type={left_node.type}, value={left_node.value}")
print(f"Right node: type={right_node.type}, value={right_node.value}")

# Evaluate left
if left_node.type == "identifier":
    val = symbols[left_node.value]
    print(f"Left value in symbols: {val}")
    # Try to convert to int
    try:
        left_val = int(val)
        print(f"Left as int: {left_val}")
    except ValueError:
        if val.startswith('"') and val.endswith('"'):
            left_val = val[1:-1]
            print(f"Left as string (no quotes): {left_val}")
        else:
            left_val = 1 if val else 0
            print(f"Left as boolean: {left_val}")

# Evaluate right
if right_node.type == "string":
    right_val = right_node.value[1:-1]
    print(f"Right as string (no quotes): {right_val}")

# Compare
print(f"\nComparison: {left_val} == {right_val}: {left_val == right_val}")
