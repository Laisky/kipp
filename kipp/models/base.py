#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

from concurrent.futures import Future
from functools import wraps
from types import ModuleType
from typing import Any, Callable, TypeVar

from kipp.aio import aio_internal_thread_executor

F = TypeVar("F", bound=Callable[..., Any])


def as_coroutine(func: F) -> F:
    """Decorator that optionally wraps a method call in a thread pool executor.

    When the instance has an ``_executor`` (i.e. async mode is enabled),
    the decorated method is submitted to the executor and a Future is
    returned instead of the direct result.  This allows the same method
    implementation to serve both sync and async callers.
    """

    @wraps(func)
    def wrapper(*args: Any, **kw: Any) -> Any:
        _self = args[0]
        if getattr(_self, "_executor", None):  # wrap func to future
            return _self._executor.submit(func, *args, **kw)
        else:
            return func(*args, **kw)

    # The cast preserves the original signature for callers, even though the
    # runtime wrapper has a generic ``(*args, **kw)`` signature.
    return wrapper  # type: ignore[return-value]


class MySQLdbExceptionHandler:
    """Lazy-loads the MySQLdb module so that import-time failures are avoided.

    This is useful because MySQLdb (a C-extension) may not be installed in
    every environment (e.g. during testing or in workers that do not need DB
    access).
    """

    __mysqldb_module: ModuleType | None = None

    def get_mysqldb_exception(self, name: str) -> type[Exception]:
        if not self.__mysqldb_module:
            self.import_mysqldb()

        return getattr(self.__mysqldb_module, name)  # type: ignore[arg-type]

    def import_mysqldb(self) -> None:
        import MySQLdb

        self.__mysqldb_module = MySQLdb


class BaseDB(MySQLdbExceptionHandler):
    """Thin wrapper around the Utilities SqlHelper providing lazy connection
    and optional async execution via a thread pool.

    Subclasses must define ``__db_name__`` as a class attribute to identify
    the target database.
    """

    # Subclasses override this to select the database.
    __db_name__: str

    def __init__(self, is_aio: bool = False, executor: Any = None) -> None:
        self._db_conn: Any = None
        self._is_aio: bool = is_aio
        if is_aio:
            self._executor = executor or aio_internal_thread_executor
        else:
            self._executor = None

    def get_connection(self) -> Any:
        """Return the existing connection or lazily create one."""
        if self._db_conn:
            return self._db_conn

        self.connect_utilities_sqlhelper()
        return self._db_conn

    @property
    def conn(self) -> Any:
        return self.get_connection()

    def connect_utilities_sqlhelper(self) -> None:
        from Utilities.movoto.SqlHelper import SqlHelper

        self._db_conn = SqlHelper(self.__db_name__, use_connection_pool=True)

    def __getattr__(self, name: str) -> Any:
        # Delegate attribute access to the underlying connection so callers
        # can use DB helper methods directly on the model instance.
        return getattr(self.conn, name)

    def __exit__(self) -> None:
        self._db_conn.close()
