import sys
sys.path.insert(0, '.')
from macro_analyzer.analyzer import PCPPAnalyzer
from macro_analyzer.macro_logging import LogLevel

# 修改 analyzer 来调试
class DebugPCPPAnalyzer(PCPPAnalyzer):
    def analyze(self, filepath, target_line):
        result = super().analyze(filepath, target_line)
        
        # 添加调试信息
        print(f"\n=== DEBUG for line {target_line} ===")
        print(f"line_contexts keys: {list(self.line_contexts.keys())[:10]}...")
        
        contexts = self.line_contexts.get(target_line, [])
        print(f"Number of contexts for line {target_line}: {len(contexts)}")
        for i, ctx in enumerate(contexts):
            print(f"  Context {i}: type={ctx.type}, condition={ctx.condition}, line={ctx.line}, active={ctx.active}")
        
        return result

analyzer = DebugPCPPAnalyzer(log_level=LogLevel.QUIET)
result = analyzer.analyze('/Users/liam/warehouse/wasm-micro-runtime/core/iwasm/interpreter/wasm_loader.c', 1220)
print(f"\nResult condition_blocks: {result['condition_blocks']}")
