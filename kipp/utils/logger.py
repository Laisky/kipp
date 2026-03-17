#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
----------
Kipp Utils
----------


"""

from __future__ import annotations

import sys
import time
import logging


LOGNAME = "kipp"


def get_formatter() -> logging.Formatter:
    # Uses GMT timestamps to avoid ambiguity across timezones in log output
    formatter = logging.Formatter(
        "[%(asctime)s - %(levelname)s - %(pathname)s:%(lineno)d - %(name)s] - %(message)s"
    )
    formatter.converter = time.gmtime
    return formatter


def get_stream_handler() -> logging.StreamHandler:
    formatter = get_formatter()
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    return ch


def setup_logger(logname: str, debug: bool = False) -> logging.Logger:
    """Create logger with default formatter and stream of stdout.

    Also configures tornado and concurrent loggers to ERROR level to suppress
    their verbose output during normal operation.

    Args:
        logname: the name of the logger
        debug: whether set logging level to DEBUG
    """
    logger = logging.getLogger(logname)
    log_level = logging.DEBUG if debug else logging.INFO

    stream_handler = get_stream_handler()
    # Suppress noisy third-party loggers that clutter application output
    logging.getLogger("tornado").addHandler(stream_handler)
    logging.getLogger("tornado").setLevel(logging.ERROR)
    logging.getLogger("concurrent").addHandler(stream_handler)
    logging.getLogger("concurrent").setLevel(logging.ERROR)

    logger.setLevel(log_level)
    if not logger.handlers:
        logger.addHandler(stream_handler)

    # Prevent duplicate messages from propagating to the root logger
    logger.propagate = False
    return logger


# Module-level singleton; use get_logger()/set_logger() instead of direct access
_logger: dict[str, logging.Logger] = {"ins": setup_logger(logname=LOGNAME)}


def get_logger() -> logging.Logger:
    """Get kipp internal logger"""
    return _logger["ins"]


def get_wrap_handler(target_logger: logging.Logger) -> logging.StreamHandler:
    """Create a handler that forwards records to another logger.

    This enables bridging kipp's internal logging into an external logger
    (e.g., one that writes to a file) without replacing the handler hierarchy.
    """

    class _WrapperHandler(logging.StreamHandler):
        def emit(self, record: logging.LogRecord) -> None:
            formatter = logging.Formatter("[%(levelname)s:%(name)s] %(message)s")
            target_logger.log(record.levelno, formatter.format(record))

    return _WrapperHandler()


def set_logger(logger: logging.Logger) -> None:
    """Replace kipp internal logger.

    Since of only Utilities' logger can output to file,
    so you need to replace the kipp' internal logger with Utilities' logger
    to save your logs to file.

    Usage:
    ::
        set_logger(utilities_logger)
    """
    handler = get_wrap_handler(logger)
    get_logger().addHandler(handler)
    for dep_logger_name in ("tornado", "concurrent"):
        logging.getLogger(dep_logger_name).addHandler(handler)
