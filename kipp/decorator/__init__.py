#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations, unicode_literals

import functools
import os
import signal
import sys
from collections import namedtuple
from typing import Any, Callable, TypeVar

import time as _time_module

try:
    from time import monotonic as time
except ImportError:
    from time import time

import xxhash

from kipp.utils import get_logger

F = TypeVar("F", bound=Callable[..., Any])


def retry(
    ExceptionToCheck: type[Exception] | tuple[type[Exception], ...],
    tries: int = 3,
    delay: int | float = 1,
    backoff: int | float = 1,
) -> Callable[[F], F]:
    """Retry calling the decorated function using an exponential backoff.

    The last attempt (when tries is exhausted) is made without a try/except,
    so the exception propagates to the caller on final failure.

    http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
    original from: http://wiki.python.org/moin/PythonDecoratorLibrary#Retry

    Args:
        ExceptionToCheck: Exception class or tuple of exception classes that
            trigger a retry. All other exceptions propagate immediately.
        tries: Total number of attempts (not retries), so tries=3 means
            up to 2 retries after the initial call.
        delay: Initial delay between retries in seconds.
        backoff: Multiplier applied to delay after each retry,
            e.g. backoff=2 doubles the wait each time.
    """

    def deco_retry(f: F) -> F:
        @functools.wraps(f)
        def _wrapper(*args: Any, **kwargs: Any) -> Any:
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except ExceptionToCheck:
                    _time_module.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff

            return f(*args, **kwargs)

        return _wrapper  # type: ignore[return-value]

    return deco_retry


def single_instance(
    pidfilename: str, logger: Any = None
) -> Callable[[F], F]:
    """Ensure only one OS process runs the decorated function at a time.

    Uses a PID file for coordination. On startup, if a PID file exists and
    the recorded process is still alive, the current process exits immediately.
    This is useful for cron-scheduled tasks that might overlap.

    Note: The PID check happens at decoration time (import time), not at
    call time, so the guard runs once when the module loads.

    Args:
        pidfilename: Filesystem path for the lock file that stores the PID.
        logger: Unused legacy parameter kept for backward compatibility.
    """

    def create_pid(pidfilename: str) -> None:
        current_pid = os.getpid()
        pidfile = open(pidfilename, "w", encoding="utf-8")
        pidfile.write(str(current_pid))
        pidfile.close()

    def read_pid(file_path: str) -> str:
        """Read pid from a pid file"""
        f = open(file_path, encoding="utf-8")
        pidv = f.read()
        return pidv.strip()

    def check_pid(pid: int) -> bool:
        """Probe whether a process is alive by sending signal 0.

        Signal 0 doesn't actually deliver a signal; the kernel just checks
        permissions, which fails with OSError if the process doesn't exist.
        """
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        else:
            return True

    def deco_single_instance(func: F) -> F:
        """Make sure only one instance of this program with the same parameters runs"""
        if os.path.exists(pidfilename):
            pidv = read_pid(pidfilename)
            if check_pid(int(pidv)):
                (logger or get_logger()).info(
                    "There's already an instance of this program, pid : %s", pidv
                )
                sys.exit()
            else:
                os.remove(pidfilename)
        create_pid(pidfilename)

        @functools.wraps(func)
        def _wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        return _wrapper  # type: ignore[return-value]

    return deco_single_instance


def timer(fn: F) -> F:
    """Log wall-clock execution time of the decorated function.

    Timing is always logged (even if the function raises), because the
    log call is in the ``finally`` block. On exception the traceback is
    also logged before re-raising.

    Examples::

        from kipp.decorator import timer

        @timer
        def demo():
            time.sleep(10)

    """
    @functools.wraps(fn)
    def wrapper(*args: Any, **kw: Any) -> Any:
        try:
            start_at = time()
            r = fn(*args, **kw)
        except Exception:
            get_logger().exception("run %s", fn.__name__)
            raise
        else:
            return r
        finally:
            get_logger().info("%s cost %.2fs", fn.__name__, time() - start_at)

    return wrapper  # type: ignore[return-value]


# Legacy alias preserved for backward compatibility with older imports.
debug_wrapper = timer  # compatable


def memo(fn: F) -> F:
    """Unbounded memoization cache keyed on positional arguments.

    Only positional args are used as cache keys, so the decorated function
    must not rely on keyword arguments for varying behavior. The cache lives
    for the lifetime of the process and is never evicted -- suitable only
    for functions with a small, bounded set of possible inputs.
    """
    cache: dict[tuple[Any, ...], Any] = {}
    miss = object()

    @functools.wraps(fn)
    def wrapper(*args: Any) -> Any:
        result = cache.get(args, miss)
        if result is miss:
            result = fn(*args)
            cache[args] = result
        return result

    return wrapper  # type: ignore[return-value]


class TimeoutError(Exception):
    """Raised when a function decorated with ``timeout`` exceeds its time limit."""

    def __init__(self, value: str = "Timed Out") -> None:
        self.value = value

    def __str__(self) -> str:
        return repr(self.value)


def timeout(seconds_before_timeout: int) -> Callable[[F], F]:
    """Abort a function if it runs longer than the given number of seconds.

    Uses POSIX SIGALRM, so this only works on Unix-like systems and only
    in the main thread (signals can only be set in the main thread).

    Args:
        seconds_before_timeout: Wall-clock seconds before raising TimeoutError.
    """

    def decorate(f: F) -> F:
        def handler(signum: int, frame: Any) -> None:
            raise TimeoutError()

        def new_f(*args: Any, **kwargs: Any) -> Any:
            old = signal.signal(signal.SIGALRM, handler)
            signal.alarm(seconds_before_timeout)
            try:
                result = f(*args, **kwargs)
            finally:
                signal.signal(signal.SIGALRM, old)
            signal.alarm(0)
            return result

        new_f.__name__ = f.__name__
        return new_f  # type: ignore[return-value]

    return decorate


def calculate_args_hash(*args: Any, **kw: Any) -> str:
    """Produce a short deterministic hash of arbitrary positional/keyword args.

    Uses xxHash (xxh32) for speed over cryptographic strength -- this is
    only intended for cache-key derivation, not security.
    """
    return xxhash.xxh32(str(args) + str(kw)).hexdigest()


CacheItem = namedtuple("CacheItem", ["data", "timeout_at"])


def timeout_cache(
    expires_sec: int | float = 30, max_size: int = 128
) -> Callable[[F], F]:
    """Decorator that caches return values with a time-based expiration.

    Each unique combination of arguments (hashed via xxHash) gets its own
    cache slot. When the cache exceeds ``max_size``, an eviction pass runs
    before inserting the new entry.

    Args:
        expires_sec: Number of seconds before a cached value is considered
            stale and recomputed on next call.
        max_size: Maximum number of entries before triggering eviction.

    Examples::

        import time
        from kipp.utils import timeout_cache

        @timeout_cache(expires_sec=2)
        def demo():
            return time.time()

        r = demo()
        time.sleep(1)
        r == demo()

    """
    assert expires_sec > 0, "expires_sec should greater than 0, but got {}".format(
        expires_sec
    )
    assert max_size > 0, "max_size should greater than 0, but got {}".format(max_size)
    state: dict[str, CacheItem] = {}

    def decorator(f: F) -> F:
        @functools.wraps(f)
        def wrapper(*args: Any, **kw: Any) -> Any:
            hkey = calculate_args_hash(*args, **kw)
            if hkey not in state or state[hkey].timeout_at < time():
                if len(state) > max_size:
                    for k in list(state.keys()):
                        if state[k].timeout_at < time():
                            del state[k]

                state[hkey] = CacheItem(
                    timeout_at=time() + expires_sec, data=f(*args, **kw)
                )

            return state[hkey].data

        return wrapper  # type: ignore[return-value]

    return decorator
