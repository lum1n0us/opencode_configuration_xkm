import pcpp
import io

# Test pcpp line number handling
test_code = """/* Line 1 */
/* Line 2 */
#if FOO == 1
/* Line 4 */
#else
/* Line 6 */
#endif
/* Line 8 */
"""

p = pcpp.Preprocessor()
p.parse(test_code)

output = io.StringIO()
p.write(output)
print("Output:")
print(output.getvalue())

# Test with file
print("\nTesting line numbers in callbacks:")
class TestPreprocessor(pcpp.Preprocessor):
    def on_directive_handle(self, directive, toks, ifpassthru):
        print(f"Directive at line {directive.lineno}: {directive.value}")
        return super().on_directive_handle(directive, toks, ifpassthru)

p2 = TestPreprocessor()
p2.parse(test_code)
