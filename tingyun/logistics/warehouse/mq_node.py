# -*- coding: utf-8 -*-

import logging
from collections import namedtuple
from tingyun.logistics.attribution import TimeMetric, node_start_time, node_end_time


console = logging.getLogger(__name__)
_MQNode = namedtuple('_MQNode', ['vendor', 'name_type', 'host', 'port', 'byte', 'name', 'headers', 'children', 'role',
                                 'wrapped_info', 'start_time', 'end_time', 'duration', 'exclusive', 'external_id'])


class MQNode(_MQNode):
    """
    """
    def time_metrics(self, root, parent):
        """
        :param root:
        :param parent:
        :return:
        """
        name = 'Message %s/%s:%s%%2F%s%%2F%s/%s' % (self.vendor, self.host, self.port, self.name_type, self.name,
                                                    self.role)
        yield TimeMetric(name=name, scope=root.path, duration=self.duration, exclusive=self.exclusive)

        name = 'GENERAL/Message %s/%s:%s%%2F%s%%2F%s/%s%%2FByte' % (self.vendor, self.host, self.port, self.name_type,
                                                                    self.name, self.role)
        yield TimeMetric(name=name, scope=root.path, duration=self.byte, exclusive=self.exclusive)

        name = "GENERAL/Message %s/%s:%s/%s" % (self.vendor, self.host, self.port, self.role)
        yield TimeMetric(name=name, scope=root.path, duration=self.duration, exclusive=self.exclusive)

        # 消费者采集他的等待时长
        if self.role == 'Consume':
            name = 'GENERAL/Message %s/%s:%s%%2F%s%%2F%s/%s%%2FWait' % (self.vendor, self.host, self.port,
                                                                        self.name_type, self.name, self.role)
            yield TimeMetric(name=name, scope=root.path, duration=root.trace_interval, exclusive=self.exclusive)

        name = 'GENERAL/Message %s/NULL/All' % self.vendor
        yield TimeMetric(name=name, scope=root.path, duration=self.duration, exclusive=self.exclusive)

        if root.type == 'WebAction':
            name = "GENERAL/Message %s/NULL/AllWeb" % self.vendor
            yield TimeMetric(name=name, scope=root.path, duration=self.duration, exclusive=self.exclusive)
        else:
            name = "GENERAL/Message %s/NULL/AllBackgound" % self.vendor
            yield TimeMetric(name=name, scope=root.path, duration=self.duration, exclusive=self.exclusive)

        for child in self.children:
            for metric in child.time_metrics(root, self):
                yield metric

    def trace_node(self, root):
        """作为调用方时，txData无法回传，此时需要将externalId往服务端传递
        :param root:
        :return:
        """
        start_time = node_start_time(root, self)
        end_time = node_end_time(root, self)
        params = {}
        children = []

        # 当作为调用者时，该数据才会从上报，否则该id会跟着跨应用数据上报服务器
        if self.external_id:
            params['externalId'] = self.external_id

        if root.trace_id:
            params['txId'] = root.trace_id

        root.trace_node_count += 1
        for child in self.children:
            if root.trace_node_count > root.trace_node_limit:
                break

            children.append(child.trace_node(root))

        # 由于MQ产生的跨应用数据无法回传，txdata需要在被调方处理跨应用数据
        name = 'Message %s/%s:%s%%2F%s%%2F%s/%s' % (self.vendor, self.host, self.port, self.name_type, self.name,
                                                    self.role)

        return [start_time, end_time, name, '', 1, self.wrapped_info[0], self.wrapped_info[1], params, children]

