#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

TODO:
  - Mock MySQL
"""

from __future__ import unicode_literals

import sys
import time
from collections import namedtuple
from contextlib import contextmanager
from unittest import skipIf

from mock import patch
from tornado.escape import json_encode
from tornado.httputil import HTTPHeaders

from kipp.aio import (
    Future,
    MultiEvent,
    as_completed,
    coroutine,
    coroutine2,
    get_event_loop,
    return_in_coroutine,
    run_until_complete,
    set_aio_n_workers,
    sleep,
    wait,
    wrapper,
)
from kipp.aio.http import HTTPSessionClient, get_http_client_session
from kipp.aio.sqlhelper import SqlHelper
from kipp.exceptions import KippAIOTimeoutError
from kipp.libs import PY2, PY3, KippException
from kipp.utils import ThreadPoolExecutor, get_logger

from .base import BaseTestCase


class FakeHTTPResponse(object):
    def __init__(self):
        self.headers = HTTPHeaders({"Cookie": "a=2;b=3", "Set-Cookie": "c=3",})
        self.body = json_encode({"body": "json-body"})


class HTTPSessionClientTestCase(BaseTestCase):
    def setUp(self):
        resp = FakeHTTPResponse()
        future = Future()
        future.set_result(resp)
        self._resp = resp
        self._resp_future = future

    def _set_resp(self, resp):
        self._resp = resp

    @contextmanager
    def get_http_patch(self):
        def _response(*args, **kw):
            return self._resp_future

        with patch("tornado.httpclient.AsyncHTTPClient.fetch") as m:
            with get_http_client_session() as client:
                self.client = client
                m.side_effect = _response
                yield m

    def test_json(self):
        with self.get_http_patch() as m:
            f = self.client.post("abc", json={"request": "json"})

        run_until_complete(f)
        resp = f.result()
        self.assertEqual(json_encode({"request": "json"}), m.call_args[1]["body"])
        self.assertDictEqual({"body": "json-body"}, resp.json())

    def test_cookies(self):
        with self.get_http_patch() as m:
            f = self.client.fetch("abc", cookies={"cc": "ccc"})

        self.assertEqual("cc=ccc", m.call_args[1]["headers"]["Cookie"])
        run_until_complete(f)
        resp = f.result()
        self.assertDictEqual({"c": "3"}, resp.cookies)

    def test_rest(self):

        for method in ("get", "post", "patch", "head", "delete"):
            with self.get_http_patch() as m:
                f = getattr(self.client, method)("abc")

            self.assertEqual(m.call_args[0], ("abc",))
            self.assertPartInDict(
                {"headers": {"Connection": "keep-alive"}}, m.call_args[1]
            )
            run_until_complete(f)
            self.assertEqual(f.result().response, self._resp)


class AioTestCase(BaseTestCase):
    @coroutine
    def _simple_task(self):
        yield sleep(0.5)
        return_in_coroutine("ok")

    @coroutine
    def _task_for_sleep(self, sec):
        yield sleep(sec)
        return_in_coroutine(sec)

    def test_ioloop(self):
        ioloop = get_event_loop()

    def test_sleep(self):
        ts = time.time()
        future = self._task_for_sleep(1)
        self.assertFalse(future.done())
        run_until_complete(future)
        self.assertTrue(future.done())
        self.assertGreaterEqual(time.time() - ts, 1)

    def test_return(self):
        future = self._simple_task()
        self.assertFalse(future.done())
        run_until_complete(future)
        self.assertTrue(future.done())
        self.assertEqual(future.result(), "ok")

    def test_wait(self):
        futures = [self._simple_task() for _ in range(5)]
        self.assertFalse(any([f.done() for f in futures]))
        gathered = wait(futures)
        run_until_complete(gathered)
        self.assertTrue([r == "ok" for r in gathered.result()])

    def test_set_aio_n_workers(self):
        from kipp.aio.base import thread_executor

        set_aio_n_workers(6)
        self.assertEqual(thread_executor._n_workers, 6)
        thread_executor.submit(self._simple_task)
        self.assertRaises(KippException, set_aio_n_workers, 5)

    def test_multi_event(self):
        evt = MultiEvent(3)
        self.assertFalse(evt.is_set())
        evt.set()
        self.assertFalse(evt.is_set())
        evt.set()
        self.assertFalse(evt.is_set())
        evt.set()
        self.assertTrue(evt.is_set())

        self.assertRaises(KippException, MultiEvent, 0)
        self.assertRaises(KippException, MultiEvent, -1)
        self.assertRaises(KippException, MultiEvent, "a")

    def test_future_thread_safe(self):
        def demo():
            pass

        def _callback(f):
            pass

        @coroutine2
        def coro():
            executor = ThreadPoolExecutor(100)
            fs = []
            for _ in range(5000):
                f = executor.submit(demo)
                f.add_done_callback(_callback)
                fs.append(f)

            yield wait(fs)

        f = wait([coro() for _ in range(5)])
        run_until_complete(f)
        f.result()
        # AttributeError: 'NoneType' object has no attribute 'append'

    def test_as_completed(self):
        futures = [
            self._task_for_sleep(1.5),
            self._task_for_sleep(1.4),
            self._task_for_sleep(1.3),
            self._task_for_sleep(1.2),
            self._task_for_sleep(1.1),
            self._task_for_sleep(1),
            self._task_for_sleep(0.9),
            self._task_for_sleep(0.8),
            self._task_for_sleep(0.7),
            self._task_for_sleep(0.6),
            self._task_for_sleep(0.5),
        ]
        expect = 0.5
        for futu in as_completed(futures):
            self.assertAlmostEqual(futu.result(), expect)
            expect += 0.1

    def test_as_completed_timeout(self):
        try:
            for futu in as_completed([self._task_for_sleep(0.2)], timeout=0.1):
                pass
        except Exception as err:
            self.assertIsInstance(err, KippAIOTimeoutError)

        for futu in as_completed([self._task_for_sleep(0.2)], timeout=0.3):
            self.assertAlmostEqual(futu.result(), 0.2)


# @skipIf(not PY2, 'only support PY2 now')
@skipIf(True, "do not complete")
class AioSqlHelperTestCase(BaseTestCase):
    def setUp(self):
        if PY2:
            sys.path.insert(0, "/Users/laisky/repo/movoto")
            try:
                from Utilities.movoto import settings
            except ImportError:
                get_logger().error("Can not import utilities")
                raise

    def tearDown(self):
        sys.path.pop(0)
        for m in list(sys.modules.keys()):
            if m == "Utilities" or m.startswith("Utilities."):
                del sys.modules[m]

    def test_init_sqlhelper(self):
        @coroutine
        @wrapper
        def _test():
            sqlhelper = SqlHelper("movoto")
            return_in_coroutine("ok")

        future = _test()
        run_until_complete(future)
        self.assertEqual(future.result(), "ok")

    def test_getOneBySql(self):
        @coroutine
        @wrapper
        def _test():
            sqlhelper = SqlHelper("movoto")
            r = yield sqlhelper.get_one_by_sql("show databases;")
            return_in_coroutine(r)

        future = _test()
        run_until_complete(future)
        self.assertIsNone(future.exception())
        self.assertEqual(future.result()[0], "information_schema")

    def test_getAllBySql(self):
        @coroutine
        @wrapper
        def _test():
            sqlhelper = SqlHelper("movoto")
            r = yield sqlhelper.get_all_by_sql("show databases;")
            return_in_coroutine(r)

        future = _test()
        run_until_complete(future)
        self.assertIsNone(future.exception())
        self.assertEqual(future.result()[0][0], "information_schema")

    def test_wrapper(self):
        @coroutine
        @wrapper
        def _test():
            raise IOError

        future = _test()
        run_until_complete(future)
        self.assertRaises(IOError, future.result)
