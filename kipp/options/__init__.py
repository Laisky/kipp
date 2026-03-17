#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
---------------------
Configuration Manager
---------------------

Uniform arguments entrypoint.

Provides a cascading configuration lookup that checks multiple sources
in priority order: inner settings > CLI args > env vars > env-specific
settings > local settings > project settings.
"""

from __future__ import annotations

import copy
import importlib
import os
from types import ModuleType
from typing import Any

# import sys

# from imp import load_source

from kipp.libs import SingletonMixin
from kipp.utils import get_logger

# from .mlogger import LazyMLogger, ConvertFailureLog
from .arguments import ArgparseMixin
from .exceptions import KippOptionsException


# class UtilitiesMixin:
#     """Load Utilities from PYTHONPATH
#     """

#     def load_utilities_settings(self):
#         for p in sys.path:
#             py_path = os.path.abspath(p)
#             if not os.path.isdir(py_path):
#                 continue

#             for package in next(os.walk(py_path))[1]:
#                 if package != 'Utilities':
#                     continue

#                 if not os.path.isdir(os.path.join(p, package)):
#                     continue

#                 st_fpath = os.path.join(p, package, 'movoto', 'settings.py')
#                 get_logger().info('load utilities from: %s', st_fpath)
#                 return load_source('utils_settings', st_fpath)

#         raise KippOptionsException('Can not found ``Utilities`` in PYTHONPATH')

#     def patch_utilities(self):
#         """Patch Utilities settings"""
#         if getattr(self, '_is_patched_utilities', None):  # do not patch twice
#             return

#         import Utilities
#         from Utilities import movoto as utils_movoto
#         from Utilities.movoto import settings as utils_settings

#         self._orig_utilities = Utilities
#         self._orig_movoto = utils_movoto
#         self._movoto_settings = utils_settings

#         _self = self

#         class SettingsMock(object):

#             def __getattr__(self, name):
#                 if getattr(_self, '_is_patched_utilities', None):
#                     return getattr(_self, name)
#                 else:
#                     return getattr(_self._movoto_settings, name)

#         class MovotoMock(object):

#             def __getattr__(self, name):
#                 if name == 'settings':
#                     return SettingsMock()
#                 else:
#                     return getattr(_self._orig_movoto, name)

#         class UtilitiesMock(object):

#             def __getattr__(self, name):
#                 if name == 'movoto':
#                     return MovotoMock()
#                 else:
#                     return getattr(_self._orig_utilities, name)

#         sys.modules['Utilities'] = UtilitiesMock()
#         sys.modules['Utilities.movoto'] = MovotoMock()
#         sys.modules['Utilities.movoto.settings'] = SettingsMock()

#         self._is_patched_utilities = True

#     def unpatch_utilities(self):
#         if not getattr(self, '_is_patched_utilities', None):
#             return

#         sys.modules['Utilities'] = self._orig_utilities
#         sys.modules['Utilities.movoto'] = self._orig_movoto
#         sys.modules['Utilities.movoto.settings'] = self._orig_movoto.settings
#         self._is_patched_utilities = False


# class MLoggerMixin:
#     def get_mlogger(self, *args, **kw):
#         """(deprecated) Get lazy-init mlogger

#         If pass no arguments, will return last setuped logger

#         DEPRECATED:
#             now you can set logger, then save logger in opt by ``opt.set_option('logger', logger)``
#         """
#         if getattr(self, '_mlogger', None) and not args and not kw:
#             return self._mlogger
#         else:
#             self._mlogger = LazyMLogger(*args, **kw)
#             return self._mlogger


class OptionKeyTypeConflictError(KippOptionsException):
    """Raised when a dotted key path conflicts with an existing non-option value."""

    pass


class BaseOptions:
    """Hierarchical key-value store supporting dotted key paths.

    Dotted keys like ``"a.b.c"`` are automatically expanded into nested
    BaseOptions instances, enabling tree-structured configuration.
    """

    def __init__(self, is_allow_overwrite_child_opt: bool = True) -> None:
        self._inner_settings: dict[str, Any] = {}
        self._is_allow_overwrite_child_opt = is_allow_overwrite_child_opt

    def create_option(self) -> BaseOptions:
        return BaseOptions()

    @property
    def is_allow_overwrite_child_opt(self) -> bool:
        return self._is_allow_overwrite_child_opt

    @is_allow_overwrite_child_opt.setter
    def is_allow_overwrite_child_opt(self, val: bool) -> None:
        assert isinstance(val, bool), "must be bool"
        self._is_allow_overwrite_child_opt = val

    def set_option(self, name: str, val: Any) -> None:
        """Set a configuration value by name.

        Dotted names (e.g. ``"db.host"``) automatically create intermediate
        BaseOptions nodes. When ``is_allow_overwrite_child_opt`` is False,
        existing child option nodes cannot be replaced by leaf values.
        """
        if "." not in name:
            self._inner_settings[name] = val
            return

        children = name.split(".")
        opt: BaseOptions = self
        for child in children[:-1]:
            if child not in opt:
                opt.set_option(child, self.create_option())
            elif not isinstance(opt[child], BaseOptions):
                if self._is_allow_overwrite_child_opt:
                    opt.set_option(child, self.create_option())  # overwrite
                else:
                    raise OptionKeyTypeConflictError(
                        "{} already exists but type is not BaseOption".format(child)
                    )

            opt = opt[child]

        last_key = children[-1]
        if (
            last_key in opt
            and isinstance(opt[last_key], BaseOptions)
            and not self._is_allow_overwrite_child_opt
        ):
            raise OptionKeyTypeConflictError("must not overwrite child option")

        opt.set_option(last_key, val)

    __setitem__ = set_option

    def del_option(self, name: str) -> None:
        """Delete a configuration value, restoring any lower-priority fallback."""
        if name in self._inner_settings:
            del self._inner_settings[name]

    __delitem__ = del_option

    def get_option(self, name: str) -> Any:
        """Retrieve a value by name, supporting dotted paths for nested lookup.

        Subclasses that override this must also reassign
        ``__getitem__ = __getattr__ = get_option`` to maintain
        consistent access semantics across ``opt.x``, ``opt['x']``,
        and ``opt.get_option('x')``.
        """
        if "." not in name:
            if name not in self._inner_settings:
                raise AttributeError
            else:
                return self._inner_settings[name]

        opt: BaseOptions | Any = self
        for child in name.split("."):
            if not isinstance(opt, BaseOptions) or child not in opt:
                raise AttributeError

            opt = opt[child]

        return opt

    __getitem__ = __getattr__ = get_option

    def __contains__(self, name: str) -> bool:
        """Override ``in`` operator"""
        try:
            self.get_option(name)
        except AttributeError:
            return False
        else:
            return True


class Options(BaseOptions, ArgparseMixin, SingletonMixin):
    """Configuration Manager

    Relate to `DATA-1026`_.

    You can write your own ``settings/settings_xxx.py`` to overwrite the Utilities settings.
    Please double check ``settings/__init__.py`` is exists.

    Load arguments in following sequences:

    #. load from your own attributes;
    #. load from command arguments (argparse);
    #. load from OS environment;
    #. load from env specified settings (``settings_xxx.py``);
    #. load from ``settings/settings_local.py``;
    #. load from project settings (``settings/settings.py``);
    #. load from ``Utilities.movoto.settings``;


    Usage:

        General usage::

            from kipp.options import options as opt

            # both ok
            opt.get_option('debug')
            opt.debug
            opt['debug']

            # will raise AttributeError if not exists

        Setup with argparse::

            from kipp.options import options as opt

            # get args from argparse
            parser = argparse.ArgumentParser()
            args = parser.parse_args()

            # set args
            opt.set_command_args(args)

            # if you want patch utilities at the same time
            opt.set_command_args(args, is_patch_utilies=True)

        Patch Utilities only::

            from kipp.options import options as opt

            # should patch before import Utilities
            opt.patch_utilities()

            from Utilities.movoto import settings

        Setup your own attribute::

            from kipp.options import options as opt

            # 321
            # assume init value is 321

            # you can set your own attr value to any object
            opt.set_option('abc', 123)
            # 123

            # then delete it to restore the default value
            opt.del_option('abc')
            # 321


    .. _DATA-1026:
        https://movoto.atlassian.net/browse/DATA-1026

    """

    def __init__(self, is_allow_overwrite_child_opt: bool = True) -> None:
        super(Options, self).__init__(
            is_allow_overwrite_child_opt=is_allow_overwrite_child_opt
        )
        self.setup_env_settings()

    def setup_env_settings(self) -> None:
        """Initialize all configuration sources.

        Loads settings modules at startup so the priority chain is ready
        before the first ``get_option`` call. Missing modules are silently
        skipped (common in dev environments without full settings layout).
        """
        self._command_args: Any = None
        self._environ: os._Environ[str] = copy.deepcopy(os.environ)
        self._env_settings: ModuleType | None = None
        self._private_settings: ModuleType | None = None

        # try:  # load Utilities settings
        #     movoto_settings = self.load_utilities_settings()
        # except KippOptionsException:
        #     self._movoto_settings = None
        #     get_logger().warning('can not found ``Utilities`` in PYTHONPATH')
        # else:
        #     get_logger().info('setup settings from Utilities')
        #     self._movoto_settings = movoto_settings

        try:  # load private settings
            from settings import settings_local as private_settings
        except ImportError:
            self._private_settings = None
        else:
            get_logger().info("setup settings from settings_local.py")
            self._private_settings = private_settings

        try:  # load project settings
            from settings import settings as project_settings
        except ImportError:
            self._project_settings: ModuleType | None = None
        else:
            get_logger().info("setup settings from settings.py")
            self._project_settings = project_settings

        self.load_specifical_settings()  # load env from environment

    def get_option(self, name: str) -> Any:
        """Look up a configuration value through the priority chain.

        The lookup order ensures that more specific/local sources always
        win over broader defaults. This allows CLI args to override env
        vars, which override file-based settings, etc.
        """
        try:
            val = super(Options, self).get_option(name)
        except AttributeError:
            pass
        else:
            get_logger().debug("load attr %s from inner settings", name)
            return val

        if hasattr(self._command_args, name):
            get_logger().debug("load attr %s from command args", name)
            return getattr(self._command_args, name)
        elif name in self._environ:
            get_logger().debug("load attr %s from environ", name)
            return self._environ[name]
        elif hasattr(self._env_settings, name):
            get_logger().debug("load attr %s from env settings", name)
            return getattr(self._env_settings, name)
        elif hasattr(self._private_settings, name):
            get_logger().debug("load attr %s from private settings", name)
            return getattr(self._private_settings, name)
        elif hasattr(self._project_settings, name):
            get_logger().debug("load attr %s from project settings", name)
            return getattr(self._project_settings, name)
        # elif hasattr(self._movoto_settings, name):
        #     get_logger().debug('load attr from %s movoto Utilities', name)
        #     return getattr(self._movoto_settings, name)

        raise AttributeError("attribute `{}` Not Found in kipp.options".format(name))

    __getitem__ = __getattr__ = get_option

    def load_specifical_settings(self, env: str | None = None) -> None:
        """Load environment-specific settings module (e.g. ``settings_staging``).

        Determined by the ``TARS_ENV`` environment variable unless
        explicitly overridden via the ``env`` parameter.
        """
        env = env or os.environ.get("TARS_ENV", None)
        if not env:
            return

        try:
            settings_fname = "settings.settings_{}".format(env)
            env_settings = importlib.import_module(settings_fname)
        except ImportError:
            raise KippOptionsException("Can not found env settings_{}".format(env))
        else:
            self._env_settings = env_settings
            get_logger().info("Setup specifical settings from settings_%s", env)

    def set_command_args(self, args: Any, is_patch_utilies: bool = True) -> None:
        """Register parsed argparse namespace as a configuration source."""
        self._command_args = args
        if hasattr(args, "env"):
            get_logger().warning(
                "You should better to use TARS_ENV environment to set run env"
            )
            self.load_specifical_settings(args.env)

        # no need for public use
        # if is_patch_utilies and not getattr(self, '_is_patched_utilities', None):
        #     self.patch_utilities()


opt = options = Options()
