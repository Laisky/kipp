#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import

from tornado.gen import TimeoutError


class KippException(Exception):
    pass


class KippAIOException(KippException):
    pass


class KippAIOTimeoutError(KippAIOException):
    pass
