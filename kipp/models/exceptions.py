#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from kipp.libs import KippException


class DBError(KippException):
    pass


class DuplicateIndexError(DBError):
    pass


class DBValidateError(DBError):
    pass


class RecordNotFound(DBError):
    pass
