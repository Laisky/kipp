#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
---------------------------
Asynchronous Base Interface
---------------------------

There's no need to use this module directly, you can use ``kipp.aio``
"""

from __future__ import annotations

from collections.abc import Callable, Generator
from threading import RLock
from datetime import timedelta
from typing import Any

import tornado
import tornado.ioloop
from tornado.concurrent import run_on_executor
from tornado.gen import coroutine, sleep, multi, Future, Return, TimeoutError
from tornado.locks import Semaphore, Event as ToroEvent, Condition
from tornado.queues import Queue as Tornado_Queue

from .exceptions import KippAIOException, KippAIOTimeoutError


def return_in_coroutine(ret: Any) -> None:
    """Return a value from a Tornado generator-based coroutine.

    Tornado's ``@coroutine`` uses ``raise Return(value)`` as the mechanism for
    returning values from generator coroutines (prior to native async/await).
    This helper hides that implementation detail behind a function call.
    """
    raise tornado.gen.Return(ret)


class Event(ToroEvent):
    """Extends Tornado's ``Event`` with a timeout that raises
    :class:`KippAIOTimeoutError` instead of Tornado's ``TimeoutError``,
    keeping exception handling consistent within the kipp ecosystem.
    """

    @coroutine  # type: ignore[misc]
    def wait(self, timeout: int | float | None = None) -> Generator[Any, Any, None]:
        """
        Args:
            timeout: Seconds to wait before raising ``KippAIOTimeoutError``.
                     ``None`` means wait indefinitely.
        """
        try:
            # Tornado expects a timedelta, not raw seconds
            timeout_td: timedelta | None = timedelta(seconds=timeout) if timeout else None
            r = yield super(Event, self).wait(timeout=timeout_td)
        except TimeoutError as err:
            raise KippAIOTimeoutError(err)
        else:
            return_in_coroutine(r)

    def __getattr__(self, name: str) -> Any:
        return super(Event, self).__getattr__(name)


class Queue(Tornado_Queue):
    """Thin wrapper adding an ``empty()`` convenience method that mirrors
    the stdlib ``queue.Queue`` interface.
    """

    def empty(self) -> bool:
        return self.qsize() == 0


class MultiEvent(Event):
    """A barrier-style event that only fires after ``set()`` has been called
    ``n_workers`` times.  Useful for fan-in synchronisation where multiple
    independent tasks must all complete before the waiter proceeds.

    Examples:
    ::
        from kipp.aio import MultiEvent

        evt = MultiEvent(3)

        evt.set()
        evt.is_set()  # False
        evt.set()
        evt.is_set()  # False
        evt.set()
        evt.is_set()  # True
    """

    def __init__(self, n_workers: int = 1) -> None:
        """
        Args:
            n_workers: Number of ``set()`` calls required to fire the event.
        """
        if not isinstance(n_workers, int):
            raise KippAIOException("MultiEvent(n_workers) must be an integer, got {}".format(type(n_workers).__name__))
        if n_workers < 1:
            raise KippAIOException("MultiEvent(n_workers) must be >= 1, got {}".format(n_workers))

        self.__lock: RLock = RLock()
        self.__n_event: int = n_workers
        super(MultiEvent, self).__init__()

    def set(self) -> None:  # type: ignore[override]
        with self.__lock:
            self.__n_event -= 1
            if self.__n_event == 0:
                return super(MultiEvent, self).set()


def _get_event_loop() -> tornado.ioloop.IOLoop:
    return tornado.ioloop.IOLoop()


# Module-level singleton IOLoop used by ``run_until_complete`` and friends.
# Deliberately separate from Tornado's global ``IOLoop.current()`` so that
# kipp's synchronous helpers don't interfere with an application-level loop.
ioloop: tornado.ioloop.IOLoop = _get_event_loop()


def wait(futures: list[Future] | set[Future]) -> Future:
    """Gather multiple futures into one future.

    Returns:
        A new future whose result is a list containing the results of all
        child futures.  Duplicates are removed via ``set()`` to avoid
        scheduling the same future twice in ``tornado.gen.multi``.
    """
    return multi(set(futures))


def as_completed(
    futures: list[Future] | set[Future],
    timeout: int | float | None = None,
) -> Generator[Future, None, None]:
    """Yield futures one-by-one in the order they complete.

    This is a blocking generator (not a coroutine) that internally pumps the
    IOLoop to wait for each completion.  It is designed for use from
    synchronous call-sites that want to process results as they arrive.

    Args:
        futures: Collection of futures to monitor.
        timeout: Max seconds to wait for *each individual* future (not total).

    Examples:
    ::
        from kipp.aio import coroutine2, sleep, as_completed

        @coroutine2
        def wait_for_seconds(sec):
            yield sleep(sec)

        futures = [
            wait_for_seconds(2),
            wait_for_seconds(1),
        ]

        for future in as_completed(futures):
            result = future.result()
            print(result)
            # >> 1
            # >> 2
    """
    futures_set: set[Future] = set(futures)
    _completed: list[Future] = []
    _lock: RLock = RLock()
    evt: Event = Event()

    def _set_evt(futu: Future) -> None:
        with _lock:
            evt.set()
            _completed.append(futu)

    for futu in futures_set:
        futu.add_done_callback(_set_evt)

    while not all([futu.done() for futu in futures_set]):
        f_evt = evt.wait(timeout=timeout)
        run_until_complete(f_evt)
        f_evt.result()
        with _lock:
            while _completed:
                yield _completed.pop(0)

            evt.clear()


def get_event_loop() -> tornado.ioloop.IOLoop:
    """Return the module-level IOLoop singleton."""
    return ioloop


def _stop(future: Future) -> None:
    ioloop.stop()


def run_until_complete(
    future: Future,
    ioloop: tornado.ioloop.IOLoop = ioloop,
) -> None:
    """Block until *future* resolves by running the IOLoop.

    Registers a done-callback that stops the loop, then starts it. The caller
    can retrieve the result via ``future.result()`` after this returns.
    """
    ioloop.add_future(future, _stop)
    ioloop.start()


# simple test
if __name__ == "__main__":

    @coroutine  # type: ignore[misc]
    def demo() -> Generator[Any, Any, None]:
        yield sleep(1)
        print("ok")
        return_in_coroutine(2)

    future = demo()
    run_until_complete(future)
    print("result:", future.result())
