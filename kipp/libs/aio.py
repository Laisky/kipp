#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
---------------------------
Asynchronous Base Interface
---------------------------

There's no need to use this module directly, you can use ``kipp.aio``
"""

from __future__ import unicode_literals
from threading import RLock
from datetime import timedelta

import tornado
from tornado.concurrent import run_on_executor
from tornado.gen import coroutine, sleep, multi, Future, Return, TimeoutError
from tornado.locks import Semaphore, Event as ToroEvent, Condition
from tornado.queues import Queue as Tornado_Queue

from .exceptions import KippAIOException, KippAIOTimeoutError


def return_in_coroutine(ret):
    """Return value in a coroutine"""
    raise tornado.gen.Return(ret)


class Event(ToroEvent):
    @coroutine
    def wait(self, timeout=None):
        """
        Args:
            timeout (int, default=None): seconds to wait for
        """
        try:
            timeout = timeout and timedelta(seconds=timeout)
            r = yield super(Event, self).wait(timeout=timeout)
        except TimeoutError as err:
            raise KippAIOTimeoutError(err)
        else:
            return_in_coroutine(r)

    def __getattr__(self, name):
        return super(Event, self).__getattr__(name)


class Queue(Tornado_Queue):
    def empty(self):
        return self.qsize() == 0


class MultiEvent(Event):
    """Event for multi workers

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
    def __init__(self, n_workers=1):
        """
        Args:
            n_workers (int, default=1): how many workers will receive this event
        """
        try:
            assert isinstance(n_workers, int), 'MultiEvent(n_workers) should be integer'
            assert n_workers >= 1, 'MultiEvent(n_workers) should greater than 1'
        except AssertionError as err:
            raise KippAIOException(err)

        self.__lock = RLock()
        self.__n_event = n_workers
        super(MultiEvent, self).__init__()

    def set(self):
        with self.__lock:
            self.__n_event -= 1
            if self.__n_event == 0:
                return super(MultiEvent, self).set()


def _get_event_loop():
    return tornado.ioloop.IOLoop()


ioloop = _get_event_loop()


def wait(futures):
    """Gather multiply futures into one future

    Returns:
        future: New future wait all child futures
            the result is a list contains the results of all child futures
    """
    return multi(set(futures))


def as_completed(futures, timeout=None):
    """Wait for futures until any future is done

    Args:
        futures (list): consists of futures
        timeout (int): max seconds to waiting for each future

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
    futures = set(futures)
    _completed = []
    _lock = RLock()
    evt = Event()

    def _set_evt(futu):
        with _lock:
            evt.set()
            _completed.append(futu)

    for futu in futures:
        futu.add_done_callback(_set_evt)

    while not all([futu.done() for futu in futures]):
        f_evt = evt.wait(timeout=timeout)
        run_until_complete(f_evt)
        f_evt.result()
        with _lock:
            while _completed:
                yield _completed.pop(0)

            evt.clear()


def get_event_loop():
    """Get current ioloop"""
    return ioloop


def _stop(future):
    ioloop.stop()


def run_until_complete(future, ioloop=ioloop):
    """Keep running untill the future is done"""
    ioloop.add_future(future, _stop)
    ioloop.start()


# simple test
if __name__ == '__main__':
    @coroutine
    def demo():
        yield sleep(1)
        print('ok')
        return_in_coroutine(2)

    future = demo()
    run_until_complete(future)
    print('result:', future.result())
