#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import os
import time

from .base import BaseTestCase
from kipp.utils import (
    IOTA,
    generate_validate_fname,
    sleep,
    DFAFilter,
)


class UtilsTestCase(BaseTestCase):
    def test_iota(self):
        iota = IOTA()
        self.assertEqual(iota(), 0)
        self.assertEqual(iota(), 1)
        self.assertEqual(iota(), 2)
        self.assertEqual(iota(), 3)
        self.assertEqual(iota(), 4)
        self.assertEqual(iota(2), 6)
        self.assertEqual(iota(0), 6)
        self.assertEqual(iota(-1), 5)
        self.assertEqual(iota.count(), 6)
        self.assertEqual(iota.count(2), 8)
        self.assertEqual(iota.count(0), 8)
        self.assertEqual(iota.count(-1), 7)
        self.assertEqual(iota.latest(), 7)
        self.assertEqual(iota(), 8)
        self.assertRaises(ValueError, iota, "str")
        self.assertRaises(ValueError, iota.count, "str")

    def test_generate_validate_fname(self):
        cases = (
            ("123 123", "123_123"),
            ("  (*d  02 s  ", "d_02_s"),
            ("俄1方123将为 a120$(#@*", "1_123_a120"),
        )
        for case in cases:
            fname = generate_validate_fname(case[0])
            self.assertEqual(os.path.split(fname)[-1], "{}.lock".format(case[1]))

    def test_sleep(self):
        start_at = time.time()
        sleep(1.5)
        self.assertGreaterEqual(time.time() - start_at, 1.5)

    def test_dfafilter(self):
        keywords = set(["一二三", "一二二", "三二一"])
        raw_text = """
            解决2力度 打击2iu 日3 一二三进ℹ️节日2 一二二将诶饿了13饿三二
            """

        f = DFAFilter()
        f.build_chains(keywords)
        results = f.load_keywords(raw_text)
        self.assertEqual(results, set(["一二三", "一二二"]))
