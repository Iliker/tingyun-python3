# -*- coding: utf-8 -*-

"""
"""

import traceback
import logging

from tingyun.armoury.ammunition.timer import Timer
from tingyun.armoury.ammunition.tracker import current_tracker
from tingyun.logistics.warehouse.database_node import DatabaseNode

console = logging.getLogger(__name__)


class DatabaseTracker(Timer):
    """
    """
    def __init__(self, tracker, sql, dbtype='', dbapi=None, connect_params=None, cursor_params=None,
                 execute_params=None, host="Unknown", port="Unknown", db_name="Unknown"):
        """
        :param tracker:
        :param sql:
        :param dbapi:
        :param connect_params:
        :param cursor_params:
        :param execute_params:
        :return:
        """
        super(DatabaseTracker, self).__init__(tracker)

        self.dbapi = dbapi
        self.connect_params = connect_params
        self.cursor_params = cursor_params
        self.execute_params = execute_params
        self.sql = sql
        self.db_type = dbtype
        self.host = host
        self.port = port
        self.db_name = db_name

        self.stack_trace = None
        self.sql_format = None

    def finalize_data(self):
        """create all the data if need
        :return:
        """
        connect_params = None
        cursor_params = None
        execute_params = None
        settings = self.tracker.settings

        if settings.action_tracer.enabled and self.duration >= settings.action_tracer.stack_trace_threshold:
            if self.tracker.stack_trace_count < settings.stack_trace_count:
                self.stack_trace = traceback.extract_stack()
                self.tracker.stack_trace_count += 1

        explain_enabled = settings.action_tracer.explain_enabled
        explain_threshold = settings.action_tracer.explain_threshold
        if settings.action_tracer.enabled and explain_enabled and self.duration > explain_threshold:
            if self.tracker.explain_plan_count < settings.explain_plan_count:
                connect_params = self.connect_params
                cursor_params = self.cursor_params
                execute_params = self.execute_params

        self.sql_format = settings.action_tracer.record_sql
        self.connect_params = connect_params
        self.cursor_params = cursor_params
        self.execute_params = execute_params

    def create_node(self):
        tracker = current_tracker()
        if tracker:
            tracker.db_time = self.duration

        return DatabaseNode(dbapi=self.dbapi, sql=self.sql, children=self.children, start_time=self.start_time,
                            end_time=self.end_time, duration=self.duration, exclusive=self.exclusive,
                            dbtype=self.db_type, stack_trace=self.stack_trace, sql_format=self.sql_format,
                            connect_params=self.connect_params, cursor_params=self.cursor_params,
                            execute_params=self.execute_params,  host=self.host, port=self.port, db_name=self.db_name)

    def terminal_node(self):
        return True
