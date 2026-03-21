import argparse
import json
import sys
from .analyzer import PCPPAnalyzer
from .logging import LogLevel


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
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity level (-v: verbose, -vv: debug, -vvv: trace)",
    )

    args = parser.parse_args()

    # Determine log level from verbosity count
    if args.verbose == 0:
        log_level = LogLevel.QUIET
    elif args.verbose == 1:
        log_level = LogLevel.VERBOSE
    elif args.verbose == 2:
        log_level = LogLevel.DEBUG
    else:
        log_level = LogLevel.TRACE

    try:
        analyzer = PCPPAnalyzer(log_level=log_level)
        result = analyzer.analyze(args.file, args.line)

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
