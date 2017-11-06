#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from functools import wraps

from kipp.aio import aio_internal_thread_executor


def as_coroutine(func):
    @wraps(func)
    def wrapper(*args, **kw):
        _self = args[0]
        if getattr(_self, '_executor', None):  # wrap func to future
            return _self._executor.submit(func, *args, **kw)
        else:
            return func(*args, **kw)

    return wrapper


class MySQLdbExceptionHandler:
    """Interface of the exceptions belong to MySQLdb"""

    __mysqldb_module = None

    def get_mysqldb_exception(self, name):
        if not self.__mysqldb_module:
            self.import_mysqldb()

        return getattr(self.__mysqldb_module, name)

    def import_mysqldb(self):
        import MySQLdb
        self.__mysqldb_module = MySQLdb


class BaseDB(MySQLdbExceptionHandler):

    def __init__(self, is_aio=False, executor=None):
        self._db_conn = None
        self._is_aio = is_aio
        if is_aio:
            self._executor = executor or aio_internal_thread_executor
        else:
            self._executor = None

    def get_connection(self):
        if self._db_conn:
            return self._db_conn

        self.connect_utilities_sqlhelper()
        return self._db_conn

    @property
    def conn(self):
        return self.get_connection()

    def connect_utilities_sqlhelper(self):
        from Utilities.movoto.SqlHelper import SqlHelper

        self._db_conn = SqlHelper(self.__db_name__, use_connection_pool=True)

    def __getattr__(self, name):
        return getattr(self.conn, name)

    def __exit__(self):
        self._db_conn.close()
