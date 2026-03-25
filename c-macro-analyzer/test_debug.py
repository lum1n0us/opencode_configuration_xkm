import sys
sys.path.insert(0, '.')
from macro_analyzer.analyzer import PCPPAnalyzer
from macro_analyzer.macro_logging import LogLevel

# Create a simple test file
test_content = """#line 100 "test.c"
int main() {
#if FOO == 1
    return 1;
#else
    return 0;
#endif
}
"""

with open('/tmp/test_debug.c', 'w') as f:
    f.write(test_content)

analyzer = PCPPAnalyzer(log_level=LogLevel.DEBUG)
result = analyzer.analyze('/tmp/test_debug.c', 103)
print("Result:", result)
