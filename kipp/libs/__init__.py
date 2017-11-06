#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import
from functools import wraps
from sys import version_info

from .exceptions import KippException, KippAIOException


PY2 = version_info[0] == 2
PY3 = version_info[0] == 3


def singleton(cls, *args, **kw):
    instances = {}

    @wraps(cls)
    def _singleton():
        if cls not in instances:
            instances[cls] = cls(*args, **kw)
        return instances[cls]

    return _singleton
