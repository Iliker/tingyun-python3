# -*- coding: utf-8 -*-

"""支持RabbitMQ数据采集
"""

import sys
import logging

from tingyun.armoury.mq.utils import retrieve_tracker, mq_common_callback_wrapper

from tingyun.armoury.ammunition.mq_tracker import MQTrace
from tingyun.armoury.ammunition.tracker import current_tracker
from tingyun.armoury.ammunition.external_tracker import process_cross_trace
from tingyun.armoury.ammunition.function_tracker import wrap_function_trace, FunctionTracker
from tingyun.logistics.object_name import callable_name
from tingyun.logistics.basic_wrapper import wrap_object, FunctionWrapper, wrap_function_wrapper

console = logging.getLogger(__name__)


def mq_produce_trace_wrapper(wrapped):
    def dynamic_wrapper(wrapped, instance, args, kwargs):
        tracker = current_tracker()
        vendor = 'RabbitMQ'
        name_type = 'Exchange'
        publish_headers = {}
        role = 'Produce'

        if not tracker:
            return wrapped(*args, **kwargs)

        def parse_server(instance, exchange, routing_key, body, properties=None, *_args, **_kwargs):
            """ 获取publish的一些必要信息，优先获取exchange作为metric名字
            :return:
            """
            global publish_headers
            host, port, byte, name = "Unknown", 0, 0, "Unknown"

            try:
                # blocking  和 其他异步生产者，
                connection = getattr(instance, 'connection', None) or getattr(instance, '_connection', None)
                impl = getattr(connection, '_impl', None) or connection
                host = impl.params.host
                port = impl.params.port

                publish_headers = getattr(properties, "headers", {}) or {}
                ty_headers, _external_id = process_cross_trace(None, msg_type='TingyunID')
                if ty_headers:
                    from pika.spec import BasicProperties

                    if not properties:
                        properties = BasicProperties(headers=ty_headers)
                    else:
                        if not getattr(properties, "headers", None):
                            setattr(properties, "headers", ty_headers)
                        elif isinstance(properties.headers, dict):
                            properties.headers.update(ty_headers)

            except Exception as err:
                console.info("Parse RabbitMQ host & port with error %s", err)
                _external_id = None

            _server = (host, port, sys.getsizeof(body), exchange or routing_key, _external_id)
            return _server, exchange, routing_key, body, properties, _args, _kwargs

        server, exchange, routing_key, body, properties, _args, _kwargs = parse_server(instance, *args, **kwargs)
        host, port, byte, name, external_id = server
        name_type = 'Queue' if not exchange else name_type

        with MQTrace(tracker, vendor, name_type, host, port, byte, name, publish_headers, role,
                     ('BlockingChannel', 'publish'), external_id):
            with FunctionTracker(tracker, callable_name(wrapped)):
                return wrapped(exchange, routing_key, body, properties, *_args, **_kwargs)

    return FunctionWrapper(wrapped, dynamic_wrapper)


def callback_wrapper(wrapped, instance, args, kwargs):
    """
    :return:
    """
    def parse_callback_params(_channel, _method, _properties, _body, *_args, **_kwarg):
        """细节参考pika官方文档http://pika.readthedocs.io/en/0.10.0/examples/blocking_consumer_generator.html
        :return:
        """
        return _channel, _method, _properties, _body, _args, _kwarg

    def parse_server_info(ch):
        """
        :return:
        """
        try:
            connection = getattr(ch, 'connection', None) or getattr(ch, '_connection', None)
            impl = getattr(connection, '_impl', None) or connection
            _host = impl.params.host
            _port = impl.params.port
        except Exception as err:
            _host, _port = "Unknown", 0
            console.debug("Parsing host & port failed when trace consume callback. %s, %s", wrapped, err)

        return _host, _port

    _ch, method, properties, body, _args, _kwarg = parse_callback_params(*args, **kwargs)
    tracker, is_web = retrieve_tracker(getattr(properties, "headers", {}))
    if not tracker:
        return wrapped(*args, **kwargs)

    vendor = 'RabbitMQ'
    name_type = 'Exchange' if method.exchange else "Queue"
    role = 'Consume'

    receive_headers = dict()
    receive_headers["message"] = {}
    receive_headers["message"]["message.byte"] = sys.getsizeof(body)
    receive_headers["message"]["message.queue"] = ''
    receive_headers["message"]["message.exchange"] = method.exchange
    receive_headers["message"]["message.routingkey"] = method.routing_key

    request_params = getattr(properties, "headers", {})
    receive_headers.update(request_params or {})
    host, port = parse_server_info(_ch)

    exceptions = None
    with MQTrace(tracker, vendor, name_type, host, port, sys.getsizeof(body), method.exchange or method.routing_key,
                 receive_headers, role, ('', wrapped.__name__), None):
        with FunctionTracker(tracker, callable_name(wrapped)):
            try:
                result = wrapped(*args, **kwargs)
                tracker.deal_response("200 ok", {})
            except Exception as err:  # Catch all
                tracker.record_exception(*sys.exc_info())
                tracker.deal_response("500 error", {})
                exceptions = err

    # 不在web应用内
    if not is_web:
        tracker._parse_request_params(receive_headers)
        tracker.set_tracker_name("%s%%2F%s" % (name_type, method.exchange or method.routing_key), priority=2)
        tracker.finish_work(*sys.exc_info())
    if exceptions:
        raise exceptions

    return result


def mq_consume_wrapper(wrapped, instance, args, kwargs):
    """
    :return:
    """
    def parse_callback(cb, *_args, **_kwargs):
        """
        :return:
        """
        return cb, _args, _kwargs

    if 'consumer_callback' in kwargs:
        callback_class_name = getattr(getattr(kwargs['consumer_callback'], 'im_class', None), '__name__', None)
        if getattr(kwargs['consumer_callback'], '_self_is_wrapped', None) or callback_class_name == 'BlockingChannel':
            console.debug("Consumer was wrapped before.")
            return wrapped(*args, **kwargs)

        kwargs['consumer_callback'] = FunctionWrapper(kwargs['consumer_callback'], callback_wrapper)
        return wrapped(*args, **kwargs)
    else:
        cb, _args, _kwargs = parse_callback(*args, **kwargs)
        callback_class_name = getattr(getattr(cb, 'im_class', None), '__name__', None)
        if getattr(cb, '_self_is_wrapped', None) or callback_class_name == 'BlockingChannel':
            console.debug("Consumer was wrapped before.")
            return wrapped(cb, *_args, **_kwargs)

        wrapped_cb = FunctionWrapper(cb, callback_wrapper)
        wrapped_cb._self_is_wrapped = True

        return wrapped(wrapped_cb, *_args, **_kwargs)


def detect_block_channel(module):
    """
    :return:
    """
    # wrap_object(module, "BlockingChannel.publish", mq_produce_trace_wrapper)
    wrap_function_wrapper(module.BlockingChannel, "basic_consume", mq_consume_wrapper)


def detect_channel(module):
    """
    :return:
    """
    # 基于selection connection libevent connect tornado connection 的生产者目前使用场景大部分为非web过程内
    # 需要单独处理才能支持，咱不考虑
    wrap_object(module, "Channel.basic_publish", mq_produce_trace_wrapper)
    wrap_function_wrapper(module.Channel, "basic_consume", mq_consume_wrapper)

    # 下面的方法都是采用即时读写的方式跟mq通信，故可以直接采集之性能
    wrap_function_trace(module.Channel, "basic_get", name='basic_get')
    wrap_function_trace(module.Channel, "basic_nack", name='basic_nack')
    wrap_function_trace(module.Channel, "exchange_bind", name='exchange_bind')
    wrap_function_trace(module.Channel, "exchange_declare", name='exchange_declare')
    wrap_function_trace(module.Channel, "exchange_delete", name='exchange_delete')
    wrap_function_trace(module.Channel, "queue_bind", name='queue_bind')
    wrap_function_trace(module.Channel, "queue_declare", name='queue_declare')
    wrap_function_trace(module.Channel, "queue_delete", name='queue_delete')

    # 其他常规用户可能执行的回调
    # 为了减少性能开销，不捕获基于CallbackManager.add所有的回调函数
    wrap_function_wrapper(module, "Channel.add_on_cancel_callback", mq_common_callback_wrapper)
    wrap_function_wrapper(module, "Channel.add_on_close_callback", mq_common_callback_wrapper)
    wrap_function_wrapper(module, "Channel.add_on_return_callback", mq_common_callback_wrapper)


def detect_connection(module):
    """"""
    # 其他常规用户可能执行的回调
    # blockingconnection中的add_on_connection_blocked_callback&
    # add_on_connection_unblocked_callback都是调用connection中同样的方法
    # 为了减少性能开销，不捕获基于CallbackManager.add所有的回调函数
    wrap_function_wrapper(module, "Connection.add_on_close_callback", mq_common_callback_wrapper)
    wrap_function_wrapper(module, "Connection.add_on_connection_blocked_callback", mq_common_callback_wrapper)
    wrap_function_wrapper(module, "Connection.add_on_connection_unblocked_callback", mq_common_callback_wrapper)
    wrap_function_wrapper(module, "Connection.add_on_open_callback", mq_common_callback_wrapper)
    wrap_function_wrapper(module, "Connection.add_on_open_error_callback", mq_common_callback_wrapper)
