#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import datetime
from unittest import TestCase

import pytz

from kipp.utils import date


UTC = pytz.timezone("utc")
CST = pytz.timezone("Asia/Shanghai")


class DateUtilTestCase(TestCase):
    def test_parse_dtstr(self):
        expect_dt = datetime.datetime(2017, 1, 2, 13, 12)
        expect_utc = UTC.localize(expect_dt)
        expect_rep_cst = expect_utc.replace(tzinfo=CST)
        expect_as_cst = expect_utc.astimezone(tz=CST)
        for dt_str in [
            "2017/1/2 13:12:00",
            "1/2/2017 13:12:00",
            "1/2/2017 1:12:00 PM",
            "1/2/2017 1:12:00PM",
            "Jan 2 2017 13:12:00",
            "2017/01/02 13:12:00",
            "2017/01/02 13:12:00.000",
            "2017/01/02 13:12:00Z",
            "2017/01/02 13:12:00 +00:00",
        ]:
            dt = date.parse_dtstr(dt_str, naive=True)
            self.assertEqual(dt, expect_dt)

            dt_utc = date.parse_dtstr(dt_str)
            self.assertEqual(dt_utc, expect_utc)

            dt_rep_cst = date.parse_dtstr(dt_str, replace_tz=CST)
            self.assertEqual(dt_rep_cst, expect_rep_cst)

            dt_as_cst = date.parse_dtstr(dt_str, convert_tz=CST)
            self.assertEqual(dt_as_cst, expect_as_cst)

    def test_special_dtste(self):
        expect_dt = UTC.localize(datetime.datetime(1900, 1, 1, 11, 42))
        for dt_str in [
            "1142",
            "11:42 NoOn",
            "11:42 Noon",
            "11:42 noon",
        ]:
            dt = date.parse_dtstr(dt_str)
            self.assertEqual(dt, expect_dt)

    def test_timezones(self):
        self.assertEqual(UTC, date.UTC)
        self.assertEqual(CST, date.CST)

        expect_dt = datetime.datetime(2017, 1, 2, 13)
        for dt_str in [
            "2017/01/02 21:00:00 +08:00",
            "2017/01/02 22:00:00 +09:00",
            "2017/01/02 22:00:00 +9",
            "2017/01/02 23:00:00 +10:00",
            "2017/01/02 23:00:00 +10",
            "2017/01/02 23:00:00+10",
            "2017/01/02 05:00:00 -08:00",
            "2017/01/02 08:00:00 -05:00",
            "2017/01/02 09:00:00 -04:00",
            "2017/01/02 09:00:00 -04",
            "2017/01/02 09:00:00 -4",
            "2017/01/02 09:00:00-4",
        ]:
            dt = date.parse_dtstr(dt_str, naive=True)
            self.assertEqual(dt, expect_dt)

    def test_ignore_tz(self):
        expect_dt = datetime.datetime(2017, 1, 2, 13)
        for dt_str in [
            "2017/01/02 13:00:00 +08:00",
            "2017/01/02 13:00:00 +08",
            "2017/01/02 13:00:00 +8",
            "2017/01/02 13:00:00+8",
            "2017/01/02T13:00:00+8",
            "2017/01/02 13:00:00 +09:00",
            "2017/01/02 13:00:00 +10:00",
            "2017/01/02 13:00:00 -08:00",
            "2017/01/02 13:00:00 -05:00",
            "2017/01/02 13:00:00 -04:00",
        ]:
            dt = date.parse_dtstr(dt_str, ignore_tz=True, naive=True)
            self.assertEqual(dt, expect_dt)
