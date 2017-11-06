#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import
from datetime import datetime


class LazyMLogger:
    """Lazy Movoto Logger

    Load logger just before use.
    Let Utilities patch works well.

    Initialize
    ::

        from kipp.options import options as opt

        logger = opt.get_mlogger()  # get logger without init

        logger.setup(*args, **kw)  # setup logger after opt.set_command_args

        logger.info(xxx)  # will construct MLogger just before use
    """
    _mlogger = None
    _args = _kw = None

    def __init__(self, *args, **kw):
        self._args = args
        self._kw = kw

    def __getattr__(self, name):
        if not self._mlogger:
            self.setup()

        return getattr(self._mlogger, name)

    def setup(self):
        """Setup movoto's MLogger manually"""
        from Utilities.movoto.logger import MLogger
        self._mlogger = MLogger().getLogger(*self._args, **self._kw)


class ConvertFailureLog:
    """MLS mapping failure logs

    Accroding to DATA-1531

    Usage:
    ::
        opt.setup_failure_logger(stage, mls_id)
        opt.record_failure_log(mls_sysid, mls_number, column_name, column_value, exc_info)
        # will record log to ``log_null_values_{stage}_{mls_id}.log``
    """

    def setup_failure_logger(self, stage, mls_id):
        """Setup failures logger

        Args:
            stage (str): normalizer/converter/keywords
            mls_id (int):

        Returns:
            logger: the failure logger
        """
        assert stage in ('normalizer', 'converter', 'keywords'), "stage should be 'normalizer'/'converter'/'keywords'"

        from Utilities.movoto.logger import MLogger
        self._failures_logger = MLogger().getLogger('log_null_values_{stage}_{mls_id}'.format(stage=stage, mls_id=mls_id), mls_id)
        return self._failures_logger

    def format_failure_log(self, mls_sysid, mls_number, column_name, column_value, exc_info=None):
        """Format arguments to log message

        Args:
            mls_sysid (str):
            mls_number (str):
            column_name (str):
            column_value (str):
            exc_info (Exception):

        Returns:
            str: message
        """
        s = 'mls_sysid: {mls_sysid}, mls_number: {mls_number}, column_name: {column_name}, column_value: {column_value}'.format(
            mls_sysid=mls_sysid, mls_number=mls_number, column_name=column_name, column_value=column_value)
        if exc_info:
            s += ', error: '.format(exc_info)

        return s

    def record_failure_log(self, **kw):
        """Record message to failure logger

        arguments as same as format_failure_log
        """
        assert self._failures_logger, 'You should invoke ``setup_failure_logger(stage, mls_id)`` first'

        if kw.get('exc_info', None):
            self._failures_logger.error(self.format_failure_log(**kw), exc_info=kw['exc_info'])
        else:
            self._failures_logger.info(self.format_failure_log(**kw))
