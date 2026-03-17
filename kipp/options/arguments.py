#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
from textwrap import dedent
from typing import Any


class ArgparseMixin:
    """Mixin that adds argparse integration to the Options class.

    Allows registering CLI arguments incrementally and parsing them
    into the options lookup chain. The parser is lazily initialized
    on first ``add_argument`` call.

    Usage::

        from kipp.options import options as opt

        # set command argument
        opt.add_argument('--test', type=str)

        # parse argument
        opt.parse_args()

        # use argument
        print(opt.test)
    """

    def setup_argparse(self, name: str = "") -> None:
        """Initialize the argument parser with RawTextHelpFormatter
        to preserve manual formatting in help strings.
        """
        self._parser = argparse.ArgumentParser(
            name, formatter_class=argparse.RawTextHelpFormatter
        )

    def add_argument(self, *args: Any, **kw: Any) -> None:
        """Add a CLI argument, auto-initializing the parser if needed.

        Multiline help strings are auto-dedented so callers can use
        indented triple-quoted strings without breaking formatting.
        """
        if not hasattr(self, "_parser"):
            self.setup_argparse()

        if "\n" in kw.get("help", ""):
            kw["help"] = dedent(kw["help"])

        self._parser.add_argument(*args, **kw)

    def parse_args(self, *args: Any, **kw: Any) -> argparse.Namespace:
        """Parse CLI arguments and register them as a configuration source.

        Delegates to ``set_command_args`` (provided by the Options class)
        to wire the parsed namespace into the configuration priority chain.
        """
        is_patch_utilies: bool = kw.pop("is_patch_utilies", True)
        args = self._parser.parse_args(*args, **kw)
        self.set_command_args(args, is_patch_utilies=is_patch_utilies)
        return args
