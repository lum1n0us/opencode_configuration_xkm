from macro_analyzer.expression import evaluate_expression

symbols = {"PLATFORM": '"linux"', "VERSION": "3"}
result = evaluate_expression('PLATFORM == "linux"', symbols)
print(f'PLATFORM == "linux": {result}')

result = evaluate_expression('PLATFORM == "windows"', symbols)
print(f'PLATFORM == "windows": {result}')

# Test tokenization
from macro_analyzer.expression import tokenize_expression

tokens = tokenize_expression('PLATFORM == "linux"')
print(f"Tokens: {tokens}")
