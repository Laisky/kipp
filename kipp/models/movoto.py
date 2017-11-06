#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
----------------
Movoto Databases
----------------

"""

from __future__ import unicode_literals
from collections import namedtuple

from past.builtins import basestring

from kipp.libs.aio import run_until_complete, Future
from .base import BaseDB, as_coroutine
from .exceptions import DBValidateError, DuplicateIndexError, RecordNotFound


class RuntimeStats:
    """Create/Get/Update/Delete runtime status into movotodb

    Usage:
    ::
        from kipp.models import MovotoDB

        movotodb = MovotoDB()

        movotodb.create_runtime_stats(name, stats=None)
        movotodb.update_runtime_stats(name, stats)
        movotodb.delete_runtime_stats(name)
        movotodb.get_runtime_stats(name)
        is_runtime_stats_exists(name)

    Asynchronous Usage:
    ::
        from kipp.models import MovotoDB

        movotodb = MovotoDB(is_aio=True)

        yield movotodb.create_runtime_stats(name, stats=None)
        yield movotodb.update_runtime_stats(name, stats)
        yield movotodb.delete_runtime_stats(name)
        yield movotodb.get_runtime_stats(name)

    """
    _sql_to_create_runtime_stats = '''
        insert into runtime_stats (name, stats)
        values (%s, %s);
        '''
    _sql_to_update_runtime_stats = '''
        update runtime_stats
        set stats=%s
        where name=%s;
        '''
    _RuntimeStats = namedtuple('stats', ['created_at', 'updated_at', 'stats'])
    _sql_to_get_runtime_stats = '''
        select created_at, updated_at, stats
        from runtime_stats
        where name=%s;
        '''
    _sql_to_delete_runtime_stats = '''
        delete from runtime_stats
        where name=%s;
        '''

    def validate_stats(self, stats):
        try:
            assert stats, 'stats should not empty'
            assert isinstance(stats, basestring), 'stats should be ``str``'
            assert len(stats) <= 200, 'the length of stats should shorter than 200'
        except AssertionError as err:
            raise DBValidateError(*err.args)

    def validate_name(self, name):
        try:
            assert name, 'name should not empty'
            assert isinstance(name, basestring), 'name should be ``str``'
            assert len(name) <= 50, 'the length of name should shorter than 50'
        except AssertionError as err:
            raise DBValidateError(*err.args)

    @as_coroutine
    def create_runtime_stats(self, name, stats=None):
        """
        Args:
            name (str): new name
            stats (str, default=None): new stats

        Raises:
            DuplicateIndexError: if exists in db
            DBValidateError: if name/stats invalidate
        """
        self.validate_name(name)
        if stats:
            self.validate_stats(stats)

        try:
            r = self.conn.executeBySql(self._sql_to_create_runtime_stats, name, stats)
        except self.get_mysqldb_exception('IntegrityError') as err:
            if len(err.args) >= 2 and str(err.args[1]).startswith('Duplicate entry '):
                raise DuplicateIndexError('Duplicate name in ``runtime_stats`` for {}'.format(name))
            else:
                raise
        else:
            return r

    @as_coroutine
    def update_runtime_stats(self, name, stats, upsert=False):
        """
        Args:
            upsert (bool, default=False): create if not exists

        Raises:
            DBValidateError: if name/stats invalidate

        Returns:
            int: how many lines influenced
        """
        self.validate_name(name)
        self.validate_stats(stats)
        r = self.conn.executeBySql(self._sql_to_update_runtime_stats, stats, name)
        if not int(r):  # not exists
            if upsert:  # create new stats
                r = self.create_runtime_stats(name, stats)
                if isinstance(r, Future):
                    run_until_complete(r)
                    return r.result()

        return r

    @as_coroutine
    def get_runtime_stats(self, name, **kwargs):
        """Load runtime stats by name

        Args:
            name (str): name of the stats
            default (optional): do not raises RecordNotFound

        Raises:
            RecordNotFound: if not found and no default is specified
            DBValidateError: if name invalidate

        Returns:
            namedtuple: ('created_at', 'updated_at', 'stats')
        """
        self.validate_name(name)
        r = self.conn.getOneBySql(self._sql_to_get_runtime_stats, name)
        if not r:
            if 'default' in kwargs:
                return kwargs['default']
            else:
                raise RecordNotFound('Can not find stats via name {}'.format(name))

        return self._RuntimeStats(*r)

    @as_coroutine
    def delete_runtime_stats(self, name):
        """
        Raises:
            DBValidateError: if name invalidate
        """
        self.validate_name(name)
        return self.conn.executeBySql(self._sql_to_delete_runtime_stats, name)

    @as_coroutine
    def is_runtime_stats_exists(self, name):
        """Check whether name exists in runtime_stats

        Raises:
            DBValidateError: if name invalidate

        Returns:
            bool: is name exists
        """
        f = self.get_runtime_stats(name, default=None)
        if isinstance(f, Future):
            run_until_complete(f)
            return f.result() is not None

        return f is not None


class MovotoDB(BaseDB,
               RuntimeStats,
               object):

    __db_name__ = 'movoto'
