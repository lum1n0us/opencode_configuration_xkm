import argparse
import json
import sys
from .processor import FileProcessor


def main():
    parser = argparse.ArgumentParser(
        description="Analyze C/C++ preprocessor macro control of source lines"
    )
    parser.add_argument("file", help="Path to C/C++ source file")
    parser.add_argument("line", type=int, help="Line number to analyze (1-indexed)")
    parser.add_argument(
        "--output",
        "-o",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )

    args = parser.parse_args()

    try:
        processor = FileProcessor()
        result = processor.analyze_file(args.file, args.line)

        if args.output == "json":
            print(json.dumps(result, indent=2))
        else:
            print(f"File: {result['file']}")
            print(f"Line: {result['line']}")
            print(f"Macros: {len(result['macros'])}")
            print(f"Expression: {result['combined_expression']}")

        return 0
    except FileNotFoundError:
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
