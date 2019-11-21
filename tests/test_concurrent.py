#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from unittest import TestCase
import time

from kipp.utils import ThreadPoolExecutor
from kipp.aio import run_until_complete, wait


class ThreadPoolExecutorTestCase(TestCase):
    def _fake_task(self):
        return 2

    def _fake_task_with_exception(self):
        raise AttributeError

    def _fake_slow_task(self):
        time.sleep(1)
        return 3

    def _fake_very_slow_task(self):
        time.sleep(4)
        return 4

    def _fake_infinite_task(self, obj):
        while not obj.is_done:
            time.sleep(1)

        time.sleep(0.1)

    def test_threadpool_result(self):
        thread_pool = ThreadPoolExecutor(1)
        future = thread_pool.submit(self._fake_task)
        run_until_complete(future)
        self.assertTrue(future.done())
        self.assertEqual(future.result(), 2)

    def test_task_exception(self):
        thread_pool = ThreadPoolExecutor(1)
        future = thread_pool.submit(self._fake_task_with_exception)
        run_until_complete(future)
        self.assertRaises(AttributeError, future.result)

    def test_slow_task(self):
        thread_pool = ThreadPoolExecutor(1)
        future = thread_pool.submit(self._fake_slow_task)
        self.assertFalse(future.done())
        run_until_complete(future)
        self.assertTrue(future.done())
        self.assertEqual(future.result(), 3)

    def test_run_on_executor(self):
        thread_pool = ThreadPoolExecutor(1)

        @thread_pool.coroutine
        def _fake_slow_task():
            time.sleep(1)
            return 3.5

        future = _fake_slow_task()
        self.assertFalse(future.done())
        run_until_complete(future)
        self.assertTrue(future.done())
        self.assertEqual(future.result(), 3.5)

    def test_run_on_executor_for_class(self):
        thread_pool = ThreadPoolExecutor(1)

        class Demo(object):
            @thread_pool.coroutine
            def _fake_slow_task(self):
                time.sleep(1)
                return 3.1

        demo = Demo()
        future = demo._fake_slow_task()
        self.assertFalse(future.done())
        run_until_complete(future)
        self.assertTrue(future.done())
        self.assertEqual(future.result(), 3.1)

    def test_wait_specified_tasks(self):
        thread_pool = ThreadPoolExecutor(1)
        future_slow = thread_pool.submit(self._fake_slow_task)
        future_very_slow = thread_pool.submit(self._fake_very_slow_task)
        start_time = time.time()
        run_until_complete(future_slow)
        end_time = time.time()
        self.assertLess(end_time - start_time, 2)
        self.assertTrue(future_slow.done())
        self.assertFalse(future_very_slow.done())
        self.assertEqual(future_slow.result(), 3)

    def test_add_multi_tasks(self):
        thread_pool = ThreadPoolExecutor(5)
        futures = [thread_pool.submit(self._fake_task) for _ in range(5)]
        run_until_complete(wait(futures))
        for f in futures:
            self.assertEqual(f.result(), 2)

    def test_shutdown_task(self):
        class obj:
            is_done = False

        thread_pool = ThreadPoolExecutor(1)
        future = thread_pool.submit(self._fake_infinite_task, obj)
        self.assertFalse(future.done())
        obj.is_done = True
        thread_pool.shutdown(wait=False)  # shutdown without wait
        self.assertFalse(future.done())
        run_until_complete(future)
        self.assertTrue(future.done())

        thread_pool = ThreadPoolExecutor(1)
        obj.is_done = False
        future = thread_pool.submit(self._fake_infinite_task, obj)
        self.assertFalse(future.done())
        obj.is_done = True
        thread_pool.shutdown()  # wait to finish
        self.assertTrue(future.done())
