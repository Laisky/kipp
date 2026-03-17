#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import datetime
import logging
import os
import subprocess
import tempfile
import threading
import time
from unittest import TestCase
from unittest.mock import MagicMock, patch

import pytz

from kipp.utils import IOTA, generate_validate_fname, run_command, sleep
from kipp.utils.concurrents import (
    Future,
    KippPoolMixin,
    ProcessPoolExecutor,
    ThreadPoolExecutor,
)
from kipp.utils.date import (
    CST,
    UTC,
    _extrace_dtstr_exclude_tz,
    _parse_special_dtstr,
    cstnow,
    parse_dtstr,
    utcnow,
)
from kipp.utils.logger import (
    get_formatter,
    get_logger,
    get_stream_handler,
    get_wrap_handler,
    set_logger,
    setup_logger,
)


# ---------------------------------------------------------------------------
# IOTA
# ---------------------------------------------------------------------------


class IOTABasicTestCase(TestCase):
    def test_default_starts_at_zero(self):
        iota = IOTA()
        self.assertEqual(iota(), 0)

    def test_sequential_increment(self):
        iota = IOTA()
        self.assertEqual(iota(), 0)
        self.assertEqual(iota(), 1)
        self.assertEqual(iota(), 2)

    def test_custom_init(self):
        iota = IOTA(init=10)
        self.assertEqual(iota(), 11)

    def test_custom_step_via_count(self):
        iota = IOTA(init=-1, step=5)
        self.assertEqual(iota.count(), 4)
        self.assertEqual(iota.count(), 9)

    def test_call_always_uses_explicit_step(self):
        iota = IOTA(init=-1, step=5)
        # __call__ passes step=1 by default, overriding instance step
        self.assertEqual(iota(), 0)
        self.assertEqual(iota(), 1)

    def test_negative_step_via_count(self):
        iota = IOTA(init=10, step=-1)
        self.assertEqual(iota.count(), 9)
        self.assertEqual(iota.count(), 8)

    def test_call_with_negative_step(self):
        iota = IOTA()
        iota()  # 0
        self.assertEqual(iota(-1), -1)

    def test_step_zero_via_count(self):
        iota = IOTA(init=5, step=0)
        self.assertEqual(iota.count(), 5)
        self.assertEqual(iota.count(), 5)

    def test_explicit_step_override(self):
        iota = IOTA()
        self.assertEqual(iota(), 0)
        self.assertEqual(iota(2), 2)
        self.assertEqual(iota(0), 2)
        self.assertEqual(iota(-1), 1)

    def test_count_method(self):
        iota = IOTA()
        self.assertEqual(iota.count(), 0)
        self.assertEqual(iota.count(), 1)

    def test_count_with_step(self):
        iota = IOTA()
        self.assertEqual(iota.count(3), 2)
        self.assertEqual(iota.count(0), 2)

    def test_latest(self):
        iota = IOTA()
        iota()
        iota()
        self.assertEqual(iota.latest(), 1)

    def test_latest_before_any_call(self):
        iota = IOTA()
        self.assertEqual(iota.latest(), -1)

    def test_str_repr(self):
        iota = IOTA()
        iota()
        self.assertEqual(str(iota), "0")
        self.assertEqual(repr(iota), "0")

    def test_str_before_any_call(self):
        iota = IOTA(init=42)
        self.assertEqual(str(iota), "42")

    def test_invalid_step_string_raises(self):
        iota = IOTA()
        with self.assertRaises(ValueError):
            iota("str")

    def test_invalid_count_string_raises(self):
        iota = IOTA()
        with self.assertRaises(ValueError):
            iota.count("str")

    def test_init_coerced_to_int(self):
        iota = IOTA(init=2.9)
        self.assertEqual(iota.latest(), 2)

    def test_large_step(self):
        iota = IOTA(init=0, step=1000000)
        self.assertEqual(iota.count(), 1000000)
        self.assertEqual(iota.count(), 2000000)

    def test_thread_safety(self):
        iota = IOTA()
        num_threads = 10
        increments_per_thread = 100

        def increment():
            for _ in range(increments_per_thread):
                iota()

        threads = [threading.Thread(target=increment) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        expected = num_threads * increments_per_thread - 1
        self.assertEqual(iota.latest(), expected)


# ---------------------------------------------------------------------------
# sleep
# ---------------------------------------------------------------------------


class SleepTestCase(TestCase):
    def test_sleeps_at_least_requested_time(self):
        start = time.time()
        sleep(0.5)
        elapsed = time.time() - start
        self.assertGreaterEqual(elapsed, 0.5)

    def test_sleep_zero(self):
        start = time.time()
        sleep(0)
        elapsed = time.time() - start
        self.assertLess(elapsed, 1.0)

    def test_sleep_small_duration(self):
        start = time.time()
        sleep(0.1)
        elapsed = time.time() - start
        self.assertGreaterEqual(elapsed, 0.1)

    def test_sleep_returns_none(self):
        result = sleep(0)
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# generate_validate_fname
# ---------------------------------------------------------------------------


class GenerateValidateFnameTestCase(TestCase):
    def test_basic_string(self):
        result = generate_validate_fname("hello")
        self.assertTrue(result.endswith(".lock"))
        self.assertIn("hello", result)

    def test_strips_special_characters(self):
        result = generate_validate_fname("  (*d  02 s  ")
        fname = os.path.basename(result)
        self.assertEqual(fname, "d_02_s.lock")

    def test_spaces_become_underscores(self):
        result = generate_validate_fname("123 456")
        fname = os.path.basename(result)
        self.assertEqual(fname, "123_456.lock")

    def test_unicode_stripped(self):
        result = generate_validate_fname("俄1方123将为 a120$(#@*")
        fname = os.path.basename(result)
        self.assertEqual(fname, "1_123_a120.lock")

    def test_custom_dirpath(self):
        result = generate_validate_fname("test", dirpath="/custom/dir")
        self.assertTrue(result.startswith("/custom/dir"))
        self.assertTrue(result.endswith("test.lock"))

    def test_empty_dirpath(self):
        result = generate_validate_fname("test", dirpath="")
        self.assertEqual(result, "test.lock")

    def test_default_dirpath_is_tempdir(self):
        result = generate_validate_fname("test")
        self.assertTrue(result.startswith(tempfile.gettempdir()))

    def test_all_special_chars(self):
        result = generate_validate_fname("!@#$%^&*()")
        fname = os.path.basename(result)
        self.assertEqual(fname, ".lock")

    def test_dots_and_slashes_stripped(self):
        result = generate_validate_fname("../../etc/passwd")
        fname = os.path.basename(result)
        self.assertEqual(fname, "etc_passwd.lock")


# ---------------------------------------------------------------------------
# run_command
# ---------------------------------------------------------------------------


class RunCommandTestCase(TestCase):
    def test_successful_command(self):
        with patch("kipp.utils.subprocess.Popen") as MockPopen:
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = ("output", "")
            mock_proc.returncode = 0
            MockPopen.return_value = mock_proc

            result = run_command("echo hello", timeout=10)
            self.assertEqual(result, "output")

    def test_nonzero_exit_raises(self):
        with patch("kipp.utils.subprocess.Popen") as MockPopen:
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = ("", "error msg")
            mock_proc.returncode = 1
            MockPopen.return_value = mock_proc

            with self.assertRaises(AssertionError):
                run_command("false", timeout=10)

    def test_timeout_kills_process(self):
        with patch("kipp.utils.subprocess.Popen") as MockPopen:
            mock_proc = MagicMock()
            mock_proc.communicate.side_effect = [
                subprocess.TimeoutExpired("cmd", 5),
                ("partial output", ""),
            ]
            mock_proc.returncode = 0
            MockPopen.return_value = mock_proc

            result = run_command("slow_cmd", timeout=5)
            mock_proc.kill.assert_called_once()
            self.assertEqual(result, "partial output")

    def test_command_passed_to_popen(self):
        with patch("kipp.utils.subprocess.Popen") as MockPopen:
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = ("", "")
            mock_proc.returncode = 0
            MockPopen.return_value = mock_proc

            run_command("ls -la", timeout=30)
            MockPopen.assert_called_once_with(
                ["ls", "-la"],
                shell=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

    def test_shell_metacharacters_are_not_executed_by_a_shell(self):
        with patch("kipp.utils.subprocess.Popen") as MockPopen:
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = ("", "")
            mock_proc.returncode = 0
            MockPopen.return_value = mock_proc

            run_command("echo 'hello; rm -rf /'", timeout=30)
            self.assertEqual(MockPopen.call_args[0][0], ["echo", "hello; rm -rf /"])
            self.assertFalse(MockPopen.call_args[1]["shell"])

    def test_timeout_then_nonzero_raises(self):
        with patch("kipp.utils.subprocess.Popen") as MockPopen:
            mock_proc = MagicMock()
            mock_proc.communicate.side_effect = [
                subprocess.TimeoutExpired("cmd", 5),
                ("", "killed"),
            ]
            mock_proc.returncode = -9
            MockPopen.return_value = mock_proc

            with self.assertRaises(AssertionError):
                run_command("slow_cmd", timeout=5)


# ---------------------------------------------------------------------------
# check_is_allow_to_running
# ---------------------------------------------------------------------------


class CheckIsAllowToRunningTestCase(TestCase):
    def test_lock_acquired(self):
        from kipp.utils import check_is_allow_to_running

        mock_fp = MagicMock()
        with patch("builtins.open", return_value=mock_fp), patch(
            "kipp.utils.fcntl"
        ) as mock_fcntl:
            mock_fcntl.LOCK_EX = 2
            mock_fcntl.LOCK_NB = 4
            result = check_is_allow_to_running("/tmp/test.lock")

        self.assertIs(result, mock_fp)
        mock_fcntl.lockf.assert_called_once()

    def test_lock_denied(self):
        from kipp.utils import check_is_allow_to_running

        mock_fp = MagicMock()
        with patch("builtins.open", return_value=mock_fp), patch(
            "kipp.utils.fcntl"
        ) as mock_fcntl:
            mock_fcntl.LOCK_EX = 2
            mock_fcntl.LOCK_NB = 4
            mock_fcntl.lockf.side_effect = IOError("Resource unavailable")
            result = check_is_allow_to_running("/tmp/test.lock")

        self.assertFalse(result)

    def test_no_fcntl_raises(self):
        from kipp.utils import check_is_allow_to_running

        with patch("kipp.utils.fcntl", None):
            with self.assertRaises(NotImplementedError):
                check_is_allow_to_running("/tmp/test.lock")


# ---------------------------------------------------------------------------
# date.py - UTC / CST constants
# ---------------------------------------------------------------------------


class TimezoneConstantsTestCase(TestCase):
    def test_utc_is_utc(self):
        self.assertEqual(str(UTC), "UTC")

    def test_cst_is_shanghai(self):
        self.assertEqual(str(CST), "Asia/Shanghai")

    def test_utc_offset_is_zero(self):
        dt = datetime.datetime(2020, 1, 1, tzinfo=pytz.utc)
        offset = UTC.utcoffset(dt)
        self.assertEqual(offset, datetime.timedelta(0))

    def test_cst_offset_is_8_hours(self):
        dt = datetime.datetime(2020, 6, 1)
        offset = CST.localize(dt).utcoffset()
        self.assertEqual(offset, datetime.timedelta(hours=8))


# ---------------------------------------------------------------------------
# date.py - utcnow / cstnow
# ---------------------------------------------------------------------------


class UtcnowTestCase(TestCase):
    def test_returns_datetime(self):
        result = utcnow()
        self.assertIsInstance(result, datetime.datetime)

    def test_has_tzinfo(self):
        result = utcnow()
        self.assertIsNotNone(result.tzinfo)

    def test_tzinfo_is_utc(self):
        result = utcnow()
        self.assertEqual(str(result.tzinfo), "UTC")

    def test_naive_mode_strips_tzinfo(self):
        result = utcnow(is_naive=True)
        self.assertIsNone(result.tzinfo)

    def test_close_to_real_time(self):
        before = datetime.datetime.now(tz=datetime.timezone.utc)
        result = utcnow()
        after = datetime.datetime.now(tz=datetime.timezone.utc)
        # Compare in UTC; result has pytz UTC, before/after have stdlib UTC
        self.assertGreaterEqual(result.timestamp(), before.timestamp())
        self.assertLessEqual(result.timestamp(), after.timestamp())


class CstnowTestCase(TestCase):
    def test_returns_datetime(self):
        # The critical bug fix: cstnow must return datetime, not True
        result = cstnow()
        self.assertIsInstance(result, datetime.datetime)

    def test_not_boolean(self):
        result = cstnow()
        self.assertNotEqual(result, True)
        self.assertIsNot(result, True)

    def test_has_tzinfo(self):
        result = cstnow()
        self.assertIsNotNone(result.tzinfo)

    def test_timezone_is_cst(self):
        result = cstnow()
        offset = result.utcoffset()
        self.assertEqual(offset, datetime.timedelta(hours=8))

    def test_naive_mode_strips_tzinfo(self):
        result = cstnow(is_naive=True)
        self.assertIsNone(result.tzinfo)

    def test_cst_is_8_hours_ahead_of_utc(self):
        utc_dt = utcnow()
        cst_dt = cstnow()
        # Same instant in time; timestamps should be very close
        self.assertAlmostEqual(utc_dt.timestamp(), cst_dt.timestamp(), places=0)
        # But the hour should differ by 8 (modulo 24)
        expected_hour = (utc_dt.hour + 8) % 24
        self.assertEqual(cst_dt.hour, expected_hour)


# ---------------------------------------------------------------------------
# date.py - _parse_special_dtstr
# ---------------------------------------------------------------------------


class ParseSpecialDtstrTestCase(TestCase):
    def test_four_digit_time(self):
        # "1300" -> 13:00 UTC
        result = _parse_special_dtstr("1300")
        self.assertIsNotNone(result)
        self.assertEqual(result.hour, 13)
        self.assertEqual(result.minute, 0)
        self.assertIsNotNone(result.tzinfo)

    def test_hhmm_noon_suffix(self):
        result = _parse_special_dtstr("13:00 noon")
        self.assertIsNotNone(result)
        self.assertEqual(result.hour, 13)
        self.assertEqual(result.minute, 0)

    def test_noon_case_insensitive(self):
        result = _parse_special_dtstr("09:30 NOON")
        self.assertIsNotNone(result)
        self.assertEqual(result.hour, 9)
        self.assertEqual(result.minute, 30)

    def test_unrecognized_returns_none(self):
        result = _parse_special_dtstr("2020-01-01T12:00:00")
        self.assertIsNone(result)

    def test_empty_string_returns_none(self):
        result = _parse_special_dtstr("")
        self.assertIsNone(result)

    def test_midnight_four_digit(self):
        result = _parse_special_dtstr("0000")
        self.assertIsNotNone(result)
        self.assertEqual(result.hour, 0)
        self.assertEqual(result.minute, 0)


# ---------------------------------------------------------------------------
# date.py - _extrace_dtstr_exclude_tz
# ---------------------------------------------------------------------------


class ExtraceDtstrExcludeTzTestCase(TestCase):
    def test_strips_positive_offset(self):
        result = _extrace_dtstr_exclude_tz("2020-01-01T12:00:00+08:00")
        self.assertEqual(result, "2020-01-01T12:00:00")

    def test_strips_negative_offset(self):
        result = _extrace_dtstr_exclude_tz("2020-01-01T12:00:00-05:00")
        self.assertEqual(result, "2020-01-01T12:00:00")

    def test_strips_short_offset(self):
        result = _extrace_dtstr_exclude_tz("2020-01-01T12:00:00+08")
        self.assertEqual(result, "2020-01-01T12:00:00")

    def test_no_offset_unchanged(self):
        dtstr = "2020-01-01T12:00:00"
        result = _extrace_dtstr_exclude_tz(dtstr)
        self.assertEqual(result, dtstr)

    def test_z_suffix_unchanged(self):
        # Z is not matched by the regex (not +/- digits)
        dtstr = "2020-01-01T12:00:00Z"
        result = _extrace_dtstr_exclude_tz(dtstr)
        self.assertEqual(result, dtstr)


# ---------------------------------------------------------------------------
# date.py - parse_dtstr
# ---------------------------------------------------------------------------


class ParseDtstrTestCase(TestCase):
    def test_iso_format(self):
        dt = parse_dtstr("2020-01-15T10:30:00Z")
        self.assertEqual(dt.year, 2020)
        self.assertEqual(dt.month, 1)
        self.assertEqual(dt.day, 15)
        self.assertEqual(dt.hour, 10)
        self.assertEqual(dt.minute, 30)

    def test_returns_aware_by_default(self):
        dt = parse_dtstr("2020-01-15T10:30:00Z")
        self.assertIsNotNone(dt.tzinfo)

    def test_naive_strips_tzinfo(self):
        dt = parse_dtstr("2020-01-15T10:30:00Z", naive=True)
        self.assertIsNone(dt.tzinfo)

    def test_replace_tz(self):
        dt = parse_dtstr("2020-01-15T10:30:00Z", replace_tz=CST)
        # Hour unchanged, but tzinfo is now CST
        self.assertEqual(dt.hour, 10)
        self.assertIs(dt.tzinfo, CST)
        # ``replace`` attaches the zone object directly instead of localizing,
        # so pytz exposes the historical LMT offset here rather than modern CST.
        self.assertEqual(dt.utcoffset(), datetime.timedelta(hours=8, minutes=6))

    def test_convert_tz(self):
        dt = parse_dtstr("2020-01-15T10:30:00Z", convert_tz=CST)
        # Hour shifted by +8
        self.assertEqual(dt.hour, 18)
        self.assertEqual(dt.minute, 30)

    def test_ignore_tz(self):
        dt = parse_dtstr("2020-01-15T10:30:00+05:00", ignore_tz=True)
        # Timezone offset stripped before parsing; maya treats as UTC
        self.assertEqual(dt.hour, 10)

    def test_special_four_digit_time(self):
        dt = parse_dtstr("1300")
        self.assertEqual(dt.hour, 13)
        self.assertEqual(dt.minute, 0)

    def test_special_noon_format(self):
        dt = parse_dtstr("14:30 noon")
        self.assertEqual(dt.hour, 14)
        self.assertEqual(dt.minute, 30)

    def test_slash_date_format(self):
        dt = parse_dtstr("2017/1/1 13:00")
        self.assertEqual(dt.year, 2017)
        self.assertEqual(dt.month, 1)
        self.assertEqual(dt.day, 1)

    def test_naive_takes_precedence_over_replace_tz(self):
        # naive branch is checked first
        dt = parse_dtstr("2020-01-15T10:30:00Z", naive=True, replace_tz=CST)
        self.assertIsNone(dt.tzinfo)

    def test_convert_tz_not_applied_when_naive(self):
        dt = parse_dtstr("2020-01-15T10:30:00Z", naive=True, convert_tz=CST)
        self.assertIsNone(dt.tzinfo)


# ---------------------------------------------------------------------------
# logger.py - get_formatter
# ---------------------------------------------------------------------------


class GetFormatterTestCase(TestCase):
    def test_returns_formatter(self):
        fmt = get_formatter()
        self.assertIsInstance(fmt, logging.Formatter)

    def test_uses_gmt(self):
        fmt = get_formatter()
        self.assertIs(fmt.converter, time.gmtime)


# ---------------------------------------------------------------------------
# logger.py - get_stream_handler
# ---------------------------------------------------------------------------


class GetStreamHandlerTestCase(TestCase):
    def test_returns_stream_handler(self):
        handler = get_stream_handler()
        self.assertIsInstance(handler, logging.StreamHandler)

    def test_level_is_debug(self):
        handler = get_stream_handler()
        self.assertEqual(handler.level, logging.DEBUG)

    def test_has_formatter(self):
        handler = get_stream_handler()
        self.assertIsNotNone(handler.formatter)


# ---------------------------------------------------------------------------
# logger.py - setup_logger / get_logger / set_logger
# ---------------------------------------------------------------------------


class SetupLoggerTestCase(TestCase):
    def test_returns_logger(self):
        logger = setup_logger("test_setup")
        self.assertIsInstance(logger, logging.Logger)

    def test_default_level_is_info(self):
        logger = setup_logger("test_info_level")
        self.assertEqual(logger.level, logging.INFO)

    def test_debug_flag(self):
        logger = setup_logger("test_debug_level", debug=True)
        self.assertEqual(logger.level, logging.DEBUG)

    def test_propagate_false(self):
        logger = setup_logger("test_propagate")
        self.assertFalse(logger.propagate)

    def test_has_handler(self):
        logger = setup_logger("test_has_handler")
        self.assertGreater(len(logger.handlers), 0)

    def test_idempotent_handlers(self):
        # Calling setup_logger twice should not double-add handlers
        name = "test_idempotent_unique"
        logger1 = setup_logger(name)
        count1 = len(logger1.handlers)
        logger2 = setup_logger(name)
        count2 = len(logger2.handlers)
        self.assertEqual(count1, count2)

    def test_tornado_logger_set_to_error(self):
        setup_logger("test_tornado_check")
        tornado_logger = logging.getLogger("tornado")
        self.assertEqual(tornado_logger.level, logging.ERROR)

    def test_concurrent_logger_set_to_error(self):
        setup_logger("test_concurrent_check")
        concurrent_logger = logging.getLogger("concurrent")
        self.assertEqual(concurrent_logger.level, logging.ERROR)


class GetLoggerTestCase(TestCase):
    def test_returns_logger_instance(self):
        logger = get_logger()
        self.assertIsInstance(logger, logging.Logger)

    def test_singleton(self):
        self.assertIs(get_logger(), get_logger())

    def test_logger_name_is_kipp(self):
        logger = get_logger()
        self.assertEqual(logger.name, "kipp")


class SetLoggerTestCase(TestCase):
    def test_adds_wrap_handler(self):
        external_logger = logging.getLogger("test_external_wrap")
        kipp_logger = get_logger()
        handler_count_before = len(kipp_logger.handlers)
        set_logger(external_logger)
        handler_count_after = len(kipp_logger.handlers)
        self.assertEqual(handler_count_after, handler_count_before + 1)


# ---------------------------------------------------------------------------
# logger.py - get_wrap_handler
# ---------------------------------------------------------------------------


class GetWrapHandlerTestCase(TestCase):
    def test_returns_handler(self):
        target = logging.getLogger("test_wrap_target")
        handler = get_wrap_handler(target)
        self.assertIsInstance(handler, logging.StreamHandler)

    def test_forwards_log_records(self):
        target = MagicMock(spec=logging.Logger)
        handler = get_wrap_handler(target)
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=1,
            msg="hello",
            args=None,
            exc_info=None,
        )
        handler.emit(record)
        target.log.assert_called_once()
        args = target.log.call_args
        self.assertEqual(args[0][0], logging.WARNING)
        self.assertIn("hello", args[0][1])


# ---------------------------------------------------------------------------
# concurrents.py - ThreadPoolExecutor
# ---------------------------------------------------------------------------


class ThreadPoolExecutorTestCase(TestCase):
    def test_submit_returns_future(self):
        with ThreadPoolExecutor(max_workers=2) as executor:
            future = executor.submit(lambda: 42)
            self.assertIsInstance(future, Future)
            self.assertEqual(future.result(timeout=5), 42)

    def test_submit_with_args(self):
        def add(a, b):
            return a + b

        with ThreadPoolExecutor(max_workers=2) as executor:
            future = executor.submit(add, 3, 7)
            self.assertEqual(future.result(timeout=5), 10)

    def test_coroutine_decorator(self):
        executor = ThreadPoolExecutor(max_workers=2)
        try:

            @executor.coroutine
            def blocking_work(x):
                return x * 2

            future = blocking_work(5)
            self.assertIsInstance(future, Future)
            self.assertEqual(future.result(timeout=5), 10)
        finally:
            executor.shutdown(wait=True)

    def test_coroutine_preserves_name(self):
        executor = ThreadPoolExecutor(max_workers=1)
        try:

            @executor.coroutine
            def my_func():
                pass

            self.assertEqual(my_func.__name__, "my_func")
        finally:
            executor.shutdown(wait=True)

    def test_coroutine_with_kwargs(self):
        executor = ThreadPoolExecutor(max_workers=1)
        try:

            @executor.coroutine
            def greet(name, greeting="hello"):
                return f"{greeting} {name}"

            future = greet("world", greeting="hi")
            self.assertEqual(future.result(timeout=5), "hi world")
        finally:
            executor.shutdown(wait=True)

    def test_coroutine_exception_propagates(self):
        executor = ThreadPoolExecutor(max_workers=1)
        try:

            @executor.coroutine
            def fail():
                raise ValueError("boom")

            future = fail()
            with self.assertRaises(ValueError):
                future.result(timeout=5)
        finally:
            executor.shutdown(wait=True)

    def test_multiple_concurrent_tasks(self):
        results = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(lambda i=i: i * i, i) for i in range(10)]
            for f in futures:
                results.append(f.result(timeout=5))
        self.assertEqual(sorted(results), [i * i for i in range(10)])


# ---------------------------------------------------------------------------
# concurrents.py - ProcessPoolExecutor
# ---------------------------------------------------------------------------


class ProcessPoolExecutorTestCase(TestCase):
    def test_is_subclass_of_mixin(self):
        self.assertTrue(issubclass(ProcessPoolExecutor, KippPoolMixin))

    def test_has_coroutine_method(self):
        self.assertTrue(hasattr(ProcessPoolExecutor, "coroutine"))


# ---------------------------------------------------------------------------
# concurrents.py - KippPoolMixin
# ---------------------------------------------------------------------------


class KippPoolMixinTestCase(TestCase):
    def test_mixin_provides_coroutine(self):
        self.assertTrue(hasattr(KippPoolMixin, "coroutine"))

    def test_thread_executor_inherits_mixin(self):
        self.assertTrue(issubclass(ThreadPoolExecutor, KippPoolMixin))

    def test_process_executor_inherits_mixin(self):
        self.assertTrue(issubclass(ProcessPoolExecutor, KippPoolMixin))
