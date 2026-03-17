#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import copy
import os
import sys
from types import ModuleType
from unittest import TestCase
from unittest.mock import patch, MagicMock

from kipp.options import BaseOptions, OptionKeyTypeConflictError
from kipp.options.exceptions import KippOptionsException


class BaseOptionsSetGetTestCase(TestCase):
    """Tests for BaseOptions basic set/get/del operations."""

    def setUp(self):
        self.opt = BaseOptions()

    def test_set_and_get_simple(self):
        self.opt.set_option("key", "value")
        self.assertEqual(self.opt.get_option("key"), "value")

    def test_getitem(self):
        self.opt["key"] = 123
        self.assertEqual(self.opt["key"], 123)

    def test_getattr(self):
        self.opt.set_option("myattr", "val")
        self.assertEqual(self.opt.myattr, "val")

    def test_get_missing_raises_attribute_error(self):
        with self.assertRaises(AttributeError):
            self.opt.get_option("nonexistent")

    def test_getitem_missing_raises_attribute_error(self):
        with self.assertRaises(AttributeError):
            self.opt["nonexistent"]

    def test_getattr_missing_raises_attribute_error(self):
        with self.assertRaises(AttributeError):
            _ = self.opt.nonexistent

    def test_del_option(self):
        self.opt.set_option("key", "value")
        self.opt.del_option("key")
        with self.assertRaises(AttributeError):
            self.opt.get_option("key")

    def test_delitem(self):
        self.opt["key"] = "val"
        del self.opt["key"]
        with self.assertRaises(AttributeError):
            self.opt["key"]

    def test_del_nonexistent_no_error(self):
        self.opt.del_option("missing")

    def test_contains_true(self):
        self.opt.set_option("present", 1)
        self.assertIn("present", self.opt)

    def test_contains_false(self):
        self.assertNotIn("absent", self.opt)

    def test_overwrite_value(self):
        self.opt.set_option("key", 1)
        self.opt.set_option("key", 2)
        self.assertEqual(self.opt["key"], 2)

    def test_various_value_types(self):
        self.opt.set_option("int", 42)
        self.opt.set_option("str", "hello")
        self.opt.set_option("list", [1, 2, 3])
        self.opt.set_option("dict", {"a": 1})
        self.opt.set_option("none", None)
        self.assertEqual(self.opt["int"], 42)
        self.assertEqual(self.opt["str"], "hello")
        self.assertEqual(self.opt["list"], [1, 2, 3])
        self.assertEqual(self.opt["dict"], {"a": 1})
        self.assertIsNone(self.opt["none"])

    def test_set_and_delete_then_set_again(self):
        self.opt.set_option("key", "first")
        self.opt.del_option("key")
        self.opt.set_option("key", "second")
        self.assertEqual(self.opt["key"], "second")


class BaseOptionsDottedKeyTestCase(TestCase):
    """Tests for dotted key creation and nested access."""

    def setUp(self):
        self.opt = BaseOptions()

    def test_dotted_key_creates_nested(self):
        self.opt.set_option("a.b.c", 123)
        self.assertIsInstance(self.opt["a"], BaseOptions)
        self.assertIsInstance(self.opt["a.b"], BaseOptions)
        self.assertEqual(self.opt["a.b.c"], 123)

    def test_dotted_key_access(self):
        self.opt.set_option("x.y", "val")
        self.assertEqual(self.opt["x.y"], "val")
        child_x = self.opt["x"]
        self.assertEqual(child_x["y"], "val")

    def test_multiple_dotted_keys_same_parent(self):
        self.opt.set_option("a.b", 1)
        self.opt.set_option("a.c", 2)
        self.assertEqual(self.opt["a.b"], 1)
        self.assertEqual(self.opt["a.c"], 2)

    def test_contains_dotted_key(self):
        self.opt.set_option("a.b.c", 99)
        self.assertIn("a.b.c", self.opt)
        self.assertIn("a.b", self.opt)
        self.assertIn("a", self.opt)
        self.assertNotIn("a.b.d", self.opt)

    def test_dotted_key_missing_intermediate(self):
        with self.assertRaises(AttributeError):
            self.opt["a.b.c"]

    def test_deeply_nested_dotted_key(self):
        self.opt.set_option("a.b.c.d.e", "deep")
        self.assertEqual(self.opt["a.b.c.d.e"], "deep")
        self.assertIsInstance(self.opt["a.b.c.d"], BaseOptions)

    def test_dotted_key_get_partial_path_returns_baseoptions(self):
        self.opt.set_option("x.y.z", 10)
        intermediate = self.opt.get_option("x.y")
        self.assertIsInstance(intermediate, BaseOptions)
        self.assertEqual(intermediate["z"], 10)

    def test_dotted_key_missing_leaf(self):
        self.opt.set_option("a.b", 1)
        with self.assertRaises(AttributeError):
            self.opt["a.c"]

    def test_set_dotted_key_then_check_contains_nonexistent_sibling(self):
        self.opt.set_option("db.host", "localhost")
        self.assertIn("db.host", self.opt)
        self.assertNotIn("db.port", self.opt)


class BaseOptionsOverwriteConflictTestCase(TestCase):
    """Tests for OptionKeyTypeConflictError behavior."""

    def test_conflict_when_overwrite_not_allowed(self):
        opt = BaseOptions(is_allow_overwrite_child_opt=False)
        opt.set_option("a.b.c", 123)
        with self.assertRaises(OptionKeyTypeConflictError):
            opt.set_option("a.b", 1)

    def test_overwrite_allowed(self):
        opt = BaseOptions(is_allow_overwrite_child_opt=True)
        opt.set_option("a.b.c", 123)
        opt.set_option("a.b", 1)
        self.assertEqual(opt["a.b"], 1)
        with self.assertRaises(AttributeError):
            opt["a.b.c"]

    def test_overwrite_leaf_to_subtree_not_allowed(self):
        opt = BaseOptions(is_allow_overwrite_child_opt=False)
        opt.set_option("a.b", 42)
        with self.assertRaises(OptionKeyTypeConflictError):
            opt.set_option("a.b.c", 99)

    def test_overwrite_leaf_to_subtree_allowed(self):
        opt = BaseOptions(is_allow_overwrite_child_opt=True)
        opt.set_option("a.b", 42)
        opt.set_option("a.b.c", 99)
        self.assertEqual(opt["a.b.c"], 99)

    def test_is_allow_overwrite_child_opt_setter_validation(self):
        opt = BaseOptions()
        with self.assertRaises(AssertionError):
            opt.is_allow_overwrite_child_opt = "not_bool"
        with self.assertRaises(AssertionError):
            opt.is_allow_overwrite_child_opt = 123
        opt.is_allow_overwrite_child_opt = False
        self.assertFalse(opt.is_allow_overwrite_child_opt)

    def test_option_key_type_conflict_is_kipp_options_exception(self):
        self.assertTrue(issubclass(OptionKeyTypeConflictError, KippOptionsException))

    def test_create_option_returns_new_baseoptions(self):
        opt = BaseOptions()
        child = opt.create_option()
        self.assertIsInstance(child, BaseOptions)
        self.assertIsNot(child, opt)

    def test_default_allows_overwrite(self):
        opt = BaseOptions()
        self.assertTrue(opt.is_allow_overwrite_child_opt)

    def test_toggle_overwrite_at_runtime(self):
        opt = BaseOptions()
        opt.set_option("a.b", 1)
        opt.is_allow_overwrite_child_opt = False
        with self.assertRaises(OptionKeyTypeConflictError):
            opt.set_option("a.b.c", 2)


class OptionsSingletonTestCase(TestCase):
    """Tests for Options singleton behavior."""

    def setUp(self):
        self.origin_modules = {}
        for m, i in sys.modules.items():
            if m == "kipp" or m.startswith("kipp.") or m == "Utilities" or m.startswith("Utilities."):
                self.origin_modules[m] = i

    def tearDown(self):
        for m in list(sys.modules.keys()):
            if m == "kipp" or m.startswith("kipp.") or m == "Utilities" or m.startswith("Utilities."):
                del sys.modules[m]
        sys.modules.update(self.origin_modules)

    def test_options_is_singleton(self):
        from kipp.options import options as opt1
        from kipp.options import options as opt2
        self.assertIs(opt1, opt2)

    def test_options_inherits_base_options(self):
        from kipp.options import options, BaseOptions
        self.assertIsInstance(options, BaseOptions)

    def test_opt_and_options_are_same(self):
        from kipp.options import opt, options
        self.assertIs(opt, options)

    def test_options_multiple_instantiations_same_object(self):
        from kipp.options import Options
        o1 = Options()
        o2 = Options()
        self.assertIs(o1, o2)


class OptionsCascadingLookupTestCase(TestCase):
    """Tests for Options cascading lookup priority."""

    def setUp(self):
        self.origin_modules = {}
        for m, i in sys.modules.items():
            if m == "kipp" or m.startswith("kipp.") or m == "Utilities" or m.startswith("Utilities."):
                self.origin_modules[m] = i

    def tearDown(self):
        for m in list(sys.modules.keys()):
            if m == "kipp" or m.startswith("kipp.") or m == "Utilities" or m.startswith("Utilities."):
                del sys.modules[m]
        sys.modules.update(self.origin_modules)

    def test_inner_settings_highest_priority(self):
        from kipp.options import options as opt

        os.environ["MY_TEST_KEY_XYZ"] = "from_env"
        try:
            opt._environ = os.environ.copy()
            opt.set_option("MY_TEST_KEY_XYZ", "from_inner")
            self.assertEqual(opt["MY_TEST_KEY_XYZ"], "from_inner")
        finally:
            opt.del_option("MY_TEST_KEY_XYZ")
            del os.environ["MY_TEST_KEY_XYZ"]

    def test_environ_fallback(self):
        from kipp.options import options as opt

        os.environ["KIPP_TEST_ENV_ONLY_VAR"] = "env_value"
        opt._environ = copy.deepcopy(os.environ)
        try:
            val = opt["KIPP_TEST_ENV_ONLY_VAR"]
            self.assertEqual(val, "env_value")
        finally:
            del os.environ["KIPP_TEST_ENV_ONLY_VAR"]

    def test_command_args_over_environ(self):
        from kipp.options import options as opt

        os.environ["MY_CMD_TEST"] = "env_val"
        opt._environ = copy.deepcopy(os.environ)

        ns = argparse.Namespace(MY_CMD_TEST="cmd_val")
        opt._command_args = ns
        try:
            val = opt["MY_CMD_TEST"]
            self.assertEqual(val, "cmd_val")
        finally:
            opt._command_args = None
            del os.environ["MY_CMD_TEST"]

    def test_inner_over_command_args(self):
        from kipp.options import options as opt

        ns = argparse.Namespace(INNER_TEST="cmd_val")
        opt._command_args = ns
        opt.set_option("INNER_TEST", "inner_val")
        try:
            self.assertEqual(opt["INNER_TEST"], "inner_val")
        finally:
            opt.del_option("INNER_TEST")
            opt._command_args = None

    def test_missing_key_raises(self):
        from kipp.options import options as opt
        with self.assertRaises(AttributeError):
            opt["completely_nonexistent_key_abc123"]

    def test_env_settings_fallback(self):
        from kipp.options import options as opt

        mock_env_settings = ModuleType("mock_env_settings")
        mock_env_settings.SPECIAL_KEY = "from_env_settings"
        opt._env_settings = mock_env_settings
        try:
            self.assertEqual(opt["SPECIAL_KEY"], "from_env_settings")
        finally:
            opt._env_settings = None

    def test_private_settings_fallback(self):
        from kipp.options import options as opt

        mock_private = ModuleType("mock_private")
        mock_private.PRIV_KEY = "from_private"
        opt._private_settings = mock_private
        try:
            self.assertEqual(opt["PRIV_KEY"], "from_private")
        finally:
            opt._private_settings = None

    def test_project_settings_fallback(self):
        from kipp.options import options as opt

        mock_project = ModuleType("mock_project")
        mock_project.PROJ_KEY = "from_project"
        opt._project_settings = mock_project
        try:
            self.assertEqual(opt["PROJ_KEY"], "from_project")
        finally:
            opt._project_settings = None

    def test_env_settings_over_private(self):
        from kipp.options import options as opt

        mock_env = ModuleType("mock_env")
        mock_env.PRIORITY_KEY = "env_settings"
        mock_private = ModuleType("mock_private")
        mock_private.PRIORITY_KEY = "private"
        opt._env_settings = mock_env
        opt._private_settings = mock_private
        try:
            self.assertEqual(opt["PRIORITY_KEY"], "env_settings")
        finally:
            opt._env_settings = None
            opt._private_settings = None

    def test_private_over_project(self):
        from kipp.options import options as opt

        mock_private = ModuleType("mock_private")
        mock_private.PRI_KEY = "private"
        mock_project = ModuleType("mock_project")
        mock_project.PRI_KEY = "project"
        opt._private_settings = mock_private
        opt._project_settings = mock_project
        try:
            self.assertEqual(opt["PRI_KEY"], "private")
        finally:
            opt._private_settings = None
            opt._project_settings = None

    def test_del_inner_falls_back_to_environ(self):
        from kipp.options import options as opt

        os.environ["FALLBACK_TEST"] = "env_val"
        opt._environ = copy.deepcopy(os.environ)
        opt.set_option("FALLBACK_TEST", "inner_val")
        self.assertEqual(opt["FALLBACK_TEST"], "inner_val")
        opt.del_option("FALLBACK_TEST")
        self.assertEqual(opt["FALLBACK_TEST"], "env_val")
        del os.environ["FALLBACK_TEST"]


class OptionsSetCommandArgsTestCase(TestCase):
    """Tests for Options.set_command_args."""

    def setUp(self):
        self.origin_modules = {}
        for m, i in sys.modules.items():
            if m == "kipp" or m.startswith("kipp.") or m == "Utilities" or m.startswith("Utilities."):
                self.origin_modules[m] = i

    def tearDown(self):
        for m in list(sys.modules.keys()):
            if m == "kipp" or m.startswith("kipp.") or m == "Utilities" or m.startswith("Utilities."):
                del sys.modules[m]
        sys.modules.update(self.origin_modules)

    def test_set_command_args_stores_args(self):
        from kipp.options import options as opt

        ns = argparse.Namespace(foo="bar")
        opt.set_command_args(ns)
        try:
            self.assertEqual(opt["foo"], "bar")
        finally:
            opt._command_args = None

    def test_set_command_args_with_env_attribute(self):
        """If args has 'env', load_specifical_settings is called."""
        from kipp.options import options as opt

        ns = argparse.Namespace(env="staging")
        with patch.object(opt, "load_specifical_settings") as mock_load:
            opt.set_command_args(ns)
            mock_load.assert_called_with("staging")
        opt._command_args = None


class ArgparseMixinTestCase(TestCase):
    """Tests for ArgparseMixin via Options."""

    def setUp(self):
        self.origin_modules = {}
        for m, i in sys.modules.items():
            if m == "kipp" or m.startswith("kipp.") or m == "Utilities" or m.startswith("Utilities."):
                self.origin_modules[m] = i

    def tearDown(self):
        for m in list(sys.modules.keys()):
            if m == "kipp" or m.startswith("kipp.") or m == "Utilities" or m.startswith("Utilities."):
                del sys.modules[m]
        sys.modules.update(self.origin_modules)

    def test_add_argument_and_parse(self):
        from kipp.options import options as opt

        opt.add_argument("--test-flag", type=str, default="default_val")
        args = opt.parse_args([])
        try:
            self.assertEqual(args.test_flag, "default_val")
            self.assertEqual(opt["test_flag"], "default_val")
        finally:
            opt._command_args = None

    def test_add_argument_creates_parser_lazily(self):
        from kipp.options import options as opt

        if hasattr(opt, "_parser"):
            delattr(opt, "_parser")
        opt.add_argument("--lazy", type=int, default=0)
        self.assertTrue(hasattr(opt, "_parser"))
        opt._command_args = None

    def test_parse_args_with_values(self):
        from kipp.options import options as opt

        opt.add_argument("--port", type=int, default=8080)
        args = opt.parse_args(["--port", "9090"])
        try:
            self.assertEqual(args.port, 9090)
            self.assertEqual(opt["port"], 9090)
        finally:
            opt._command_args = None

    def test_add_argument_multiline_help_dedented(self):
        from kipp.options import options as opt

        help_text = """
            This is
            multiline help
        """
        opt.add_argument("--multi", help=help_text)
        # Should not raise; parser is set up
        self.assertTrue(hasattr(opt, "_parser"))
        opt._command_args = None

    def test_setup_argparse_explicit(self):
        from kipp.options import options as opt

        opt.setup_argparse("test_prog")
        self.assertIsNotNone(opt._parser)
        self.assertEqual(opt._parser.prog, "test_prog")
        opt._command_args = None


class KippOptionsExceptionTestCase(TestCase):
    """Tests for KippOptionsException hierarchy."""

    def test_inherits_kipp_exception(self):
        from kipp.libs.exceptions import KippException
        self.assertTrue(issubclass(KippOptionsException, KippException))

    def test_option_key_conflict_inherits(self):
        self.assertTrue(issubclass(OptionKeyTypeConflictError, KippOptionsException))

    def test_raise_and_catch(self):
        with self.assertRaises(KippOptionsException):
            raise OptionKeyTypeConflictError("conflict")
