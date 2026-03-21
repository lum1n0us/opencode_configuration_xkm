class SymbolTable:
    """Manages macro definitions and their values."""

    def __init__(self):
        self._symbols = {}  # name -> value (None for defined without value)

    def define(self, name: str, value: str = None) -> None:
        """Define a macro with optional value.

        Args:
            name: Macro name
            value: Macro value (string) or None for defined without value
        """
        self._symbols[name] = value

    def undefine(self, name: str) -> None:
        """Remove a macro definition.

        Args:
            name: Macro name
        """
        if name in self._symbols:
            del self._symbols[name]

    def is_defined(self, name: str) -> bool:
        """Check if a macro is defined.

        Args:
            name: Macro name

        Returns:
            True if defined, False otherwise
        """
        return name in self._symbols

    def get_value(self, name: str) -> str:
        """Get the value of a macro.

        Args:
            name: Macro name

        Returns:
            Macro value or None if not defined or defined without value
        """
        return self._symbols.get(name)

    def get_all(self) -> dict:
        """Get all symbol definitions.

        Returns:
            Copy of the symbol dictionary
        """
        return self._symbols.copy()
