#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from kipp3.libs import KippException


class KippRunnerException(KippException):
    pass


class KippRunnerTimeoutException(KippRunnerException):
    pass


class KippRunnerSIGTERMException(KippRunnerException):
    pass
