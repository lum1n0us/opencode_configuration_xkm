import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple

import pcpp

from .logging import LogLevel, MacroLogger


@dataclass
class ConditionContext:
    """Represents a conditional block context."""

    type: str  # 'if', 'ifdef', 'ifndef', 'elif', 'else'
    condition: str  # Original condition expression
    line: int  # Line number where directive appears
    active: bool  # Whether this branch is active
    is_else: bool = False


class PCPPAnalyzer(pcpp.Preprocessor):
    """PCPP-based macro analyzer with condition tracking."""

    _RESERVED_WORDS = frozenset({"defined", "and", "or", "not"})

    def __init__(self, log_level: LogLevel = LogLevel.QUIET):
        super().__init__()
        self.logger = MacroLogger(log_level)
        self.condition_stack: List[ConditionContext] = []
        self.line_conditions: Dict[int, List[str]] = {}
        self.current_line = 0
        self.symbols: Dict[str, Optional[str]] = {}
        self.last_directive_line = 0
        self.last_directive_conditions: List[str] = []
        self.block_stack: List[Tuple[int, str]] = []  # (start_line, condition)
        self.block_ranges: List[Tuple[int, int, str]] = []  # (start, end, condition)

        # Configure pcpp to preserve comments and whitespace for line tracking
        self.define("__LINE__")
        self.line_directive = None

    def analyze(self, filepath: str, target_line: int) -> Dict[str, Any]:
        """Analyze file and return macro control information.

        Args:
            filepath: Path to C/C++ source file
            target_line: Line number to analyze (1-indexed)

        Returns:
            Dictionary with analysis results matching existing format
        """
        # Reset state for new analysis
        self.condition_stack.clear()
        self.line_conditions.clear()
        self.symbols.clear()
        self.current_line = 0
        self.block_stack.clear()
        self.block_ranges.clear()

        self.logger.verbose(f"Starting analysis of {filepath}")

        try:
            # Process the file
            with open(filepath, "r") as f:
                content = f.read()

            # Parse with pcpp
            self.parse(content, filepath)

            # Process through preprocessor to trigger callbacks
            import io

            output = io.StringIO()
            self.write(output)

            # After processing, apply block ranges to lines
            self._apply_block_ranges()

            # Get conditions for target line
            conditions = self.line_conditions.get(target_line, [])
            combined = self._combine_conditions(conditions)

            self.logger.verbose(f"Line {target_line} controlled by: {combined}")

            return {
                "file": filepath,
                "line": target_line,
                "macros": self._extract_macros(combined),
                "combined_expression": combined,
            }

        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            raise

    def _combine_conditions(self, conditions: List[str]) -> str:
        """Combine multiple conditions with && operator.

        Args:
            conditions: List of condition strings

        Returns:
            Combined condition string, empty if no conditions
        """
        if not conditions:
            return ""

        valid_conditions = [c for c in conditions if c]
        if not valid_conditions:
            return ""

        if len(valid_conditions) == 1:
            return valid_conditions[0]

        # Combine with &&, adding parentheses for complex expressions
        combined = valid_conditions[0]
        for condition in valid_conditions[1:]:
            if any(op in condition for op in ["&&", "||", "<", ">", "==", "!=", "!"]):
                condition = f"({condition})"
            combined = f"{combined} && {condition}"

        return combined

    def _extract_macros(self, expression: str) -> List[Dict[str, str]]:
        """Extract individual macros from combined expression.

        Args:
            expression: Combined logical expression

        Returns:
            List of dicts with name, condition, and expression for each macro
        """
        all_matches = []
        found_names = set()

        def is_header_guard(name: str) -> bool:
            return bool(re.match(r".*_H(_[A-Z0-9_]*)?$", name))

        # Pattern for defined(macro) or !defined(macro)
        for match in re.finditer(r"(!?\s*defined)\s*\(\s*(\w+)\s*\)", expression):
            name = match.group(2)
            if (
                name not in found_names
                and name not in self._RESERVED_WORDS
                and not is_header_guard(name)
            ):
                all_matches.append(
                    {
                        "pos": match.start(),
                        "name": name,
                        "condition": "defined",
                        "expression": f"defined({name})",
                    }
                )
                found_names.add(name)

        # Pattern for comparison expressions: MACRO OP value
        for match in re.finditer(
            r"(\w+)\s*(==|!=|<|>|<=|>=)\s*([^\s&|()]+)", expression
        ):
            name = match.group(1)
            if (
                name not in found_names
                and name not in self._RESERVED_WORDS
                and not is_header_guard(name)
            ):
                all_matches.append(
                    {
                        "pos": match.start(),
                        "name": name,
                        "condition": "comparison",
                        "expression": match.group(0),
                    }
                )
                found_names.add(name)

        # Pattern for simple macro usage (identifiers not already found)
        # Strip string literals to avoid matching content inside strings
        expr_stripped = re.sub(r'"[^"]*"', '""', expression)
        for match in re.finditer(
            r"(?<![a-zA-Z0-9_])([a-zA-Z_]\w*)(?![a-zA-Z0-9_(])", expr_stripped
        ):
            name = match.group(1)
            if (
                name not in found_names
                and name not in self._RESERVED_WORDS
                and not is_header_guard(name)
            ):
                all_matches.append(
                    {
                        "pos": match.start(),
                        "name": name,
                        "condition": "value",
                        "expression": name,
                    }
                )
                found_names.add(name)

        # Sort by position and extract results
        all_matches.sort(key=lambda x: x["pos"])
        return [{k: v for k, v in m.items() if k != "pos"} for m in all_matches]

    # Override pcpp callback methods
    def on_directive_handle(self, directive, toks, ifpassthru, precedingtoks):
        """Handle preprocessor directives."""
        # Update current line from directive
        self.current_line = directive.lineno
        self._track_line()
        self.logger.trace(f"Directive at line {directive.lineno}: {directive.value}")

        directive_name = directive.value.lower()

        if directive_name == "if":
            expr = self._extract_expression(toks)
            self._push_condition("if", expr)
            self.block_stack.append((self.current_line, expr))
            self.logger.debug(f"#{self.current_line}: Processing #if {expr}")

        elif directive_name == "ifdef":
            macro = self._extract_macro_name(toks)
            expr = f"defined({macro})"
            self._push_condition("ifdef", expr)
            self.block_stack.append((self.current_line, expr))
            self.logger.debug(f"#{self.current_line}: Processing #ifdef {macro}")

        elif directive_name == "ifndef":
            macro = self._extract_macro_name(toks)
            expr = f"!defined({macro})"
            self._push_condition("ifndef", expr)
            self.block_stack.append((self.current_line, expr))
            self.logger.debug(f"#{self.current_line}: Processing #ifndef {macro}")

        elif directive_name == "elif":
            expr = self._extract_expression(toks)
            self._pop_condition()  # Remove previous if/elif
            self._push_condition("elif", expr)
            # Update the top block with new condition
            if self.block_stack:
                self.block_stack[-1] = (self.block_stack[-1][0], expr)
            self.logger.debug(f"#{self.current_line}: Processing #elif {expr}")

        elif directive_name == "else":
            self._pop_condition()  # Remove previous if/elif
            self._push_condition("else", "", is_else=True)
            # For else, keep the same block start but mark as else
            self.logger.debug(f"#{self.current_line}: Processing #else")

        elif directive_name == "endif":
            if self.condition_stack:
                self.condition_stack.pop()
            if self.block_stack:
                start_line, condition = self.block_stack.pop()
                self.block_ranges.append((start_line, self.current_line, condition))
            self.logger.debug(f"#{self.current_line}: Processing #endif")

        elif directive_name == "define":
            # Extract macro name and value
            if toks:
                # Find macro name (first non-whitespace after directive)
                macro = None
                value_tokens = []
                for i, t in enumerate(toks[1:], 1):
                    if t.type != "CPP_WS":
                        if macro is None:
                            macro = t.value
                        else:
                            value_tokens.append(t)

                if macro:
                    value = (
                        " ".join(t.value for t in value_tokens)
                        if value_tokens
                        else None
                    )
                    self.symbols[macro] = value
                    self.logger.debug(
                        f"#{self.current_line}: Defined {macro} = {value}"
                    )

        elif directive_name == "undef":
            if toks:
                macro = self._extract_macro_name(toks)
                if macro:
                    if macro in self.symbols:
                        del self.symbols[macro]
                    self.logger.debug(f"#{self.current_line}: Undefined {macro}")

        # Call parent implementation
        return super().on_directive_handle(directive, toks, ifpassthru, precedingtoks)

    def token(self):
        """Override token method to track line numbers."""
        tok = super().token()
        if tok:
            # Update current line from token
            if tok.lineno != self.current_line:
                self.current_line = tok.lineno
                self._track_line()
            self.logger.trace(
                f"Token at line {tok.lineno}: {tok.type} = {repr(tok.value)}"
            )
        return tok

    def on_comment(self, tok):
        """Handle comment tokens."""
        # Update current line from comment
        if tok.lineno != self.current_line:
            self.current_line = tok.lineno
            self._track_line()
        self.logger.trace(f"Comment at line {tok.lineno}: {tok.value[:50]}...")
        # Call parent implementation
        return super().on_comment(tok)

    # Helper methods
    def _track_line(self):
        """Record current line's active conditions."""
        if self.current_line > 0:
            # Only record if not already recorded for this line
            if self.current_line not in self.line_conditions:
                active_conditions = []
                for ctx in self.condition_stack:
                    if ctx.active and ctx.condition:
                        active_conditions.append(ctx.condition)
                self.line_conditions[self.current_line] = active_conditions
                self.logger.trace(
                    f"Line {self.current_line} conditions: {active_conditions} (stack size: {len(self.condition_stack)})"
                )

    def _push_condition(self, cond_type: str, condition: str, is_else: bool = False):
        """Push a condition onto the stack."""
        # Determine if this condition is active
        active = True
        if not is_else and condition:
            # For non-else conditions, check if any true branch already taken in current block
            for ctx in reversed(self.condition_stack):
                if not ctx.is_else:
                    # Found the current block
                    if ctx.active:
                        active = False  # Already have an active branch
                    break

        ctx = ConditionContext(
            type=cond_type,
            condition=condition,
            line=self.current_line,
            active=active,
            is_else=is_else,
        )
        self.condition_stack.append(ctx)

    def _pop_condition(self):
        """Pop a condition from the stack."""
        if self.condition_stack:
            return self.condition_stack.pop()
        return None

    def _extract_expression(self, tokens):
        """Extract expression string from tokens."""
        if not tokens:
            return ""
        # Filter out whitespace tokens and join
        expr_tokens = [t for t in tokens if t.type != "CPP_WS"]
        if not expr_tokens:
            return ""
        # tokens contains only expression tokens (directive token is separate)
        return " ".join(t.value for t in expr_tokens)

    def _extract_macro_name(self, tokens):
        """Extract macro name from tokens."""
        if not tokens:
            return ""
        # Find first non-whitespace token
        for t in tokens:
            if t.type != "CPP_WS":
                return t.value
        return ""

    def _apply_block_ranges(self):
        """Apply block ranges to line conditions."""
        for start_line, end_line, condition in self.block_ranges:
            self.logger.trace(f"Block range: {start_line}-{end_line}: {condition}")
            # Include both start and end lines (directive lines are also controlled)
            for line in range(start_line, end_line + 1):
                if line not in self.line_conditions:
                    self.line_conditions[line] = []
                if condition and condition not in self.line_conditions[line]:
                    self.line_conditions[line].append(condition)
