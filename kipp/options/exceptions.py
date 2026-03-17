#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

from kipp.libs import KippException


class KippOptionsException(KippException):
    """Base exception for all kipp.options errors (settings lookup failures, conflicts, etc.)."""

    pass
