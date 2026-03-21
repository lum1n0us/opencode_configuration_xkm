import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

import pcpp

from .logging import LogLevel, MacroLogger


@dataclass
class ConditionContext:
    type: str
    condition: str
    line: int
    active: bool
    is_else: bool = False


class PCPPAnalyzer(pcpp.Preprocessor):
    def __init__(self, log_level: LogLevel = LogLevel.QUIET):
        super().__init__()
        self.log_level = log_level
        self.logger = MacroLogger(log_level)

        self.condition_stack: List[ConditionContext] = []
        self.line_conditions: List[Dict[str, str]] = []
        self.symbols: Dict[str, Optional[str]] = {}
        self.current_line: int = 0

        self.define("__LINE__")
        self.line_directive = None

    def _combine_conditions(self) -> str:
        if not self.condition_stack:
            return ""

        active_conditions = [
            ctx.condition
            for ctx in self.condition_stack
            if ctx.active and ctx.condition
        ]
        if not active_conditions:
            return ""

        if len(active_conditions) == 1:
            return active_conditions[0]

        combined = " && ".join(
            f"({cond})"
            if any(op in cond for op in ["&&", "||", "<", ">", "==", "!=", "!"])
            else cond
            for cond in active_conditions
        )
        return combined

    def _extract_macros(self, expression: str) -> List[Dict[str, str]]:
        macros = []
        defined_pattern = re.compile(r"defined\s*\(\s*(\w+)\s*\)")
        matches = defined_pattern.findall(expression)
        for macro in matches:
            macros.append({"name": macro, "condition": "defined"})
        return macros

    def analyze(self, filepath: str, target_line: int) -> Dict[str, Any]:
        self.condition_stack = []
        self.line_conditions = []
        self.symbols = {}
        self.current_line = 0

        self.logger.verbose(f"Starting analysis of {filepath}")

        try:
            with open(filepath, "r") as f:
                content = f.read()

            self.parse(content, filepath)

            combined_expression = self._combine_conditions()
            macros = self._extract_macros(combined_expression)

            self.logger.verbose(
                f"Line {target_line} controlled by: {combined_expression}"
            )

            return {
                "file": filepath,
                "line": target_line,
                "macros": macros,
                "combined_expression": combined_expression,
            }

        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            raise
