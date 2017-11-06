#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals
from functools import wraps

from kipp.libs.aio import (Return, KippAIOException, as_completed, coroutine,
                           run_on_executor)
from kipp.utils import ThreadPoolExecutor, get_logger


class LazyThreadPoolExecutor:

    def __init__(self, n_workers):
        self._n_workers = n_workers
        self.threadpoolexecutor = None

    def init(self):
        self.threadpoolexecutor = ThreadPoolExecutor(self._n_workers)

    def __getattr__(self, name):
        if not self.threadpoolexecutor:
            self.init()

        return getattr(self.threadpoolexecutor, name)

    def set_n_workers(self, n_workers):
        get_logger().info('set internal thread pool to %s', n_workers)
        if self.threadpoolexecutor:
            raise KippAIOException(
                'you should not call ``set_n_workers`` when ThreadPoolExecutor is already running')

        self._n_workers = n_workers


# create the default internal workers for ``aio`` module
thread_executor = LazyThreadPoolExecutor(10)


def set_aio_n_workers(n_workers=10):
    """Change the default number of workers in ``aio`` module

    Args:
        n_workers (int, default=10): setup the number of workers
    """
    try:
        assert isinstance(n_workers, int), '``n_workers`` must be integer'
        assert n_workers > 0, '``n_workers`` must bigger than zero'
    except Exception as err:
        raise KippAIOException(err)

    get_logger().info('set_aio_n_workers for n_workers: %s', n_workers)
    thread_executor.set_n_workers(n_workers)


def coroutine2(func):
    """Catch the exception in a coroutine

    Examples:
    ::
        @coroutine2
        def demo():
            yield sleep(0.5)
    """
    @coroutine
    @wraps(func)
    def _wrap(*args, **kw):
        try:
            g = func(*args, **kw)
            coro = next(g)
            while 1:
                try:
                    r = yield coro
                except (Return, StopIteration):
                    raise
                except Exception as err:
                    coro = g.throw(err)
                else:
                    coro = g.send(r)
        except Return:
            raise
        except StopIteration:
            # According to PEP-479
            # should not raise StopIteration in a generator
            return
        except Exception as err:
            get_logger().error('kipp.aio.coroutine2 encounter error:', exc_info=True)
            raise

    return _wrap


def wrapper(func):
    """Catch the exception in a coroutine

    *Deprecated*

    Examples:
    ::
        @coroutine
        @wrapper
        def demo():
            yield sleep(0.5)
    """
    @wraps(func)
    def _wrap(*args, **kw):
        get_logger().error('`wrapper` is deprecated! Please use `coroutine2` instead.')
        try:
            g = func(*args, **kw)
            return g
        except (Return, StopIteration):
            raise
        except Exception as err:
            get_logger().error('kipp.aio.wrapper encouter error: ', exc_info=True)
            raise err

    return _wrap
