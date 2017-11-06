#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
----------------------
Asynchronous SqlHelper
----------------------

TODO:

    #. Transaction


Examples:

    Simple Usage:
    ::
        from kipp.aio import SqlHelper, run_until_complete, coroutine2

        @coroutine2
        def main():
            db = SqlHelper('movoto')
            r = yield db.getOneBySql('show DATABASES;')

        if __name__ == '__main__':
            run_until_complete(main())

"""

from __future__ import unicode_literals

from kipp.libs import PY2, PY3
from kipp.utils import get_logger
from .base import run_on_executor, thread_executor


class Py3SqlHelper(object):
    pass


class Py2SqlHelper:
    executor = thread_executor

    def __init__(self, *args, **kw):
        from Utilities.movoto.SqlHelper import SqlHelper as MovotoSqlHelper
        self.sqlhelper = MovotoSqlHelper(*args, **kw)

    def __getattr__(self, name):
        return getattr(self.sqlhelper, name)

    @run_on_executor()
    def getAllBySql(self, sql, *args, **kw):
        return self.sqlhelper.getAllBySql(sql, *args, **kw)

    @run_on_executor()
    def getOneBySql(self, sql, *args, **kw):
        return self.sqlhelper.getOneBySql(sql, *args, **kw)

    @run_on_executor()
    def executeBySql(self, sql, *args, **kw):
        return self.sqlhelper.executeBySql(sql, *args, **kw)

    @run_on_executor()
    def executeManyBySql(self, sql, *args, **kw):
        return self.sqlhelper.executeManyBySql(sql, *args, **kw)

    get_all_by_sql = getAllBySql
    get_one_by_sql = getOneBySql
    execute_by_sql = executeBySql
    execute_many_by_sql = executeManyBySql


class SqlHelper:

    def __init__(self, *args, **kw):
        if PY2:
            get_logger().info('set SqlHelper for py2')
            from Utilities.movoto import settings
            print(settings)
            self.sqlhelper = Py2SqlHelper(*args, **kw)
        elif PY3:
            get_logger().info('set SqlHelper for py3')
            self.sqlhelper = Py3SqlHelper(*args, **kw)

    def __getattr__(self, name):
        return getattr(self.sqlhelper, name)
