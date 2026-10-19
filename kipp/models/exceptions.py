#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Database-layer exceptions.

Hierarchy: KippException -> DBError -> specific error classes.
All DB exceptions share a common base so callers can catch ``DBError``
to handle any database-related failure uniformly.
"""

from __future__ import annotations

from kipp.libs import KippException


class DBError(KippException):
    """Base exception for all database operations."""
    pass


class DuplicateIndexError(DBError):
    """Raised when an insert violates a unique constraint."""
    pass


class DBValidateError(DBError):
    """Raised when input data fails validation before reaching the DB."""
    pass


class RecordNotFound(DBError):
    """Raised when a query expected exactly one result but found none."""
    pass
