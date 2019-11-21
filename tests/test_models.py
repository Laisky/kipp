#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import re
import sys
from collections import namedtuple
from datetime import datetime

from mock import MagicMock
from concurrent.futures import Future

from kipp.aio import run_until_complete
from kipp.libs import PY3
from kipp.exceptions import DBValidateError
from kipp.models import MovotoDB

from .base import BaseTestCase


class MovotoDBTestCase(BaseTestCase):
    @classmethod
    def setUpClass(cls):
        m = MagicMock()
        cls.sqlhelper = m()

        cls._RuntimeStats = namedtuple("stats", ["created_at", "updated_at", "stats"])
        cls.sqlhelper.getOneBySql.return_value = cls._RuntimeStats(
            datetime.now(), datetime.now(), "fake_stats"
        )
        cls.sqlhelper.executeBySql.return_value = True

        class MovotoModuleMock(object):
            def __getattr__(cls, name):
                return SqlHelperModuleMock()

        class UtilitiesModuleMock(object):
            def __getattr__(cls, name):
                return MovotoModuleMock()

        class SqlHelperModuleMock(object):
            def __getattr__(cls, name):
                if name == "SqlHelper":
                    return m

        sys.modules["Utilities"] = UtilitiesModuleMock()
        sys.modules["Utilities.movoto"] = MovotoModuleMock()
        sys.modules["Utilities.movoto.SqlHelper"] = SqlHelperModuleMock()

        cls.movotodb = MovotoDB()

    def replace_sql(self, val):
        val = val.strip()
        val = re.sub("[\n\b\t]", "", val)
        val = re.sub("\ +", " ", val)
        return val

    def test_create_runtime_stats(self):
        r = self.movotodb.create_runtime_stats(name="test1")
        _sql_expect = "insert into runtime_stats (name, stats) values (%s, %s);"
        _sql = self.replace_sql(self.sqlhelper.executeBySql.call_args_list[-1][0][0])
        self.assertEqual(_sql, _sql_expect)
        self.assertEqual(r, True)
        self.assertEqual(self.sqlhelper.executeBySql.call_args_list[-1][0][1], "test1")
        self.assertEqual(self.sqlhelper.executeBySql.call_args_list[-1][0][2], None)

        self.movotodb.create_runtime_stats(name="test2", stats="yeo")
        self.assertEqual(self.sqlhelper.executeBySql.call_args_list[-1][0][1], "test2")
        self.assertEqual(self.sqlhelper.executeBySql.call_args_list[-1][0][2], "yeo")

        self.assertRaises(
            DBValidateError, self.movotodb.create_runtime_stats, name=None
        )
        self.assertRaises(
            DBValidateError, self.movotodb.create_runtime_stats, name="-" * 51
        )

    def test_update_runtime_stats(self):
        r = self.movotodb.update_runtime_stats(name="test_update", stats="update_stats")
        _sql_expect = "update runtime_stats set stats=%s where name=%s;"
        _sql = self.replace_sql(self.sqlhelper.executeBySql.call_args_list[-1][0][0])
        self.assertEqual(r, True)
        self.assertEqual(_sql, _sql_expect)
        self.assertEqual(
            self.sqlhelper.executeBySql.call_args_list[-1][0][1], "update_stats"
        )
        self.assertEqual(
            self.sqlhelper.executeBySql.call_args_list[-1][0][2], "test_update"
        )

        self.assertRaises(
            DBValidateError,
            self.movotodb.update_runtime_stats,
            name="xxx",
            stats="-" * 201,
        )
        self.assertRaises(
            DBValidateError,
            self.movotodb.update_runtime_stats,
            name="xxx" * 51,
            stats="-",
        )
        self.assertRaises(
            DBValidateError, self.movotodb.update_runtime_stats, name="xxx", stats=None
        )
        self.assertRaises(
            DBValidateError, self.movotodb.update_runtime_stats, name=None, stats="-"
        )

    def test_delete_runtime_stats(self):
        r = self.movotodb.delete_runtime_stats(name="test_delete")
        _sql_expect = "delete from runtime_stats where name=%s;"
        _sql = self.replace_sql(self.sqlhelper.executeBySql.call_args_list[-1][0][0])
        self.assertEqual(r, True)
        self.assertEqual(_sql, _sql_expect)
        self.assertEqual(
            self.sqlhelper.executeBySql.call_args_list[-1][0][1], "test_delete"
        )

        self.assertRaises(
            DBValidateError, self.movotodb.delete_runtime_stats, name="xxx" * 51
        )
        self.assertRaises(
            DBValidateError, self.movotodb.delete_runtime_stats, name=None
        )

    def test_get_runtime_stats(self):
        r = self.movotodb.get_runtime_stats(name="test_get")
        _sql_expect = (
            "select created_at, updated_at, stats from runtime_stats where name=%s;"
        )
        _sql = self.replace_sql(self.sqlhelper.getOneBySql.call_args_list[-1][0][0])
        self.assertEqual(r.stats, "fake_stats")
        self.assertEqual(_sql, _sql_expect)
        self.assertEqual(
            self.sqlhelper.getOneBySql.call_args_list[-1][0][1], "test_get"
        )

        self.assertRaises(
            DBValidateError, self.movotodb.get_runtime_stats, name="xxx" * 51
        )
        self.assertRaises(DBValidateError, self.movotodb.get_runtime_stats, name=None)

    def test_aio_get_runtime_stats(self):
        aio_movotodb = MovotoDB(is_aio=True)
        f = aio_movotodb.get_runtime_stats(name="test_get")
        self.assertIsInstance(f, Future)
        run_until_complete(f)
        r = f.result()
        _sql_expect = (
            "select created_at, updated_at, stats from runtime_stats where name=%s;"
        )
        _sql = self.replace_sql(self.sqlhelper.getOneBySql.call_args_list[-1][0][0])
        self.assertEqual(r.stats, "fake_stats")
        self.assertEqual(_sql, _sql_expect)
        self.assertEqual(
            self.sqlhelper.getOneBySql.call_args_list[-1][0][1], "test_get"
        )

        self.assertRaises(
            DBValidateError, self.movotodb.get_runtime_stats, name="xxx" * 51
        )
        self.assertRaises(DBValidateError, self.movotodb.get_runtime_stats, name=None)
