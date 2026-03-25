import pcpp
import io

class TestPreprocessor(pcpp.Preprocessor):
    def on_directive_handle(self, directive, toks, ifpassthru, precedingtoks):
        print(f"Directive: {directive.value} at line {directive.lineno}, ifpassthru={ifpassthru}")
        return super().on_directive_handle(directive, toks, ifpassthru, precedingtoks)

# Test 1: Simple #if
print("Test 1: #if 1")
p1 = TestPreprocessor()
p1.parse("#if 1\nint x = 1;\n#endif")
print()

# Test 2: #if 0  
print("Test 2: #if 0")
p2 = TestPreprocessor()
p2.parse("#if 0\nint x = 1;\n#endif")
print()

# Test 3: #if/#elif/#else
print("Test 3: #if 0, #elif 1, #else")
p3 = TestPreprocessor()
p3.parse("#if 0\nint x = 1;\n#elif 1\nint x = 2;\n#else\nint x = 3;\n#endif")
