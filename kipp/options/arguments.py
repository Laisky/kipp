#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import argparse
from textwrap import dedent


class ArgparseMixin:
    """Argparse utils

    Usage
    ::
        from kipp.options import options as opt

        # set command argument
        opt.add_argument('--test', type=str)

        # parse argument
        opt.parse_args()

        # use argument
        print(opt.test)
    """

    def setup_argparse(self, name=''):
        """Setup argparse with name"""
        self._parser = argparse.ArgumentParser(name, formatter_class=argparse.RawTextHelpFormatter)

    def add_argument(self, *args, **kw):
        """Add command arguments"""
        if not hasattr(self, '_parser'):
            self.setup_argparse()

        if '\n' in kw.get('help', ''):
            kw['help'] = dedent(kw['help'])

        self._parser.add_argument(*args, **kw)

    def parse_args(self, *args, **kw):
        """Parse command arguments"""
        is_patch_utilies = kw.pop('is_patch_utilies', True)
        args = self._parser.parse_args(*args, **kw)
        self.set_command_args(args, is_patch_utilies=is_patch_utilies)
        return args
