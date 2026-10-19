#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations, unicode_literals, absolute_import

from functools import wraps
from sys import version_info
from typing import Any, Callable, TypeVar, cast

from .exceptions import KippException, KippAIOException


PY2: bool = version_info[0] == 2
PY3: bool = version_info[0] == 3

T = TypeVar("T")


def singleton(cls: Callable[..., T], *args: Any, **kw: Any) -> Callable[[], T]:
    """Decorator that restricts a class to a single instance (lazy-initialized).

    The instance is created on first call with the *args and **kw captured at
    decoration time -- not at call time.  This means the decorated callable
    accepts no arguments; pass construction parameters to the decorator itself.

    Uses a dict keyed by class rather than a simple variable so the closure
    can mutate state without `nonlocal`.
    """
    instances: dict[Callable[..., T], T] = {}

    @wraps(cls)
    def _singleton() -> T:
        if cls not in instances:
            instances[cls] = cls(*args, **kw)
        return instances[cls]

    return _singleton


class SingletonMixin:
    """Mixin that turns any class into a singleton via __new__.

    Unlike the `singleton` decorator, this approach lets subclasses inherit
    singleton behaviour and works naturally with isinstance/issubclass checks.
    Each concrete subclass gets its own independent _instance -- the attribute
    is set on `cls`, not on SingletonMixin itself.
    """

    _instance: SingletonMixin | None

    def __new__(cls, *_args: Any, **_kw: Any) -> SingletonMixin:
        if "_instance" not in cls.__dict__:
            cls._instance = super(SingletonMixin, cls).__new__(cls)
        instance = cls._instance
        assert instance is not None
        return cast(SingletonMixin, instance)
