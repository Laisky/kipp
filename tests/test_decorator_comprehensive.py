from __future__ import annotations

import os
import signal
import tempfile
import threading
import time as time_module
import unittest
from unittest.mock import MagicMock, patch

from kipp.decorator import (
    CacheItem,
    TimeoutError,
    calculate_args_hash,
    debug_wrapper,
    memo,
    retry,
    single_instance,
    timeout,
    timeout_cache,
    timer,
)


class TestRetrySuccessPath(unittest.TestCase):
    @patch("kipp.decorator._time_module.sleep")
    def test_succeeds_first_try_no_sleep(self, mock_sleep: MagicMock) -> None:
        call_count = 0

        @retry(ValueError, tries=3, delay=1, backoff=2)
        def succeed() -> str:
            nonlocal call_count
            call_count += 1
            return "ok"

        self.assertEqual(succeed(), "ok")
        self.assertEqual(call_count, 1)
        mock_sleep.assert_not_called()

    @patch("kipp.decorator._time_module.sleep")
    def test_retries_then_succeeds_on_last_attempt(self, mock_sleep: MagicMock) -> None:
        call_count = 0

        @retry(ValueError, tries=3, delay=1, backoff=2)
        def fail_twice() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("not yet")
            return "ok"

        self.assertEqual(fail_twice(), "ok")
        self.assertEqual(call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)

    @patch("kipp.decorator._time_module.sleep")
    def test_retries_once_then_succeeds(self, mock_sleep: MagicMock) -> None:
        call_count = 0

        @retry(ValueError, tries=3, delay=0.5, backoff=1)
        def fail_once() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("first fail")
            return "recovered"

        self.assertEqual(fail_once(), "recovered")
        self.assertEqual(call_count, 2)
        mock_sleep.assert_called_once_with(0.5)

    @patch("kipp.decorator._time_module.sleep")
    def test_preserves_return_value_types(self, mock_sleep: MagicMock) -> None:
        @retry(Exception, tries=2, delay=0)
        def return_complex() -> dict:
            return {"key": [1, 2, 3]}

        self.assertEqual(return_complex(), {"key": [1, 2, 3]})

    @patch("kipp.decorator._time_module.sleep")
    def test_passes_args_and_kwargs_through(self, mock_sleep: MagicMock) -> None:
        @retry(Exception, tries=2, delay=0)
        def add(a: int, b: int, extra: int = 0) -> int:
            return a + b + extra

        self.assertEqual(add(1, 2, extra=10), 13)


class TestRetryExponentialBackoff(unittest.TestCase):
    @patch("kipp.decorator._time_module.sleep")
    def test_backoff_doubles_delay(self, mock_sleep: MagicMock) -> None:
        @retry(RuntimeError, tries=4, delay=1, backoff=2)
        def always_fail() -> None:
            raise RuntimeError("boom")

        with self.assertRaises(RuntimeError):
            always_fail()

        delays = [call.args[0] for call in mock_sleep.call_args_list]
        self.assertEqual(delays, [1, 2, 4])

    @patch("kipp.decorator._time_module.sleep")
    def test_backoff_fractional_multiplier(self, mock_sleep: MagicMock) -> None:
        @retry(RuntimeError, tries=4, delay=10, backoff=0.5)
        def always_fail() -> None:
            raise RuntimeError()

        with self.assertRaises(RuntimeError):
            always_fail()

        delays = [call.args[0] for call in mock_sleep.call_args_list]
        self.assertAlmostEqual(delays[0], 10)
        self.assertAlmostEqual(delays[1], 5.0)
        self.assertAlmostEqual(delays[2], 2.5)

    @patch("kipp.decorator._time_module.sleep")
    def test_backoff_one_means_constant_delay(self, mock_sleep: MagicMock) -> None:
        @retry(RuntimeError, tries=4, delay=3, backoff=1)
        def always_fail() -> None:
            raise RuntimeError()

        with self.assertRaises(RuntimeError):
            always_fail()

        delays = [call.args[0] for call in mock_sleep.call_args_list]
        self.assertEqual(delays, [3, 3, 3])


class TestRetryFailurePath(unittest.TestCase):
    @patch("kipp.decorator._time_module.sleep")
    def test_exhausts_all_tries_then_raises(self, mock_sleep: MagicMock) -> None:
        call_count = 0

        @retry(ValueError, tries=3, delay=0.1, backoff=1)
        def always_fail() -> None:
            nonlocal call_count
            call_count += 1
            raise ValueError("fail")

        with self.assertRaises(ValueError):
            always_fail()
        self.assertEqual(call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)

    @patch("kipp.decorator._time_module.sleep")
    def test_unmatched_exception_propagates_immediately(self, mock_sleep: MagicMock) -> None:
        call_count = 0

        @retry(ValueError, tries=5, delay=1, backoff=1)
        def raise_type_error() -> None:
            nonlocal call_count
            call_count += 1
            raise TypeError("wrong type")

        with self.assertRaises(TypeError):
            raise_type_error()
        self.assertEqual(call_count, 1)
        mock_sleep.assert_not_called()

    @patch("kipp.decorator._time_module.sleep")
    def test_tries_one_no_retry(self, mock_sleep: MagicMock) -> None:
        @retry(ValueError, tries=1, delay=1, backoff=1)
        def fail() -> None:
            raise ValueError("fail")

        with self.assertRaises(ValueError):
            fail()
        mock_sleep.assert_not_called()


class TestRetryExceptionTuple(unittest.TestCase):
    @patch("kipp.decorator._time_module.sleep")
    def test_catches_multiple_exception_types(self, mock_sleep: MagicMock) -> None:
        call_count = 0

        @retry((ValueError, KeyError), tries=3, delay=0.1, backoff=1)
        def alternate_errors() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("v")
            if call_count == 2:
                raise KeyError("k")
            return "done"

        self.assertEqual(alternate_errors(), "done")
        self.assertEqual(call_count, 3)

    @patch("kipp.decorator._time_module.sleep")
    def test_tuple_does_not_catch_unlisted_exception(self, mock_sleep: MagicMock) -> None:
        call_count = 0

        @retry((ValueError, KeyError), tries=3, delay=0.1, backoff=1)
        def raise_runtime() -> None:
            nonlocal call_count
            call_count += 1
            raise RuntimeError("not in tuple")

        with self.assertRaises(RuntimeError):
            raise_runtime()
        self.assertEqual(call_count, 1)


class TestSingleInstance(unittest.TestCase):
    def test_creates_pid_file_with_current_pid(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pid") as f:
            pidfile = f.name
        os.unlink(pidfile)

        try:
            @single_instance(pidfile)
            def do_work() -> str:
                return "working"

            self.assertTrue(os.path.exists(pidfile))
            with open(pidfile) as f:
                pid = int(f.read().strip())
            self.assertEqual(pid, os.getpid())
            self.assertEqual(do_work(), "working")
        finally:
            if os.path.exists(pidfile):
                os.unlink(pidfile)

    def test_stale_pid_file_is_removed(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pid") as f:
            pidfile = f.name
        with open(pidfile, "w") as f:
            f.write("999999999")

        try:
            with patch("os.kill", side_effect=OSError("No such process")):
                @single_instance(pidfile)
                def do_work() -> str:
                    return "ok"

            self.assertTrue(os.path.exists(pidfile))
            self.assertEqual(do_work(), "ok")
        finally:
            if os.path.exists(pidfile):
                os.unlink(pidfile)

    def test_exits_if_another_instance_alive(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pid") as f:
            pidfile = f.name
        with open(pidfile, "w") as f:
            f.write(str(os.getpid()))

        try:
            with self.assertRaises(SystemExit):
                @single_instance(pidfile)
                def do_work() -> None:
                    pass
        finally:
            if os.path.exists(pidfile):
                os.unlink(pidfile)

    def test_no_existing_pid_file(self) -> None:
        pidfile = tempfile.mktemp(suffix=".pid")
        self.assertFalse(os.path.exists(pidfile))

        try:
            @single_instance(pidfile)
            def do_work() -> str:
                return "first"

            self.assertEqual(do_work(), "first")
        finally:
            if os.path.exists(pidfile):
                os.unlink(pidfile)

    def test_decorated_function_preserves_behavior(self) -> None:
        pidfile = tempfile.mktemp(suffix=".pid")

        try:
            @single_instance(pidfile)
            def add(a: int, b: int) -> int:
                return a + b

            self.assertEqual(add(3, 7), 10)
        finally:
            if os.path.exists(pidfile):
                os.unlink(pidfile)


class TestTimer(unittest.TestCase):
    @patch("kipp.decorator.get_logger")
    def test_returns_result(self, mock_get_logger: MagicMock) -> None:
        @timer
        def add(a: int, b: int) -> int:
            return a + b

        self.assertEqual(add(2, 3), 5)

    @patch("kipp.decorator.get_logger")
    def test_logs_function_name_and_cost(self, mock_get_logger: MagicMock) -> None:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        @timer
        def my_func() -> None:
            pass

        my_func()
        mock_logger.info.assert_called_once()
        log_args = mock_logger.info.call_args[0]
        self.assertEqual(log_args[0], "%s cost %.2fs")
        self.assertEqual(log_args[1], "my_func")

    @patch("kipp.decorator.get_logger")
    def test_exception_is_logged_and_reraised(self, mock_get_logger: MagicMock) -> None:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        @timer
        def failing() -> None:
            raise RuntimeError("oops")

        with self.assertRaises(RuntimeError):
            failing()
        mock_logger.exception.assert_called_once()
        # info is called in finally block even on exception
        mock_logger.info.assert_called_once()

    @patch("kipp.decorator.get_logger")
    def test_preserves_function_name_via_wraps(self, mock_get_logger: MagicMock) -> None:
        @timer
        def original_name() -> None:
            pass

        self.assertEqual(original_name.__name__, "original_name")

    @patch("kipp.decorator.get_logger")
    def test_passes_args_and_kwargs(self, mock_get_logger: MagicMock) -> None:
        @timer
        def multiply(a: int, b: int, factor: int = 1) -> int:
            return a * b * factor

        self.assertEqual(multiply(2, 3, factor=5), 30)


class TestDebugWrapperAlias(unittest.TestCase):
    def test_debug_wrapper_is_timer(self) -> None:
        self.assertIs(debug_wrapper, timer)


class TestMemo(unittest.TestCase):
    def test_caches_result_on_same_args(self) -> None:
        call_count = 0

        @memo
        def expensive(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        self.assertEqual(expensive(5), 10)
        self.assertEqual(expensive(5), 10)
        self.assertEqual(call_count, 1)

    def test_different_args_cached_separately(self) -> None:
        call_count = 0

        @memo
        def compute(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x + 1

        self.assertEqual(compute(1), 2)
        self.assertEqual(compute(2), 3)
        self.assertEqual(compute(1), 2)
        self.assertEqual(call_count, 2)

    def test_multiple_positional_args_form_key(self) -> None:
        call_count = 0

        @memo
        def add(a: int, b: int) -> int:
            nonlocal call_count
            call_count += 1
            return a + b

        self.assertEqual(add(1, 2), 3)
        self.assertEqual(add(1, 2), 3)
        # (2, 1) is a different tuple key than (1, 2)
        self.assertEqual(add(2, 1), 3)
        self.assertEqual(call_count, 2)

    def test_caches_none_result(self) -> None:
        call_count = 0

        @memo
        def return_none(x: int) -> None:
            nonlocal call_count
            call_count += 1
            return None

        self.assertIsNone(return_none(1))
        self.assertIsNone(return_none(1))
        self.assertEqual(call_count, 1)

    def test_caches_falsy_results(self) -> None:
        call_count = 0

        @memo
        def return_zero() -> int:
            nonlocal call_count
            call_count += 1
            return 0

        self.assertEqual(return_zero(), 0)
        self.assertEqual(return_zero(), 0)
        self.assertEqual(call_count, 1)

    def test_no_args_function(self) -> None:
        call_count = 0

        @memo
        def constant() -> int:
            nonlocal call_count
            call_count += 1
            return 42

        self.assertEqual(constant(), 42)
        self.assertEqual(constant(), 42)
        self.assertEqual(call_count, 1)

    def test_preserves_function_name(self) -> None:
        @memo
        def my_function() -> None:
            pass

        self.assertEqual(my_function.__name__, "my_function")


class TestTimeoutError(unittest.TestCase):
    def test_default_message(self) -> None:
        err = TimeoutError()
        self.assertEqual(err.value, "Timed Out")
        self.assertEqual(str(err), repr("Timed Out"))

    def test_custom_message(self) -> None:
        err = TimeoutError("custom msg")
        self.assertEqual(err.value, "custom msg")
        self.assertEqual(str(err), repr("custom msg"))

    def test_is_exception_subclass(self) -> None:
        self.assertTrue(issubclass(TimeoutError, Exception))


class TestTimeout(unittest.TestCase):
    def test_completes_within_timeout(self) -> None:
        @timeout(2)
        def fast() -> str:
            return "done"

        self.assertEqual(fast(), "done")

    def test_raises_timeout_error_on_slow_function(self) -> None:
        @timeout(1)
        def slow() -> None:
            time_module.sleep(5)

        with self.assertRaises(TimeoutError):
            slow()

    def test_preserves_function_name(self) -> None:
        @timeout(5)
        def my_decorated_func() -> None:
            pass

        self.assertEqual(my_decorated_func.__name__, "my_decorated_func")

    def test_restores_previous_signal_handler(self) -> None:
        original_handler = signal.getsignal(signal.SIGALRM)

        @timeout(5)
        def quick() -> str:
            return "ok"

        quick()
        restored = signal.getsignal(signal.SIGALRM)
        self.assertEqual(restored, original_handler)

    def test_restores_handler_on_exception(self) -> None:
        original_handler = signal.getsignal(signal.SIGALRM)

        @timeout(5)
        def raise_error() -> None:
            raise ValueError("inner error")

        with self.assertRaises(ValueError):
            raise_error()

        restored = signal.getsignal(signal.SIGALRM)
        self.assertEqual(restored, original_handler)

    def test_passes_args_and_kwargs(self) -> None:
        @timeout(5)
        def add(a: int, b: int, extra: int = 0) -> int:
            return a + b + extra

        self.assertEqual(add(1, 2, extra=10), 13)

    def test_alarm_is_cancelled_after_success(self) -> None:
        with patch("kipp.decorator.signal.alarm") as mock_alarm:
            with patch("kipp.decorator.signal.signal"):
                @timeout(10)
                def quick() -> str:
                    return "ok"

                quick()
            # signal.alarm(0) cancels the alarm
            mock_alarm.assert_any_call(0)


class TestCalculateArgsHash(unittest.TestCase):
    def test_deterministic(self) -> None:
        h1 = calculate_args_hash(1, 2, 3)
        h2 = calculate_args_hash(1, 2, 3)
        self.assertEqual(h1, h2)

    def test_different_args_different_hash(self) -> None:
        h1 = calculate_args_hash(1, 2)
        h2 = calculate_args_hash(3, 4)
        self.assertNotEqual(h1, h2)

    def test_kwargs_affect_hash(self) -> None:
        h1 = calculate_args_hash(1, key="a")
        h2 = calculate_args_hash(1, key="b")
        self.assertNotEqual(h1, h2)

    def test_returns_hex_string(self) -> None:
        h = calculate_args_hash("test")
        self.assertIsInstance(h, str)
        self.assertRegex(h, r"^[0-9a-f]+$")

    def test_empty_args(self) -> None:
        h = calculate_args_hash()
        self.assertIsInstance(h, str)
        self.assertTrue(len(h) > 0)

    def test_arg_order_matters(self) -> None:
        h1 = calculate_args_hash(1, 2)
        h2 = calculate_args_hash(2, 1)
        self.assertNotEqual(h1, h2)

    def test_mixed_types(self) -> None:
        h = calculate_args_hash(1, "two", 3.0, None, True)
        self.assertIsInstance(h, str)
        self.assertRegex(h, r"^[0-9a-f]+$")


class TestCacheItem(unittest.TestCase):
    def test_named_fields(self) -> None:
        item = CacheItem(data="hello", timeout_at=100.0)
        self.assertEqual(item.data, "hello")
        self.assertEqual(item.timeout_at, 100.0)

    def test_tuple_indexing(self) -> None:
        item = CacheItem(data=1, timeout_at=2.0)
        self.assertEqual(item[0], 1)
        self.assertEqual(item[1], 2.0)

    def test_is_iterable(self) -> None:
        item = CacheItem(data="x", timeout_at=5.0)
        data, timeout_at = item
        self.assertEqual(data, "x")
        self.assertEqual(timeout_at, 5.0)


class TestTimeoutCache(unittest.TestCase):
    def test_caches_result(self) -> None:
        call_count = 0

        @timeout_cache(expires_sec=60)
        def compute(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        self.assertEqual(compute(5), 10)
        self.assertEqual(compute(5), 10)
        self.assertEqual(call_count, 1)

    def test_different_args_cached_separately(self) -> None:
        call_count = 0

        @timeout_cache(expires_sec=60)
        def identity(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x

        self.assertEqual(identity(1), 1)
        self.assertEqual(identity(2), 2)
        self.assertEqual(identity(1), 1)
        self.assertEqual(call_count, 2)

    def test_expired_entry_is_recomputed(self) -> None:
        call_count = 0
        fake_time = [1000.0]

        def mock_time() -> float:
            return fake_time[0]

        with patch("kipp.decorator.time", side_effect=mock_time):
            @timeout_cache(expires_sec=10)
            def compute() -> int:
                nonlocal call_count
                call_count += 1
                return call_count

            self.assertEqual(compute(), 1)

            fake_time[0] = 1011.0
            self.assertEqual(compute(), 2)
            self.assertEqual(call_count, 2)

    def test_not_expired_entry_is_served_from_cache(self) -> None:
        call_count = 0
        fake_time = [1000.0]

        def mock_time() -> float:
            return fake_time[0]

        with patch("kipp.decorator.time", side_effect=mock_time):
            @timeout_cache(expires_sec=10)
            def compute() -> int:
                nonlocal call_count
                call_count += 1
                return call_count

            self.assertEqual(compute(), 1)

            fake_time[0] = 1005.0
            self.assertEqual(compute(), 1)
            self.assertEqual(call_count, 1)

    def test_eviction_removes_expired_entries_when_over_max_size(self) -> None:
        fake_time = [1000.0]

        def mock_time() -> float:
            return fake_time[0]

        with patch("kipp.decorator.time", side_effect=mock_time):
            call_count = 0

            @timeout_cache(expires_sec=5, max_size=2)
            def compute(x: int) -> int:
                nonlocal call_count
                call_count += 1
                return x

            compute(1)
            compute(2)
            self.assertEqual(call_count, 2)

            # Advance past expiration so entries are stale
            fake_time[0] = 1010.0

            # Entry for 3 is new and triggers eviction of expired 1 and 2
            compute(3)
            self.assertEqual(call_count, 3)

            # Entry 1 was evicted, so calling it again recomputes
            compute(1)
            self.assertEqual(call_count, 4)

    def test_eviction_keeps_fresh_entries(self) -> None:
        fake_time = [1000.0]

        def mock_time() -> float:
            return fake_time[0]

        with patch("kipp.decorator.time", side_effect=mock_time):
            call_count = 0

            @timeout_cache(expires_sec=20, max_size=2)
            def compute(x: int) -> int:
                nonlocal call_count
                call_count += 1
                return x

            compute(1)  # cached at t=1000, expires at t=1020
            compute(2)  # cached at t=1000, expires at t=1020

            fake_time[0] = 1005.0

            # 3 is expired (new), triggers eviction check, but 1 & 2 are fresh
            compute(3)
            self.assertEqual(call_count, 3)

    def test_kwargs_affect_cache_key(self) -> None:
        call_count = 0

        @timeout_cache(expires_sec=60)
        def compute(x: int = 0) -> int:
            nonlocal call_count
            call_count += 1
            return x

        compute(x=1)
        compute(x=2)
        compute(x=1)
        self.assertEqual(call_count, 2)

    def test_caches_none_return(self) -> None:
        call_count = 0

        @timeout_cache(expires_sec=60)
        def return_none() -> None:
            nonlocal call_count
            call_count += 1
            return None

        self.assertIsNone(return_none())
        self.assertIsNone(return_none())
        self.assertEqual(call_count, 1)

    def test_invalid_expires_sec_zero(self) -> None:
        with self.assertRaises(AssertionError):
            @timeout_cache(expires_sec=0)
            def f() -> None:
                pass

    def test_invalid_expires_sec_negative(self) -> None:
        with self.assertRaises(AssertionError):
            @timeout_cache(expires_sec=-1)
            def g() -> None:
                pass

    def test_invalid_max_size_zero(self) -> None:
        with self.assertRaises(AssertionError):
            @timeout_cache(max_size=0)
            def f() -> None:
                pass

    def test_invalid_max_size_negative(self) -> None:
        with self.assertRaises(AssertionError):
            @timeout_cache(max_size=-5)
            def f() -> None:
                pass

    def test_preserves_function_name(self) -> None:
        @timeout_cache(expires_sec=10)
        def my_cached_func() -> None:
            pass

        self.assertEqual(my_cached_func.__name__, "my_cached_func")

    def test_concurrent_access_does_not_crash(self) -> None:
        call_count = 0

        @timeout_cache(expires_sec=60)
        def slow_compute(x: int) -> int:
            nonlocal call_count
            call_count += 1
            time_module.sleep(0.01)
            return x * 2

        results: list[int] = []
        errors: list[Exception] = []

        def worker(val: int) -> None:
            try:
                results.append(slow_compute(val))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i % 3,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 10)
        for r in results:
            self.assertIn(r, [0, 2, 4])

    def test_cache_real_expiry_with_sleep(self) -> None:
        call_count = 0

        @timeout_cache(expires_sec=0.2)
        def get_val() -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        r1 = get_val()
        self.assertEqual(r1, 1)
        # Still cached
        self.assertEqual(get_val(), 1)

        time_module.sleep(0.3)
        r2 = get_val()
        self.assertEqual(r2, 2)

    def test_max_size_one(self) -> None:
        call_count = 0

        @timeout_cache(expires_sec=60, max_size=1)
        def compute(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x

        compute(1)
        compute(2)  # triggers eviction attempt (len=1 is not > 1, so no eviction)
        self.assertEqual(call_count, 2)


if __name__ == "__main__":
    unittest.main()
