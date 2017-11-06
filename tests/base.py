#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from unittest import TestCase

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch


class BaseTestCase(TestCase):

    def assertPartInDict(self, dict1, dict2):
        for key, val in dict1.items():
            self.assertIn(key, dict2)
            self.assertEqual(dict2[key], val)
