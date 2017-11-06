#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
---------------
Datatime Utilis
---------------

Usage
::

    # import timezone constants
    from kipp.utils import UTC, CST

    # import datetime functions
    from kipp.utils import parse_dtstr, utcnow, cstnow


"""

from __future__ import unicode_literals
import re
import datetime
from future.utils import iteritems

import pytz
import maya


UTC = pytz.timezone('utc')
CST = pytz.timezone('Asia/Shanghai')

_SPECIAL_DTSTR_REGEX_MAP = {
    re.compile('^(\d{4})$'): '%H%M',
    re.compile('^(\d{2}:\d{2}) noon$', flags=re.I): '%H:%M',
}


def _parse_special_dtstr(dtstr):
    """Parse MLSes weird datetime string formats"""
    for dt_regx, dt_fmt in iteritems(_SPECIAL_DTSTR_REGEX_MAP):
        m = dt_regx.match(dtstr)
        if m:
            _dtstr = m.groups()[0]
            return UTC.localize(datetime.datetime.strptime(_dtstr, dt_fmt))


_IGNORE_TZ_REGEX = re.compile('[+\-][0-9:]{1,5}$')


def _extrace_dtstr_exclude_tz(dtstr):
    r = _IGNORE_TZ_REGEX.search(dtstr)
    if not r:
        return dtstr

    return dtstr[: r.start()]


def parse_dtstr(date_str,
                naive=False,
                replace_tz=None,
                convert_tz=None,
                ignore_tz=False):
    """Parse datetime string to datetime object

    Default timezone is UTC.

    Args:
        date_str (str): origin datetime string.
        naive (bool, default=False): if True, return a naive datetime object.
        replace_tz (timezone):replace to che specified timezone,
            without change the literal datetime attributes.
        convert_tz (timezone, default=UTC): convert to specified timezone.
        ignore_tz (bool, default=False): do not parse timezone.

    Raises:
        ValueError: if cannot parse the date_str.

    Examples:
    ::
        from kipp.utils import parse_dtstr

        dtstr = '2017/1/1 13:00 +08:00'
        dt = parse_dtstr(dtstr)

    """
    if ignore_tz:
        date_str = _extrace_dtstr_exclude_tz(date_str)

    dt = _parse_special_dtstr(date_str) or maya.parse(date_str).datetime()
    if naive:
        dt = dt.replace(tzinfo=None)
    elif replace_tz:
        dt = dt.replace(tzinfo=replace_tz)
    elif convert_tz:
        dt = dt.astimezone(tz=convert_tz)

    return dt


def utcnow(is_naive=False):
    """Get current datetime with UTC timezone"""
    dt = datetime.datetime.utcnow()
    if not is_naive:
        dt =  UTC.localize(dt)

    return dt


def cstnow(is_naive=False):
    """Get current datetime with cst timezone"""
    dt = utcnow()
    if not is_naive:
        dt = dt.astimezone(CST)

    return True
