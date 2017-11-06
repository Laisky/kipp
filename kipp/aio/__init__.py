#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
---------------------------------
Asynchronous Compatibility Module
---------------------------------

Notify: You should run ``pip install "kipp[aio]"`` to install requirements.

Examples:

    Write your own coroutine:
    ::
        from kipp.aio import (
            get_event_loop, coroutine2, sleep,
            run_until_complete, wrapper, wait,
            set_aio_n_workers
        )


        @coroutine2
        def sub_task():
            yield sleep(0.5)
            return_in_coroutine('subtask ok')

        @coroutine2
        def demo():
            r = yield sub_task
            assert r == 'subtask ok'

            yield sleep(0.5)
            return_in_coroutine('ok')


        future = demo()

        # wait future done
        run_until_complete(future)

        # get the result
        result = future.result()
        assert result == 'ok'

        # Run many tasks
        futures = [demo() for _ in range(10)]
        gathered_future = wait(futures)
        run_until_complete(gathered_future)

        assert([r=='ok' for r in gathered_future.result()])

"""

from __future__ import unicode_literals

from kipp.libs.aio import (
    Future, sleep, coroutine,
    get_event_loop, run_until_complete,
    return_in_coroutine,
    Semaphore, Event, MultiEvent,Condition,
    Queue, wait)
from .base import (
    wrapper, set_aio_n_workers, coroutine2,
    thread_executor as aio_internal_thread_executor,
    as_completed,)
from .sqlhelper import SqlHelper
from .http import HTTPSessionClient, get_http_client_session
