# -*- coding: utf-8 -*-

import sys
import logging
from tingyun.armoury.ammunition.tornado.name_parser import object_name
from tingyun.armoury.ammunition.function_tracker import FunctionTracker
from tingyun.armoury.ammunition.tornado.wrappers import wrap_function_wrapper, function_wrapper
from tingyun.armoury.ammunition.tornado_4.utils import TrackerTransferContext
from tingyun.armoury.ammunition.tornado_4.utils import obtain_tracker_from_request, record_exception

console = logging.getLogger(__name__)


@function_wrapper
def trace_handler_execute(wrapped, instance, args, kwargs):
    """
    """
    handler = instance
    request = handler.request

    if not request:
        console.warning("No request instance got from handler. this maybe agent potential design issues. "
                        "if this continue, please report to us.")
        return wrapped(*args, **kwargs)

    tracker = obtain_tracker_from_request(request)
    if not tracker:
        return wrapped(*args, **kwargs)

    if request.method not in handler.SUPPORTED_METHODS:
        name = object_name(wrapped)
    else:
        name = object_name(getattr(handler, request.method.lower()))

    tracker.set_tracker_name(name, priority=3)
    with TrackerTransferContext(tracker):
        return wrapped(*args, **kwargs)


@function_wrapper
def _do_method_trace(wrapped, instance, args, kwargs):

    tracker = obtain_tracker_from_request(instance.request)
    if not tracker:
        return wrapped(*args, **kwargs)

    with FunctionTracker(tracker, name=object_name(wrapped)):
        return wrapped(*args, **kwargs)


@function_wrapper
def _do_http_method_trace(wrapped, instance, args, kwargs):
    """所有从用户代码开始的性能采集要从内存中获取tracker对象，而不是request对象中获取，
    后续所有的性能捕获，都需要上下文管理器修饰
    """
    tracker = obtain_tracker_from_request(instance.request)
    if not tracker:
        return wrapped(*args, **kwargs)

    tracker.set_tracker_name(object_name(wrapped), priority=3)
    with FunctionTracker(tracker, name=object_name(wrapped)):
        return wrapped(*args, **kwargs)


def trace_handler_init(wrapped, instance, args, kwargs):
    """
    """
    def parse_class_name(method):
        """parse the class name of the method belong to
        """
        for cls in method.__self__.__class__.__mro__:
            if method.__name__ in cls.__dict__:
                return cls.__name__

        return "Unknown"

    def parse_request_method(application, request, *args, **kwargs):
        """接口参考RequestHandler.__init__(self, application, request, **kwargs)
        :return:
        """
        return str(request.method).lower()

    result = wrapped(*args, **kwargs)

    # 正常情况下tracker应该附加在instance.request上，若没有初始化成功，直接放弃打包
    tracker = obtain_tracker_from_request(instance.request)
    if not tracker:
        console.debug("tracker is not initialized before give up trace the function %s", object_name(wrapped))
        return wrapped(*args, **kwargs)

    # 由于是动态`临时`打包， 只捕获请求方法的性能即可
    method = parse_request_method(*args, **kwargs)
    func = getattr(instance, method, None)
    if func and not hasattr(func, "_previous_object"):
        setattr(instance, method, _do_http_method_trace(func))

    # prepare & on_finish & _handle_request_exception 多半是在用户代码实现，
    # 所以需要在实际初始化的时候进行处理. 如果这些函数使用了coroutine，则他们可能已经被打包过了，
    # 所以需要检查下，方式多次打包
    if parse_class_name(instance.prepare) != 'RequestHandler' and not hasattr(instance.prepare, "_previous_object"):
        instance.prepare = _do_method_trace(instance.prepare)

    if parse_class_name(instance.on_finish) != 'RequestHandler' and not hasattr(instance.on_finish, "_previous_object"):
        instance.on_finish = _do_method_trace(instance.on_finish)

    if _do_method_trace(instance._handle_request_exception) != 'RequestHandler' and \
            not hasattr(instance._handle_request_exception, "_previous_object"):
        instance._handle_request_exception = _do_method_trace(instance._handle_request_exception)

    #  防止用户覆盖此方法导致数据抓取异常，tracker无法进入线程队列
    instance._execute = trace_handler_execute(instance._execute)

    return result


def trace_handler_request_exception(wrapped, instance, args, kwargs):
    """
    """
    tracker = obtain_tracker_from_request(instance.request)

    with TrackerTransferContext(tracker):
        record_exception(sys.exc_info())
        return wrapped(*args, **kwargs)


def trace_handler_flush(wrapped, instance, args, kwargs):
    """数据被写入socket的时候获取响应状态码
    :return:
    """
    request = instance.request
    if not request:
        console.warning("No request instance got from handler, this maybe agent potential design issues.")
        return wrapped(*args, **kwargs)

    tracker = obtain_tracker_from_request(request)
    if not tracker:
        return wrapped(*args, **kwargs)

    tracker.deal_response('%s ok' % getattr(instance, '_status_code') or 500, {})
    return wrapped(*args, **kwargs)


def detect_web(module):
    """
    :param module:
    :return:
    """
    wrap_function_wrapper(module, "RequestHandler.__init__", trace_handler_init)
    wrap_function_wrapper(module, "RequestHandler._handle_request_exception", trace_handler_request_exception)
    wrap_function_wrapper(module, "RequestHandler.flush", trace_handler_flush)
