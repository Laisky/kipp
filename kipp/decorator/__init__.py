#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import functools
import traceback
import time
import os
import sys
import datetime
import signal

from kipp.utils import get_logger


def retry(ExceptionToCheck, tries=3, delay=1, backoff=1):
    """Retry calling the decorated function using an exponential backoff.

    http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
    original from: http://wiki.python.org/moin/PythonDecoratorLibrary#Retry

    :param ExceptionToCheck: the exception to check. may be a tuple of
        exceptions to check
    :type ExceptionToCheck: Exception or tuple
    :param tries: number of times to try (not retry) before giving up
    :type tries: int
    :param delay: initial delay between retries in seconds
    :type delay: int
    :param backoff: backoff multiplier e.g. value of 2 will double the delay
        each retry
    :type backoff: int
    :param logger: logger to use. If None, print
    :type logger: logging.Logger instance
    """
    def deco_retry(f):
        @functools.wraps(f)
        def _wrapper(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except ExceptionToCheck:
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff

            return f(*args, **kwargs)

        return _wrapper  # true decorator

    return deco_retry


def single_instance(pidfilename, logger=None):
    def create_pid(pidfilename):
        current_pid = os.getpid()
        pidfile = open(pidfilename, 'w')
        pidfile.write(str(current_pid))
        pidfile.close()

    def read_pid(file_path):
        '''Read pid from a pid file'''
        f = open(file_path)
        pidv = f.read()
        return pidv.strip()

    def check_pid(pid):
        """ Check For the existence of a unix pid. """
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        else:
            return True

    def deco_single_instance(func):
        '''Make sure only one instance of this program with the same parameters runs'''
        if os.path.exists(pidfilename):
            pidv = read_pid(pidfilename)
            if check_pid(int(pidv)):
                get_logger()().info("There's already an instance of this program, pid : %s", pidv)
                sys.exit()
            else:
                os.remove(pidfilename)
        create_pid(pidfilename)

        @functools.wraps(func)
        def _wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return _wrapper  # true decorator

    return deco_single_instance


def debug_wrapper(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kw):
        try:
            start_at = time.time()
            r = fn(*args, **kw)
        except Exception as err:
            get_logger().exception(err)
            raise
        else:
            return r
        finally:
            get_logger().info('%s cost {:.2f}s'.format(time.time() - start_at), fn)

    return wrapper


def memo(fn):
    cache = {}
    miss = object()
    @functools.wraps(fn)
    def wrapper(*args):
        result = cache.get(args, miss)
        if result is miss:
            result = fn(*args)
            cache[args] = result
        return result
    return wrapper


class TimeoutError(Exception):
    def __init__(self, value="Timed Out"):
        self.value = value
    def __str__(self):
        return repr(self.value)


def timeout(seconds_before_timeout):
    def decorate(f):
        def handler(signum, frame):
            raise TimeoutError()
        def new_f(*args, **kwargs):
            old = signal.signal(signal.SIGALRM, handler)
            signal.alarm(seconds_before_timeout)
            try:
                result = f(*args, **kwargs)
            finally:
                signal.signal(signal.SIGALRM, old)
            signal.alarm(0)
            return result
        new_f.func_name = f.func_name
        return new_f
    return decorate
