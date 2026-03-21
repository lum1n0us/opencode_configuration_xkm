import logging
import sys
from enum import IntEnum


class LogLevel(IntEnum):
    QUIET = 0
    VERBOSE = 1
    DEBUG = 2
    TRACE = 3


TRACE_LEVEL = logging.DEBUG - 5
logging.addLevelName(TRACE_LEVEL, "TRACE")


class MacroLogger:
    _LOGGER_NAME = "macro_analyzer"

    _LEVEL_MAP = {
        LogLevel.QUIET: logging.WARNING,
        LogLevel.VERBOSE: logging.INFO,
        LogLevel.DEBUG: logging.DEBUG,
        LogLevel.TRACE: TRACE_LEVEL,
    }

    def __init__(self, level: LogLevel = LogLevel.QUIET):
        self.level = level
        self._logger = logging.getLogger(self._LOGGER_NAME)
        self._setup_logger()

    def _setup_logger(self) -> None:
        self._logger.handlers.clear()
        self._logger.setLevel(self._LEVEL_MAP[self.level])

        handler = logging.StreamHandler()
        handler.setStream(sys.stderr)
        handler.setFormatter(
            logging.Formatter("%(levelname)s:%(name)s:%(lineno)d - %(message)s")
        )
        self._logger.addHandler(handler)

    def verbose(self, msg: str) -> None:
        if self.level >= LogLevel.VERBOSE:
            self._logger.info(msg)

    def debug(self, msg: str) -> None:
        if self.level >= LogLevel.DEBUG:
            self._logger.debug(msg)

    def trace(self, msg: str) -> None:
        if self.level >= LogLevel.TRACE:
            self._logger.log(TRACE_LEVEL, msg)

    def error(self, msg: str) -> None:
        # Errors are always logged regardless of level
        self._logger.error(msg)
