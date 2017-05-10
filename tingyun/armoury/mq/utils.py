# -*- coding: utf-8 -*-

import logging
from tingyun.battlefield.tracer import Tracer
from tingyun.battlefield.proxy import proxy_instance
from tingyun.config.settings import global_settings
from tingyun.logistics.object_name import callable_name
from tingyun.logistics.basic_wrapper import FunctionWrapper
from tingyun.armoury.ammunition.tracker import current_tracker
from tingyun.armoury.ammunition.function_tracker import FunctionTracker

console = logging.getLogger(__name__)


def retrieve_tracker(headers, vendor='RabbitMQ'):
    """消费者调用这个接口，获取tracker，如果没有就自动生成一个并强制转换WebAction
    :return: tracker is_web
    """
    # 如果未webAction则跳过，只作为其附加组件
    tracker = current_tracker()
    if tracker:
        return tracker, True

    environ = headers
    if not headers:
        environ = {}

    tracker = Tracer(proxy_instance(), environ, vendor)
    tracker.start_work()

    if tracker.settings and not tracker.settings.mq.enabled:
        global_settings.enabled = False
        console.debug("Vendor %s consumer not enabled. Disable agent now", vendor)
        return None, False

    return tracker, False


def _do_comon_callback_wrap(wrapped, instance, args, kwargs):
    """
    :return:
    """
    tracker = current_tracker()
    if not tracker:
        console.debug("No tracker found for tracing %s", callable_name(wrapped))
        return wrapped(*args, **kwargs)

    with FunctionTracker(tracker, callable_name(wrapped)):
        return wrapped(*args, **kwargs)


def mq_common_callback_wrapper(wrapped, instance, args, kwargs):
    """
    :return:
    """
    def parse_callback(callback, *_args, **_kwargs):
        """
        :return:
        """
        return callback, _args, _kwargs

    cb, _args, _kwargs = parse_callback(*args, **kwargs)
    if getattr(cb, '_self_is_wrapped', None):
        console.debug("Consumer was wrapped before.")
        return wrapped(cb, *_args, **_kwargs)

    wrapped_cb = FunctionWrapper(cb, _do_comon_callback_wrap)
    wrapped_cb._self_is_wrapped = True

    return wrapped(wrapped_cb, *_args, **_kwargs)
