#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations, unicode_literals, absolute_import


class KippException(Exception):
    """Base exception for all Kipp operations.

    Catch this to handle any Kipp error uniformly without coupling to
    specific failure modes.
    """

    pass


class KippAIOException(KippException):
    """Base exception for async-related Kipp failures.

    Separating sync and async hierarchies lets callers distinguish between
    errors that originate in the event loop vs. synchronous code paths.
    """

    pass


class KippAIOTimeoutError(KippAIOException):
    """Raised when an async operation exceeds its deadline.

    Kept distinct from asyncio.TimeoutError so that Kipp-level timeout
    handling does not accidentally swallow unrelated asyncio timeouts.
    """

    pass
