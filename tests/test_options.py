#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import os
import sys
import argparse
import importlib
from unittest import TestCase

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

from kipp.options import BaseOptions
from kipp.exceptions import OptionKeyTypeConflictError


class OptionsTestCase(TestCase):
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

        from kipp.options import options as opt

        self.opt = opt
        self.origin_modules = {}
        for m, i in sys.modules.items():
            if (
                m == "kipp"
                or m.startswith("kipp.")
                or m == "Utilities"
                or m.startswith("Utilities.")
            ):
                self.origin_modules.update({m: i})

    def tearDown(self):
        # try:
        #     self.opt.unpatch_utilities()
        # except Exception:
        #     pass

        for m in list(sys.modules.keys()):
            if (
                m == "kipp"
                or m.startswith("kipp.")
                or m == "Utilities"
                or m.startswith("Utilities.")
            ):
                del sys.modules[m]

        sys.modules.update(self.origin_modules)

    def test_singleton(self):
        from kipp.options import options as opt

        self.assertIs(opt, self.opt)

    # def test_env(self):
    #     parser = argparse.ArgumentParser()
    #     parser.add_argument('--env', type=str)
    #     args = parser.parse_args(['--env=test'])

    #     orig_import_module = importlib.import_module

    #     def mock_import_lib(name, *args, **kw):
    #         class FakeSettings(object):

    #             def __getattr__(self, name):
    #                 if name == 'not_exists':
    #                     raise AttributeError

    #                 return 123

    #         if name == 'settings.settings_test':
    #             return FakeSettings()
    #         else:
    #             return orig_import_module(name, *args, **kw)

    #     with patch('importlib.import_module') as mock:
    #         try:
    #             mock.side_effect = mock_import_lib
    #             self.opt.set_command_args(args)
    #             self.assertEqual(self.opt['test_var_a'], 123)
    #         finally:
    #             self.opt._env_settings = None
    #             if 'settings.settings_test' in sys.modules:
    #                 del sys.modules['settings.settings_test']

    def test_command_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--test_var_c", type=int)
        args = parser.parse_args(["--test_var_c=555"])

        # self.opt.set_command_args(args, is_patch_utilies=False)
        # self.assertEqual(self.opt['test_var_c'], 555)

    def test_set_and_del_opt(self):
        self.assertRaises(AttributeError, lambda: self.opt.abc)
        self.opt.set_option("abc", 123)
        self.assertIn("abc", self.opt)  # __contains__
        self.assertNotIn("not_exists", self.opt)
        self.assertEqual(self.opt.abc, 123)  # __getitem__
        self.opt.del_option("abc")
        self.assertRaises(AttributeError, lambda: self.opt.abc)
        self.opt["abc"] = 123  # __setitem__
        self.assertEqual(self.opt.abc, 123)
        del self.opt["abc"]  # __delitem__
        self.assertRaises(AttributeError, lambda: self.opt.abc)

    # def test_set_option(self):
    #     self.opt.set_option('n', 100)
    #     self.assertEqual(self.opt.n, 100)
    #     self.opt.n += 1
    #     self.assertEqual(self.opt.n, 101)
    #     self.opt.set_option('n', 0)
    #     self.assertEqual(self.opt.n, 0)

    # def test_patch(self):
    #     class EnvSettingsMock(object):
    #         def __getattr__(self, name):
    #             if name == 'PATCHED_IN_ENV_SETT':
    #                 return 'nope'

    #             raise AttributeError

    #     class SettingsMock(object):
    #         def __getattr__(self, name):
    #             return EnvSettingsMock()

    #     sys.modules['settings'] = SettingsMock()
    #     sys.modules['settings.settings_test'] = EnvSettingsMock()

    #     self.opt.patch_utilities()
    #     self.opt.load_specifical_settings('test')
    #     from Utilities.movoto import settings
    #     self.assertEqual(settings.ABC, 'yeo')
    #     self.assertEqual(settings.PATCHED_IN_ENV_SETT, 'nope')

    #     self.opt.unpatch_utilities()
    #     self.assertEqual(settings.ABC, 'yeo')
    #     self.assertEqual(settings.PATCHED_IN_ENV_SETT, 'yeo')

    #     del sys.modules['settings']
    #     del sys.modules['settings.settings_test']

    def test_argparse(self):
        self.opt.add_argument("--test", type=str)
        self.opt.add_argument("--test2", type=str)
        self.opt.add_argument("--test3", type=str, default="default")
        self.opt.parse_args(["--test=1", "--test2=qq"])

        self.assertEqual(self.opt.test, "1")
        self.assertEqual(self.opt.test2, "qq")
        self.assertEqual(self.opt.test3, "default")

    def test_children(self):
        self.opt.set_option("a.b.c", 123)
        self.opt.set_option("a.c", 22)
        self.opt.is_allow_overwrite_child_opt = False

        def fault_set_is_allow_overwrite_child_opt():
            self.opt.is_allow_overwrite_child_opt = 123

        self.assertRaises(AssertionError, fault_set_is_allow_overwrite_child_opt)

        print(self.opt._inner_settings)
        print(self.opt._inner_settings["a"]._inner_settings)

        self.assertIsInstance(self.opt["a"], BaseOptions)
        self.assertIsInstance(self.opt["a.b"], BaseOptions)
        self.assertRaises(
            OptionKeyTypeConflictError, lambda: self.opt.set_option("a.b", 1)
        )
        self.assertEqual(self.opt["a.b.c"], 123)
        self.assertEqual(self.opt["a.c"], 22)

        # allow conflict
        self.opt.is_allow_overwrite_child_opt = True
        self.opt.set_option("a.b", 11)
        self.assertEqual(self.opt["a.b"], 11)
        child_a = self.opt.a
        self.assertEqual(child_a.b, 11)
        self.assertRaises(AttributeError, lambda: self.opt["a.b.c"])
