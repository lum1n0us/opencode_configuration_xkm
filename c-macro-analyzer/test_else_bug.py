import sys
sys.path.insert(0, '.')
from macro_analyzer.analyzer import PCPPAnalyzer
from macro_analyzer.macro_logging import LogLevel

# 测试 #if/#else 分支
test_code = """#if FOO == 1
int x = 1;  // Line 2
#else
int x = 0;  // Line 4
#endif
"""

with open('/tmp/test_else.c', 'w') as f:
    f.write(test_code)

print("Testing #if/#else:")
analyzer = PCPPAnalyzer(log_level=LogLevel.DEBUG)
result = analyzer.analyze('/tmp/test_else.c', 2)
print("Line 2 result:", result)

print("\nTesting nested conditions:")
test_code2 = """#if FOO == 1
#if BAR == 1
int x = 1;
#else
int x = 2;
#endif
#else
int x = 0;
#endif
"""

with open('/tmp/test_nested.c', 'w') as f:
    f.write(test_code2)

analyzer2 = PCPPAnalyzer(log_level=LogLevel.DEBUG)
result2 = analyzer2.analyze('/tmp/test_nested.c', 3)
print("Line 3 result:", result2)
