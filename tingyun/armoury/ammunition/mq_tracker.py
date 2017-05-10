# -*- coding: utf-8 -*-

import logging
from tingyun.armoury.ammunition.timer import Timer
from tingyun.logistics.warehouse.mq_node import MQNode
from tingyun.armoury.ammunition.tracker import current_tracker
from tingyun.logistics.basic_wrapper import wrap_object, FunctionWrapper

console = logging.getLogger(__name__)


class MQTrace(Timer):
    """
    """
    def __init__(self, tracker, vendor, name_type, host, port, byte, name, headers, role, wrapped_info, external_id):
        """
        :param tracker:
        :param vendor: RabbitMQ/AciveMQ
        :param name_type: Exchange/Queue/Topic
        :param host:
        :param port:
        :param byte:
        :param name:Exchange/routing_key
        :param role: Produce/Consume
        """
        super(MQTrace, self).__init__(tracker)
        self.vendor = vendor or "Unknown"
        self.name_type = name_type or "Unknown"
        self.host = host or "Unknown"
        self.port = port or 0
        self.byte = byte or 0
        self.name = name
        self.headers = headers or {}
        self.role = role
        self.wrapped_info = wrapped_info
        self.external_id = external_id

        # 防止mq驱动自动生成的queue name
        if str(name).startswith('amq.'):
            self.name = 'Temp'
        elif '.' in name:
            self.name_type = 'Topic'

    def create_node(self):
        """
        :return:
        """
        return MQNode(vendor=self.vendor, name_type=self.name_type, host=self.host, port=self.port, byte=self.byte,
                      name=self.name, headers=self.headers, role=self.role, wrapped_info=self.wrapped_info,
                      duration=self.duration, exclusive=self.exclusive, external_id=self.external_id,
                      start_time=self.start_time, end_time=self.end_time, children=self.children)

    def terminal_node(self):
        return False
