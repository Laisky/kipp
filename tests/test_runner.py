#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import os
import sys
from unittest import skipIf

from kipp.options import options as opt
from .base import BaseTestCase, patch


@skipIf(True, "need utilities")
class RunnerTestCase(BaseTestCase):
    def setUp(self):
        os.environ["TEST_VAR_B"] = "aaaa"

        class MovotoMock(object):
            def __getattr__(self, name):
                if name == "settings":
                    return SettingsMock()
                else:
                    return MovotoMock()

        class SettingsMock(object):
            def __getattr__(self, name):
                if name.startswith("_"):
                    raise AttributeError
                if name == "not_exists":
                    raise AttributeError

                return "yeo"

        sys.modules["Utilities"] = MovotoMock()
        sys.modules["Utilities.movoto"] = MovotoMock()

        self.origin_modules = {}
        for m, i in sys.modules.items():
            if (
                m == "kipp"
                or m.startswith("kipp.")
                or m == "Utilities"
                or m.startswith("Utilities.")
            ):
                self.origin_modules.update({m: i})

        from kipp.runner.runner import runner, setup_settings

        setup_settings()
        self.runner = runner
        opt.set_option("timeout", None)
        opt.set_option("lock", False)

    def tearDown(self):
        for m in list(sys.modules.keys()):
            if (
                m == "kipp"
                or m.startswith("kipp.")
                or m == "Utilities"
                or m.startswith("Utilities.")
            ):
                del sys.modules[m]

        sys.modules.update(self.origin_modules)

    def test_runner(self):
        self.assertRaises(TypeError, self.runner)
        with patch("kipp.runner.runner.RunStatsMonitor") as m:
            with patch("subprocess.Popen") as pm:
                self.assertRaises(RuntimeError, self.runner, "ls")
                self.assertEqual(pm.call_args_list[0][0][0], ["ls"])
                self.assertEqual(len(m().start.call_args_list), 1)
                self.assertEqual(len(m().fail.call_args_list), 1)
