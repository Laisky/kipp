#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
---------------
Kipp Exceptions
---------------

KippException
  ├─ KippAIOException
  │    └─ KippAIOTimeoutError
  ├─ DBError
  │    ├─ DBValidateError
  │    ├─ DuplicateIndexError
  │    └─ RecordNotFound
  ├─ KippRunnerException
  │    └─ KippRunnerTimeoutException

"""


from __future__ import unicode_literals

from kipp.libs.exceptions import (KippAIOException, KippAIOTimeoutError,
                                  KippException)
from kipp.models.exceptions import (DBError, DBValidateError,
                                    DuplicateIndexError, RecordNotFound)
