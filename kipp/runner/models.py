#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from kipp.utils import utcnow, get_logger


RUNSTATSMONITOR_COLLECTION_NAME = 'run_stats_monitor'


class RunStats:
    running = 'running'
    failed = 'failed'
    successed = 'successed'


class RunStatsMonitor(object):
    def __init__(self, command, args=None):
        self.connect()
        self._command = command
        self._args = args

    def connect(self):
        from Utilities.movoto.mongodbHelper import MongodbHelper

        self.mongo = MongodbHelper().connect()
        self.db = self.mongo.db
        self.collection = self.db[RUNSTATSMONITOR_COLLECTION_NAME]

    def start(self):
        d = {'command': self._command, 'updated_at': utcnow(), 'created_at': utcnow(), 'status': RunStats.running}
        if self._args:
            d.update({'arguments': self._args})

        r = self.mongo.create_documents(
            RUNSTATSMONITOR_COLLECTION_NAME,
            [d])
        self.task_id = r[0]
        return self.task_id

    def success(self):
        self.mongo.update_fields(
            RUNSTATSMONITOR_COLLECTION_NAME,
            {'_id': self.task_id},
            {'updated_at': utcnow(), 'status': RunStats.successed})

    def clean_logs_by_timedelta(self, timedelta):
        get_logger().info('clean_logs_by_timedelta for timedelta %s', timedelta)
        self.collection.remove(
            {'updated_at': {'$lt': utcnow() + timedelta}})

    def fail(self, err_msg):
        self.mongo.update_fields(
            RUNSTATSMONITOR_COLLECTION_NAME,
            {'_id': self.task_id},
            {'updated_at': utcnow(), 'status': RunStats.failed, 'err_msg': err_msg})

    def __del__(self):
        self.mongo.close()
