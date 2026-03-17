#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import io
import shlex
from threading import RLock
import time
import os
import tempfile
from functools import wraps
from collections.abc import Callable
from typing import Any
import re
import subprocess

try:
    import fcntl
except ImportError:
    # fcntl is Unix-only; on Windows this remains None and
    # check_is_allow_to_running will raise NotImplementedError
    fcntl = None  # type: ignore[assignment]

from .logger import setup_logger, get_logger
from .date import UTC, CST, parse_dtstr, utcnow, cstnow
from .concurrents import Future, ThreadPoolExecutor, ProcessPoolExecutor
from .mailsender import EmailSender
from .dfa_filters import DFAFilter


logger = get_logger()
email_sender = EmailSender()


def run_command(command: str, timeout: int) -> str:
    """Run a command and return its stdout.

    On timeout the child process is killed and its partial output is still
    captured via a second communicate() call. Raises AssertionError if the
    command exits with a non-zero return code.

    Args:
        command: command to run
        timeout: seconds before the process is killed
    """
    logger.debug("run command, {}".format(command))
    # Avoid invoking a shell for caller-provided commands; execute argv directly
    # so shell metacharacters are treated as data instead of syntax.
    p = subprocess.Popen(
        shlex.split(command),
        shell=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        outs, errs = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        outs, errs = p.communicate()

    assert p.returncode == 0, errs
    return outs


def timer(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator that logs the start and end of a function call."""

    @wraps(func)
    def wrapper(*args: Any, **kw: Any) -> Any:
        logger.info("{} running...".format(func.__name__))
        try:
            return func(*args, **kw)
        finally:
            logger.info("{} end".format(func.__name__))

    return wrapper


class IOTA:
    """Thread-safe auto-incrementing counter.

    Defaults to starting at -1 so the first call returns 0, matching
    Go's iota semantics where the first constant is zero-valued.

    Examples:
    ::
        iota = IOTA()
        iota()           # return 0
        iota()           # return 1
        iota.count()     # return 2
        iota(2)          # return 4
        iota.latest()    # return 4
    """

    def __init__(self, init: int = -1, step: int = 1) -> None:
        init = int(init)
        self.__count: int = init
        self.__step: int = step
        self.__lock: RLock = RLock()

    def count(self, step: int | None = None) -> int:
        with self.__lock:
            step = self.__step if step is None else int(step)
            self.__count += step
            return self.__count

    def latest(self) -> int:
        return self.__count

    def __call__(self, step: int = 1) -> int:
        return self.count(step)

    def __str__(self) -> str:
        return str(self.__count)

    __repr__ = __str__


def sleep(secs: float) -> None:
    """Sleep for the given duration, resilient to spurious early wakeups.

    Unlike time.sleep(), this retries in a loop to guarantee the full
    duration elapses even if the OS wakes the thread prematurely.
    """
    sleep_until = time.time() + secs
    remains = secs
    while remains:
        time.sleep(remains)
        remains = max(sleep_until - time.time(), 0)


VALID_FNAME_REGEX: re.Pattern[str] = re.compile("[a-zA-Z0-9]+")


def generate_validate_fname(
    val: str, dirpath: str = tempfile.gettempdir()
) -> str:
    """Sanitize a string into a valid lock file path.

    Strips all non-alphanumeric characters, joins remaining segments
    with underscores, and appends a .lock extension.

    Args:
        val: file name (potentially containing unsafe characters)
        dirpath: directory for the generated path

    Returns:
        Absolute file path suitable for use as a lock file
    """
    fname = "{}.lock".format("_".join(VALID_FNAME_REGEX.findall(val)))
    if dirpath:
        fname = os.path.join(dirpath, fname)

    return fname


def check_is_allow_to_running(lock_fname: str) -> io.TextIOWrapper | bool:
    """Acquire an exclusive file lock to enforce single-instance execution.

    Uses POSIX advisory locking (fcntl). The caller MUST keep a reference
    to the returned file object for the lock's lifetime -- if it gets
    garbage-collected, the lock is released.

    Args:
        lock_fname: the lock file path,
            such as ``/mnt/log/ramjet-driver.lock``

    Returns:
        The open file object if the lock was acquired (keep this reference!),
        or False if another process already holds the lock.

    Examples:
    ::
        import os

        from kipp.utils import check_is_allow_to_running

        is_allow_running = check_is_allow_to_running('/mnt/log/ramjet-driver.lock')
        if not is_allow_running:
            print('there is another process is still running, eixt...')
            os._exit(0)
    """
    if not fcntl:
        raise NotImplementedError("not support fcntl in your system")

    fp = open(lock_fname, "w")
    try:
        fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        return False
    else:
        return fp
