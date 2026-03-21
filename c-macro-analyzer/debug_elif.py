from macro_analyzer.processor import FileProcessor

processor = FileProcessor()
result = processor.analyze_file("tests/samples/nested.c", 16)
print("Result:", result)
print("Combined expression:", repr(result["combined_expression"]))

# Let's trace through the processing
print("\n--- Manual trace ---")
processor = FileProcessor()
with open("tests/samples/nested.c", "r") as f:
    lines = f.readlines()

for i, line in enumerate(lines, 1):
    print(f"Line {i}: {line.rstrip()}")
    processor._process_line(line.rstrip("\n"), i)
    if i >= 14 and i <= 16:
        print(
            f"  Stack: {[(e.condition, e.active, e.is_else, e.has_true_branch) for e in processor.stack._stack]}"
        )
        print(f"  Active conditions: {processor.stack.get_active_conditions()}")
    if i == 16:
        break
