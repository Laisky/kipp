#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
----------
Kipp Utils
----------


"""

from __future__ import unicode_literals
import sys
import time
import logging


LOGNAME = 'kipp'  # kipp internal logger name


def get_formatter():
    formatter = logging.Formatter('[%(asctime)sZ - %(levelname)s - %(name)s] - %(message)s')
    formatter.converter = time.gmtime
    return formatter


def get_stream_handler():
    formatter = get_formatter()
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    return ch


def setup_logger(logname, debug=False):
    """Create logger with default formatter and stream of stdout

    Args:
        logname (str): the name of the logger
        debug (bool, default=False): whether set logging level to DEBUG
    """
    logger = logging.getLogger(logname)
    log_level = logging.DEBUG if debug else logging.INFO

    # logger.setLevel(logging.DEBUG)
    # logger.setLevel(log_level)
    stream_handler = get_stream_handler()
    logging.getLogger('tornado').addHandler(stream_handler)
    logging.getLogger('tornado').setLevel(logging.ERROR)
    logging.getLogger('concurrent').addHandler(stream_handler)
    logging.getLogger('concurrent').setLevel(logging.ERROR)

    # root_logger = logging.getLogger()
    logger.setLevel(log_level)
    if not logger.handlers:
        logger.addHandler(stream_handler)

    return logger


_logger = {  # do not change directly
    'ins': setup_logger(logname=LOGNAME)
}


def get_logger():
    """Get kipp internal logger"""
    return _logger['ins']


def get_wrap_handler(target_logger):
    class _WrapperHandler(logging.StreamHandler):
        def emit(self, record):
            formatter = logging.Formatter('[%(levelname)s:%(name)s] %(message)s')
            target_logger.log(record.levelno, formatter.format(record))

    return _WrapperHandler()


def set_logger(logger):
    """Replace kipp internal logger

    Since of only Utilities' logger can output to file,
    so you need to replace the kipp' internal logger with Utilities' logger
    to save your logs to file.

    Usage:
    ::
        set_logger(utilities_logger)
    """
    handler = get_wrap_handler(logger)
    get_logger().addHandler(handler)
    for dep_logger_name in ('tornado', 'concurrent'):
        logging.getLogger(dep_logger_name).addHandler(handler)
