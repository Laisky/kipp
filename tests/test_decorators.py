#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import os
import time

from .base import BaseTestCase
from kipp.decorator import timeout_cache, timer


class UtilsTestCase(BaseTestCase):
    def test_timeout_cache(self):
        @timeout_cache(expires_sec=2)
        def demo(n=None):
            return time.time()

        r = demo()
        self.assertEqual(demo(), r)
        time.sleep(1)
        self.assertEqual(demo(), r)
        self.assertNotEqual(demo(1), r)
        time.sleep(2)
        self.assertNotEqual(demo(), r)

    def test_timer(self):
        @timer
        def demo():
            time.sleep(2)

        demo()
