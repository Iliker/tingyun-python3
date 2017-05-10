# -*- coding: utf-8 -*-

"""
"""

from collections import namedtuple
from tingyun.logistics.attribution import TimeMetric, node_start_time, node_end_time

_ExternalNode = namedtuple('_ExternalNode', ['library', 'url', 'children', 'start_time', 'end_time', 'protocol',
                                             'duration', 'exclusive', 'external_id'])


class ExternalNode(_ExternalNode):
    """

    """

    def time_metrics(self, root, parent):
        """
        :param root: the top node of the tracker
        :param parent: parent node.
        :return:
        """

        def extend_metric(metric_name):
            """若产生跨应用追踪，general/component里面需要有跨应用追踪数据
            :param metric_name:
            :return:
            """
            if not root.trace_data:
                return metric_name

            return "%s|%s|%s" % (metric_name, root.trace_data.get('id'), root.trace_data.get('action'))

        name = 'GENERAL/External/NULL/All'
        yield TimeMetric(name=name, scope=root.path, duration=self.duration, exclusive=self.exclusive)

        name = "GENERAL/External/NULL/AllWeb"
        yield TimeMetric(name=name, scope=root.path, duration=self.duration, exclusive=self.exclusive)

        name = 'External/%s/%s' % (self.url.replace("/", "%2F"), self.library)
        yield TimeMetric(name=extend_metric(name), scope=root.path, duration=self.duration, exclusive=self.exclusive)

        if root.trace_data:
            # for cross trace.
            trace_data = root.trace_data
            name = 'GENERAL/ExternalTransaction/NULL/%s' % trace_data.get("id")
            yield TimeMetric(name=extend_metric(name), scope=root.path, duration=self.duration,
                             exclusive=self.exclusive)

            name = 'GENERAL/ExternalTransaction/%s/%s' % (self.protocol, trace_data.get("id"))
            yield TimeMetric(name=extend_metric(name), scope=root.path, duration=self.duration,
                             exclusive=self.exclusive)

            name = 'GENERAL/ExternalTransaction/%s:sync/%s' % (self.protocol, trace_data.get("id"))
            yield TimeMetric(name=extend_metric(name), scope=root.path, duration=self.duration,
                             exclusive=self.exclusive)

        name = 'GENERAL/External/%s/%s' % (self.url.replace("/", "%2F"), self.library)
        yield TimeMetric(name=extend_metric(name), scope=root.path, duration=self.duration, exclusive=self.exclusive)

    def trace_node(self, root):
        """
        :param root: the root node of the tracker
        :return:
        """
        params = {}
        children = []
        call_count = 1
        class_name = ""
        method_name = self.library
        call_url = self.url
        root.trace_node_count += 1
        start_time = node_start_time(root, self)
        end_time = node_end_time(root, self)
        metric_name = 'External/%s/%s' % (self.url.replace("/", "%2F"), self.library)

        # 当作为调用者时，该数据才会从上报，否则该id会跟着跨应用数据上报服务器
        if self.external_id:
            params['externalId'] = self.external_id

        if root.trace_id and root.trace_data:
            params['txId'] = root.trace_id
            params['txData'] = root.trace_data

        return [start_time, end_time, metric_name, call_url, call_count, class_name, method_name, params, children]
