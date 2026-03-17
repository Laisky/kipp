#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

from collections.abc import Callable, Generator
from functools import wraps
from time import monotonic as _monotonic
from typing import Any, TypeVar

from kipp.libs.aio import (
    Return,
    KippAIOException,
    as_completed,
    coroutine,
    run_on_executor,
)
from kipp.utils import ThreadPoolExecutor, get_logger

_F = TypeVar("_F", bound=Callable[..., Any])


class LazyThreadPoolExecutor:
    """Defers creation of the underlying ``ThreadPoolExecutor`` until first use.

    This avoids spawning threads at import time, which matters when the aio
    module is imported but never actually used (e.g. during test collection or
    CLI help output).  Once any attribute other than the ones defined on this
    class is accessed, the real executor is instantiated transparently.
    """

    def __init__(self, n_workers: int) -> None:
        self._n_workers: int = n_workers
        self.threadpoolexecutor: ThreadPoolExecutor | None = None

    def init(self) -> None:
        self.threadpoolexecutor = ThreadPoolExecutor(self._n_workers)

    def __getattr__(self, name: str) -> Any:
        if not self.threadpoolexecutor:
            self.init()

        return getattr(self.threadpoolexecutor, name)

    def set_n_workers(self, n_workers: int) -> None:
        """Must be called before the executor is first used; changing the pool
        size after threads have been spawned is not safe, so we raise instead.
        """
        get_logger().info("set internal thread pool to %s", n_workers)
        if self.threadpoolexecutor:
            raise KippAIOException(
                "you should not call ``set_n_workers`` when ThreadPoolExecutor is already running"
            )

        self._n_workers = n_workers


# Module-level singleton; shared by all coroutines that run on the executor.
thread_executor: LazyThreadPoolExecutor = LazyThreadPoolExecutor(10)


def set_aio_n_workers(n_workers: int = 10) -> None:
    """Change the default number of workers in ``aio`` module.

    Args:
        n_workers: Number of threads in the pool. Must be a positive integer.
    """
    try:
        assert isinstance(n_workers, int), "``n_workers`` must be integer"
        assert n_workers > 0, "``n_workers`` must bigger than zero"
    except Exception as err:
        raise KippAIOException(err)

    get_logger().info("set_aio_n_workers for n_workers: %s", n_workers)
    thread_executor.set_n_workers(n_workers)


def coroutine2(func: _F) -> _F:
    """Wraps a generator-based coroutine with proper exception propagation.

    Unlike the plain ``@coroutine`` decorator, this manually drives the
    generator so that exceptions raised inside yielded futures are re-thrown
    into the generator via ``g.throw()``, giving the author a chance to
    handle them with a normal try/except inside the coroutine body.

    Examples:
    ::
        @coroutine2
        def demo():
            yield sleep(0.5)
    """

    @coroutine
    @wraps(func)
    def _wrap(*args: Any, **kw: Any) -> Generator[Any, Any, None]:
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
            # PEP-479: StopIteration must not leak out of a generator;
            # swallow it so the coroutine terminates cleanly.
            return
        except Exception as err:
            get_logger().exception("kipp.aio.coroutine2 got unknown error")
            raise

    return _wrap  # type: ignore[return-value]


def wrapper(func: _F) -> _F:
    """Catch the exception in a coroutine.

    .. deprecated::
        Use :func:`coroutine2` instead. This decorator only logs a deprecation
        error and returns the generator unchanged; it does *not* drive the
        generator the way ``coroutine2`` does.

    Examples:
    ::
        @coroutine
        @wrapper
        def demo():
            yield sleep(0.5)
    """

    @wraps(func)
    def _wrap(*args: Any, **kw: Any) -> Generator[Any, Any, None]:
        get_logger().error("`wrapper` is deprecated! Please use `coroutine2` instead")
        try:
            g = func(*args, **kw)
            return g
        except (Return, StopIteration):
            raise
        except Exception as err:
            get_logger().exception("kipp.aio.wrapper got unknown error")
            raise err

    return _wrap  # type: ignore[return-value]


def async_timer(func: _F) -> _F:
    """Decorator that logs wall-clock duration of an async function.

    Uses monotonic clock for accurate elapsed-time measurement that is
    immune to system clock adjustments (NTP, DST, manual changes).
    """

    @wraps(func)
    async def wrapper(*args: Any, **kw: Any) -> Any:
        get_logger().info("{} running...".format(func.__name__))
        start_at = _monotonic()
        try:
            return await func(*args, **kw)
        finally:
            get_logger().info(
                "{} end, cost {:.2f}s".format(func.__name__, _monotonic() - start_at)
            )

    return wrapper  # type: ignore[return-value]
