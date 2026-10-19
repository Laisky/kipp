#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
----------------------------------------
Compatible Pool Executors for Python 2/3
----------------------------------------


Usage
::

    from kipp.utils import ThreadPoolExecutor, ProcessPoolExecutor
    from kipp.aio import run_until_complete, wait


    # initialize thread pool
    executor = ThreadPoolExecutor(max_workers)
    # or
    # executor = ProcessPoolExecutor(max_workers)

    # submit task into thread pool
    future = executor.submit(func, *args, **kargs)

    # wait all task done
    run_until_complete(future)

    # check is task done
    future.done()  # return True/False

    # get task's result
    # could raise Exception from task
    future.result()


If you want to wait a group of specified tasks
::
    future1 = executor.submit(func, *args, **kargs)
    future2 = executor.submit(func, *args, **kargs)

    run_until_complete(wait([future1, future2]))


If you want to write a worker with infinite loop, you should use ``executor.is_killed``
::

    def worker(is_killed):
        while not is_killed():
            # do your work


    executor = ThreadPoolExecutor(10)
    executor.add_done_callback(worker, executor.is_killed)

    # kill executor
    executor.shutdown()

Wrap normal functions to coroutine
::
    from time import sleep

    @executor.coroutine
    def block_task():
        time.sleep(10)  # slow task


    future = block_task()
    run_until_complete(future)


Mixing executor task and coroutine
::
    from kipp.aio import coroutine2, run_until_complete

    @executor.coroutine
    def block_task():
        time.sleep(10)  # slow task

    @coroutine2
    def coroutine_demo():
        yield block_task()  # yield a executor task


    run_until_complete(coroutine_demo())

"""
from __future__ import annotations

from typing import Any
from collections.abc import Callable
from functools import wraps

from concurrent.futures import (
    Future,
    ThreadPoolExecutor as OriginThreadPoolExecutor,
    ProcessPoolExecutor as OriginProcessPoolExecutor,
)


class KippPoolMixin:
    """Mixin that adds a ``coroutine`` decorator to pool executors.

    This lets callers turn any blocking function into an async-compatible
    call that returns a Future, bridging sync code into the executor model.
    """

    def coroutine(self, func: Callable[..., Any]) -> Callable[..., Future[Any]]:
        """Wrap a blocking function so each call submits it to the pool.

        The decorated function returns a Future instead of blocking the caller.
        """

        @wraps(func)
        def wrapper(*args: Any, **kw: Any) -> Future[Any]:
            return self.submit(func, *args, **kw)  # type: ignore[attr-defined]

        return wrapper


class ThreadPoolExecutor(KippPoolMixin, OriginThreadPoolExecutor):
    pass


class ProcessPoolExecutor(KippPoolMixin, OriginProcessPoolExecutor):
    pass
