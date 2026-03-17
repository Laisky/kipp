#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
-----------------
Datetime Utilities
-----------------

Timezone-aware datetime parsing and construction.

All returned datetimes are timezone-aware (UTC by default) unless
explicitly requested otherwise via ``naive=True``. This avoids the
common pitfall of comparing naive and aware datetimes.

Usage::

    from kipp.utils import UTC, CST, parse_dtstr, utcnow, cstnow

"""

from __future__ import annotations

import re
import datetime

import pytz
import maya


UTC: pytz.BaseTzInfo = pytz.timezone("utc")
CST: pytz.BaseTzInfo = pytz.timezone("Asia/Shanghai")

# Maps regex patterns to strptime formats for non-standard datetime strings
# encountered in MLS data feeds (e.g., "1300" for 13:00, "13:00 noon")
_SPECIAL_DTSTR_REGEX_MAP: dict[re.Pattern[str], str] = {
    re.compile(r"^(\d{4})$"): "%H%M",
    re.compile(r"^(\d{2}:\d{2}) noon$", flags=re.I): "%H:%M",
}


def _parse_special_dtstr(dtstr: str) -> datetime.datetime | None:
    """Parse MLSes weird datetime string formats.

    Returns None if the string doesn't match any known special format,
    allowing the caller to fall through to the general-purpose parser.
    """
    for dt_regx, dt_fmt in _SPECIAL_DTSTR_REGEX_MAP.items():
        m = dt_regx.match(dtstr)
        if m:
            _dtstr = m.groups()[0]
            return UTC.localize(datetime.datetime.strptime(_dtstr, dt_fmt))

    return None


_IGNORE_TZ_REGEX: re.Pattern[str] = re.compile(r"[+\-][0-9:]{1,5}$")


def _extrace_dtstr_exclude_tz(dtstr: str) -> str:
    """Strip trailing timezone offset (e.g., '+08:00') from a datetime string."""
    r = _IGNORE_TZ_REGEX.search(dtstr)
    if not r:
        return dtstr

    return dtstr[: r.start()]


def parse_dtstr(
    date_str: str,
    naive: bool = False,
    replace_tz: pytz.BaseTzInfo | None = None,
    convert_tz: pytz.BaseTzInfo | None = None,
    ignore_tz: bool = False,
) -> datetime.datetime:
    """Parse datetime string to datetime object.

    Default timezone is UTC. The naive/replace_tz/convert_tz options are
    mutually exclusive -- only the first matching branch applies.

    Args:
        date_str: origin datetime string.
        naive: if True, return a naive datetime object.
        replace_tz: replace to the specified timezone,
            without change the literal datetime attributes.
        convert_tz: convert to specified timezone.
        ignore_tz: do not parse timezone.

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


def utcnow(is_naive: bool = False) -> datetime.datetime:
    """Return the current moment in UTC.

    Args:
        is_naive: If True, strip tzinfo so the result can be compared with
            other naive datetimes (e.g. from legacy DB columns).
    """
    dt = datetime.datetime.now(tz=datetime.timezone.utc)
    # Re-localize via pytz so the tzinfo repr matches the rest of the codebase
    dt = dt.astimezone(UTC)
    if is_naive:
        dt = dt.replace(tzinfo=None)

    return dt


def cstnow(is_naive: bool = False) -> datetime.datetime:
    """Return the current moment in Asia/Shanghai (CST, UTC+8).

    Args:
        is_naive: If True, strip tzinfo after conversion.
    """
    dt = utcnow().astimezone(CST)
    if is_naive:
        dt = dt.replace(tzinfo=None)

    return dt
