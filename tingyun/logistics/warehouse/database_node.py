# -*- coding: utf-8 -*-

"""
"""

import logging
from collections import namedtuple
from tingyun.logistics.warehouse.dbapi_tools import sql_parser
from tingyun.logistics.attribution import node_start_time, node_end_time, TimeMetric
from tingyun.config.settings import global_settings

_SlowSqlNode = namedtuple('_SlowSqlNode', ['duration', 'path', 'request_uri', 'sql', 'sql_format', 'metric', 'dbapi',
                                           'stack_trace', 'connect_params', 'cursor_params', 'execute_params',
                                           "start_time"])
_DatabaseNode = namedtuple('_DatabaseNode', ['dbapi', 'sql', 'children', 'start_time', 'end_time', 'duration',
                                             'exclusive', 'stack_trace', 'sql_format', 'connect_params',
                                             'cursor_params', 'execute_params', "dbtype", 'host', 'port', 'db_name'])
console = logging.getLogger(__name__)


class SlowSqlNode(_SlowSqlNode):
    """
    """

    def __new__(cls, *args, **kwargs):
        node = _SlowSqlNode.__new__(cls, *args, **kwargs)
        node.parser = sql_parser(node.sql, node.dbapi)
        return node

    @property
    def operation(self):
        return self.parser.operation

    @property
    def formatted(self):
        return self.parser.formatted(self.sql_format)

    @property
    def identifier(self):
        return self.parser.identifier

    @property
    def explain_plan(self):
        return self.parser.explain_plan(self.connect_params, self.cursor_params, self.execute_params)


class DatabaseNode(_DatabaseNode):
    def __new__(cls, *args, **kwargs):
        node = _DatabaseNode.__new__(cls, *args, **kwargs)
        node.parser = sql_parser(node.sql, node.dbapi)

        return node

    @property
    def operation(self):
        return self.parser.operation

    @property
    def table(self):
        return self.parser.table

    @property
    def formatted(self):
        return self.parser.formatted(self.sql_format)

    @property
    def explain_plan(self):
        return self.parser.explain_plan(self.connect_params, self.cursor_params, self.execute_params)

    def time_metrics(self, root, parent):
        """GENERAL 用于统计GENERAL中的一些组件的性能数据(通用汇总数据)
            非GENERAL将组成component数据
        :param root:
        :param parent:
        :return:
        """
        dbtype = r' %s' % self.dbtype
        host, port, db_name = self.host, self.port, self.db_name

        name = "GENERAL/Database%s/%s:%s%%2F%s/All" % (dbtype, host, port, db_name)
        yield TimeMetric(name=name, scope=root.path, duration=self.duration, exclusive=self.exclusive)

        name = 'GENERAL/Database%s/NULL/All' % dbtype
        yield TimeMetric(name=name, scope=root.path, duration=self.duration, exclusive=self.exclusive)

        if root.type == 'WebAction':
            name = "GENERAL/Database%s/NULL/AllWeb" % dbtype
            yield TimeMetric(name=name, scope=root.path, duration=self.duration, exclusive=self.exclusive)
        else:
            name = "GENERAL/Database%s/NULL/AllBackgound" % dbtype
            yield TimeMetric(name=name, scope=root.path, duration=self.duration, exclusive=self.exclusive)

        operation = str(self.operation).upper() or "CALL"

        if self.table:
            name = "GENERAL/Database%s/%s:%s%%2F%s%%2F%s/%s" % (dbtype, host, port, db_name, self.table, operation)
            yield TimeMetric(name=name, scope=root.path, duration=self.duration, exclusive=self.exclusive)

            name = "Database%s/%s:%s%%2F%s%%2F%s/%s" % (dbtype, host, port, db_name, self.table, operation)
            yield TimeMetric(name=name, scope=root.path, duration=self.duration, exclusive=self.exclusive)
        else:
            name = "GENERAL/Database%s/%s:%s%%2F%s%%2FUnknown/%s" % (dbtype, host, port, db_name, operation)
            yield TimeMetric(name=name, scope=root.path, duration=self.duration, exclusive=self.exclusive)

            name = "Database%s/%s:%s%%2F%s%%2FUnknown/%s" % (dbtype, host, port, db_name, operation)
            yield TimeMetric(name=name, scope=root.path, duration=self.duration, exclusive=self.exclusive)

        name = "GENERAL/Database%s/NULL/%s" % (dbtype, operation or "CALL")
        yield TimeMetric(name=name, scope=root.path, duration=self.duration, exclusive=self.exclusive)

    def trace_node(self, root):
        """
        :param root: the root node of the tracker
        :return:
        """
        dbtype = r" %s" % self.dbtype
        params = {"sql": "", "explainPlan": {}, "stacktrace": []}
        children = []
        call_count = 1
        class_name = ""
        root.trace_node_count += 1
        start_time = node_start_time(root, self)
        end_time = node_end_time(root, self)
        operation = str(self.operation).upper() or 'CALL'
        method_name = '%s.%s' % (self.dbtype, operation)
        metric_name = "Database%s/%s:%s%%2F%s%%2FUnknown/%s" % (dbtype, self.host, self.port, self.db_name, operation)
        call_url = ""
        host, port, db_name = self.host, self.port, self.db_name

        if self.table:
            metric_name = "Database %s/%s:%s%%2F%s%%2F%s/%s" % (dbtype, host, port, db_name, self.table, operation)
        else:
            console.debug("Can not get table for operate `%s` to `%s`", operation, dbtype)

        if self.formatted:
            # Note, use local setting only.
            _settings = global_settings()
            params['sql'] = self.formatted

            if _settings.action_tracer.log_sql:
                console.info("Log sql is opened. sql upload is disabled, sql sentence is %s", self.formatted)
                params['sql'] = ""

            if self.explain_plan:
                params['explainPlan'] = self.explain_plan

            if self.stack_trace:
                for line in self.stack_trace:
                    line = [line.filename, line.lineno, line.name, line.locals]
                    if len(line) >= 4 and 'tingyun' not in line[0]:
                        params['stacktrace'].append("%s(%s:%s)" % (line[2], line[0], line[1]))

        return [start_time, end_time, metric_name, call_url, call_count, class_name, method_name, params, children]

    def slow_sql_node(self, root):
        """
        :return:
        """
        dbtype = r" %s" % self.dbtype
        request_uri = root.request_uri.replace("%2F", "/")
        operation = str(self.operation).upper() or 'CALL'
        host, port, db_name = self.host, self.port, self.db_name
        metric_name = "Database%s/%s:%s%%2F%s%%2FUnknown/%s" % (dbtype, host, port, db_name, operation)

        if self.table:
            metric_name = "Database %s/%s:%s%%2F%s%%2F%s/%s" % (dbtype, host, port, db_name, self.table, operation)
        else:
            console.debug("Can not get table for operate `%s` to `%s`", operation, dbtype)

        return SlowSqlNode(duration=self.duration, path=root.path, request_uri=request_uri, metric=metric_name,
                           start_time=int(self.start_time), sql=self.sql, sql_format=self.sql_format, dbapi=self.dbapi,
                           stack_trace=self.stack_trace, connect_params=self.connect_params,
                           cursor_params=self.cursor_params, execute_params=self.execute_params)
