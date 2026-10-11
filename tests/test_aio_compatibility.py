"""Bounded controls for concurrent Futures and explicit Tornado loops."""

from concurrent.futures import Future
import threading
import time
import unittest

from tornado.ioloop import IOLoop

from kipp.aio import as_completed, get_event_loop, run_until_complete, wait
from kipp.utils import ThreadPoolExecutor


class AioCompatibilityTests(unittest.TestCase):
    def test_pending_thread_futures_wake_the_loop(self):
        loop = get_event_loop()
        gate = threading.Event()
        guard = loop.call_later(1, loop.stop)
        release = loop.call_later(0.05, gate.set)
        try:
            with ThreadPoolExecutor(2) as pool:
                futures = [pool.submit(lambda: (gate.wait(2), 42)[1]) for _ in range(2)]
                gathered = wait(futures + [futures[0]])
                started = time.monotonic()
                run_until_complete(gathered)
                self.assertTrue(gathered.done())
                self.assertEqual(gathered.result(), [42, 42])
                self.assertLess(time.monotonic() - started, 0.5)
        finally:
            gate.set()
            loop.remove_timeout(guard)
            loop.remove_timeout(release)

    def test_ready_futures_are_yielded_once(self):
        first, second = Future(), Future()
        first.set_result("first")
        second.set_result("second")
        self.assertCountEqual(
            [future.result() for future in as_completed([first, second, first])],
            ["first", "second"],
        )

    def test_thread_completion_keeps_exception_on_original_future(self):
        loop = get_event_loop()
        gate = threading.Event()
        release = loop.call_later(0.05, gate.set)

        def fail():
            gate.wait(2)
            raise ValueError("offline failure")

        try:
            with ThreadPoolExecutor(1) as pool:
                future = pool.submit(fail)
                completed = list(as_completed([future], timeout=1))
                self.assertEqual(completed, [future])
                with self.assertRaisesRegex(ValueError, "offline failure"):
                    completed[0].result()
        finally:
            gate.set()
            loop.remove_timeout(release)

    def test_explicit_loop_is_stopped_without_stopping_the_singleton(self):
        loop = IOLoop(make_current=False)
        future = loop.asyncio_loop.create_future()
        future.set_result("explicit")
        loop.call_later(1, loop.stop)
        started = time.monotonic()
        try:
            run_until_complete(future, ioloop=loop)
            self.assertLess(time.monotonic() - started, 0.5)
            self.assertEqual(future.result(), "explicit")
        finally:
            loop.close()


if __name__ == "__main__":
    unittest.main()
