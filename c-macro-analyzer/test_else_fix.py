import sys
sys.path.insert(0, '.')
from macro_analyzer.analyzer import PCPPAnalyzer
from macro_analyzer.macro_logging import LogLevel

# 测试 #if/#else 分支
test_code = '''#if FOO == 1
int x = 1;  // Line 2
#else
int x = 0;  // Line 4
#endif
'''

with open('/tmp/test_else_fix.c', 'w') as f:
    f.write(test_code)

print("Testing #if/#else:")
analyzer = PCPPAnalyzer(log_level=LogLevel.DEBUG)
result = analyzer.analyze('/tmp/test_else_fix.c', 2)
print("Line 2 result:", result)

result2 = analyzer.analyze('/tmp/test_else_fix.c', 4)
print("\nLine 4 result:", result2)
