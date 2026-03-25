import sys
sys.path.insert(0, '.')
from macro_analyzer.analyzer import PCPPAnalyzer
from macro_analyzer.macro_logging import LogLevel
import tempfile
import os

code = """#define DEBUG 1
#if DEBUG == 1
int x = 1;
#elif DEBUG == 2
int x = 2;
#else
int x = 3;
#endif
"""

with tempfile.NamedTemporaryFile(mode="w", suffix=".c", delete=False) as f:
    f.write(code)
    filepath = f.name

try:
    analyzer = PCPPAnalyzer(log_level=LogLevel.DEBUG)
    result = analyzer.analyze(filepath, 3)
    print("Result:", result)
finally:
    os.unlink(filepath)
