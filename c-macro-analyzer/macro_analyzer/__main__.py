import sys
import os

# Add current directory to sys.path for direct script execution
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from macro_analyzer.cli import main

if __name__ == "__main__":
    sys.exit(main())
