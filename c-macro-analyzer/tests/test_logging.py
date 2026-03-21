import logging
from io import StringIO
from macro_analyzer.logging import MacroLogger, LogLevel, TRACE_LEVEL


def test_loglevel_enum_values():
    assert LogLevel.QUIET.value == 0
    assert LogLevel.VERBOSE.value == 1
    assert LogLevel.DEBUG.value == 2
    assert LogLevel.TRACE.value == 3


def test_macro_logger_initialization_default():
    logger = MacroLogger()
    assert logger.level == LogLevel.QUIET


def test_macro_logger_initialization_with_level():
    logger = MacroLogger(LogLevel.VERBOSE)
    assert logger.level == LogLevel.VERBOSE

    logger = MacroLogger(LogLevel.DEBUG)
    assert logger.level == LogLevel.DEBUG

    logger = MacroLogger(LogLevel.TRACE)
    assert logger.level == LogLevel.TRACE


def test_macro_logger_methods_exist():
    logger = MacroLogger()
    assert hasattr(logger, "verbose")
    assert hasattr(logger, "debug")
    assert hasattr(logger, "trace")
    assert hasattr(logger, "error")


def test_logging_level_filtering():
    """Test that messages are filtered based on log level."""
    # Test QUIET level - only errors should appear
    logger = MacroLogger(LogLevel.QUIET)
    output = StringIO()

    # Replace stderr handler with StringIO for testing
    logger._logger.handlers.clear()
    handler = logging.StreamHandler(output)
    handler.setFormatter(logging.Formatter("%(levelname)s:%(message)s"))
    logger._logger.addHandler(handler)

    logger.verbose("VERBOSE message")
    logger.debug("DEBUG message")
    logger.trace("TRACE message")
    logger.error("ERROR message")

    output_str = output.getvalue()
    assert "ERROR:ERROR message" in output_str
    assert "INFO:VERBOSE message" not in output_str
    assert "DEBUG:DEBUG message" not in output_str
    assert "TRACE:TRACE message" not in output_str


def test_logging_verbose_level():
    """Test VERBOSE level includes INFO and ERROR but not DEBUG/TRACE."""
    logger = MacroLogger(LogLevel.VERBOSE)
    output = StringIO()

    logger._logger.handlers.clear()
    handler = logging.StreamHandler(output)
    handler.setFormatter(logging.Formatter("%(levelname)s:%(message)s"))
    logger._logger.addHandler(handler)

    logger.verbose("VERBOSE message")
    logger.debug("DEBUG message")
    logger.trace("TRACE message")
    logger.error("ERROR message")

    output_str = output.getvalue()
    assert "INFO:VERBOSE message" in output_str
    assert "ERROR:ERROR message" in output_str
    assert "DEBUG:DEBUG message" not in output_str
    assert "TRACE:TRACE message" not in output_str


def test_logging_debug_level():
    """Test DEBUG level includes DEBUG, INFO, ERROR but not TRACE."""
    logger = MacroLogger(LogLevel.DEBUG)
    output = StringIO()

    logger._logger.handlers.clear()
    handler = logging.StreamHandler(output)
    handler.setFormatter(logging.Formatter("%(levelname)s:%(message)s"))
    logger._logger.addHandler(handler)

    logger.verbose("VERBOSE message")
    logger.debug("DEBUG message")
    logger.trace("TRACE message")
    logger.error("ERROR message")

    output_str = output.getvalue()
    assert "INFO:VERBOSE message" in output_str
    assert "DEBUG:DEBUG message" in output_str
    assert "ERROR:ERROR message" in output_str
    assert "TRACE:TRACE message" not in output_str


def test_logging_trace_level():
    """Test TRACE level includes all messages."""
    logger = MacroLogger(LogLevel.TRACE)
    output = StringIO()

    logger._logger.handlers.clear()
    handler = logging.StreamHandler(output)
    handler.setFormatter(logging.Formatter("%(levelname)s:%(message)s"))
    logger._logger.addHandler(handler)

    logger.verbose("VERBOSE message")
    logger.debug("DEBUG message")
    logger.trace("TRACE message")
    logger.error("ERROR message")

    output_str = output.getvalue()
    assert "INFO:VERBOSE message" in output_str
    assert "DEBUG:DEBUG message" in output_str
    assert "TRACE:TRACE message" in output_str
    assert "ERROR:ERROR message" in output_str


def test_error_always_logged():
    """Test that error messages are always logged regardless of level."""
    for level in [LogLevel.QUIET, LogLevel.VERBOSE, LogLevel.DEBUG, LogLevel.TRACE]:
        logger = MacroLogger(level)
        output = StringIO()

        logger._logger.handlers.clear()
        handler = logging.StreamHandler(output)
        handler.setFormatter(logging.Formatter("%(levelname)s:%(message)s"))
        logger._logger.addHandler(handler)

        logger.error(f"ERROR at level {level.name}")

        output_str = output.getvalue()
        assert f"ERROR:ERROR at level {level.name}" in output_str


def test_trace_level_custom():
    """Test that TRACE level uses custom logging level."""
    logger = MacroLogger(LogLevel.TRACE)
    assert logger._logger.getEffectiveLevel() == TRACE_LEVEL
