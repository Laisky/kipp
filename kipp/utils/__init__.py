#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from threading import RLock
import time
import os
import tempfile
import re
import fcntl

from .logger import setup_logger, get_logger
from .date import UTC, CST, parse_dtstr, utcnow, cstnow
from .concurrents import Future, ThreadPoolExecutor, ProcessPoolExecutor
from .mailsender import EmailSender
from .dfa_filters import DFAFilter


email_sender = EmailSender()


class IOTA(object):
    """Simple Counter

    Examples:
    ::
        iota = IOTA()
        iota()           # return 0
        iota()           # return 1
        iota.count()     # return 2
        iota(2)          # return 4
        iota.latest()    # return 4
    """
    def __init__(self, init=-1, step=1):
        init = int(init)
        self.__count = init
        self.__step = step
        self.__lock = RLock()

    def count(self, step=None):
        with self.__lock:
            step = self.__step if step is None else int(step)
            self.__count += step
            return self.__count

    def latest(self):
        return self.__count

    def __call__(self, step=1):
        return self.count(step)

    def __str__(self):
        return str(self.__count)

    __repr__ = __str__


def sleep(secs):
    sleep_until = time.time() + secs
    remains = secs
    while remains:
        time.sleep(remains)
        remains = max(sleep_until - time.time(), 0)


VALID_FNAME_REGEX = re.compile('[a-zA-Z0-9]+')

def generate_validate_fname(val, dirpath=tempfile.gettempdir()):
    """Remove all invalidate characters in file path

    Args:
        val (str): file name
        dirpath (str, default=<system tempfile directory>):

    Returns:
        str: absolute file path
    """
    fname = '{}.lock'.format('_'.join(VALID_FNAME_REGEX.findall(val)))
    if dirpath:
        fname = os.path.join(dirpath, fname)

    return fname


def check_is_allow_to_running(lock_fname):
    """Check whether is another process is still running

    Args:
        lock_fname (str): the lock file path
            such as ``/mnt/log/ramjet-driver.lock``

    Returns:
        fp/False: is allow to running for current process
            fp: no other process is running, please keep the fp's reference
            False: another process is running, you should better quit current process

    Examples:
    ::
        import os

        from kipp.utils import check_is_allow_to_running

        is_allow_running = check_is_allow_to_running('/mnt/log/ramjet-driver.lock')
        if not is_allow_running:
            print('there is another process is still running, eixt...')
            os._exit(0)
    """
    fp = open(lock_fname, 'w')
    try:
        fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        return False
    else:
        return fp
