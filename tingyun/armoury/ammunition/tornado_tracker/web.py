
"""this module is implement some wrapper for trace the tornado web module

"""

import logging
import sys

from tingyun.armoury.ammunition.tracker import current_tracker
from tingyun.armoury.ammunition.function_tracker import FunctionTracker
from tingyun.armoury.ammunition.tornado_tracker.httpserver import generate_tracer, stop_request_tracer
from tingyun.armoury.ammunition.tornado_tracker.httpserver import setup_func_for_async_trace
from tingyun.armoury.ammunition.tracker import current_tracker
from tingyun.logistics.basic_wrapper import FunctionWrapper
from tingyun.logistics.object_name import callable_name


console = logging.getLogger(__name__)


def trace_request_exception(wrapped):
    """
    :param wrapped:
    :return:
    """
    def wrapper(wrapped, instance, args, kwargs):
        def parse_args(e, *args, **kwargs):
            return e

        tracer = getattr(instance.request, "_self_tracer", None)
        if tracer:
            e = parse_args(*args, **kwargs)
            tracer.http_status = getattr(e, 'status_code', 500)
            tracer.record_exception(*sys.exc_info())

        return wrapped(*args, **kwargs)

    return FunctionWrapper(wrapped, wrapper)


def trace_wsgi_app_entrance(wrapped):
    """flowing situations maybe faced.

        1. the tornado application transferred to run with WSGI server
        2. WSGI application run in tornado server.
        3. tornado application run in tornado server.
    """
    def parse_param(request, *args, **kwargs):
            return request, args, kwargs

    def trace_app_without_body(wrapped, instance, request, args, kwargs):
        """
        :return:
        """
        tracker = generate_tracer(request)
        if not tracker:
            return wrapped(*args, **kwargs)

        try:
            # we should use `FunctionWrapper` at here.because the Connection._on_finished will be executed in the
            # wrapped func. use `FunctionWrapper` will cause errors.
            ret = wrapped(*args, **kwargs)
        except:
            stop_request_tracer(request, *sys.exc_info(), segment="App.__call__.exception")
            raise
        else:
            if request._self_request_finished:
                return ret

            request._self_request_finished = True
            stop_request_tracer(request, segment='finish-app-call')
            return ret

    def wrapper(wrapped, instance, args, kwargs):
        """tracker will be put into the thread for other plugins trace in user code. such as mysql/memcached etc.
        :return:
        """
        request, _args, _kwargs = parse_param(*args, **kwargs)
        async_tracker = getattr(request, '_self_tracer', None)
        thread_tracker = current_tracker()

        # situation 1 & 2. just do nothing because the entrance of the wsgi app was detected.
        if not async_tracker and thread_tracker:
            # console.info("has not self tracer.%s, thread tracer %s", async_tracker, thread_tracker)
            return wrapped(*args, **kwargs)

        # situation 3. but no request body send by the client, at this case, the tracker was not set into the request
        # in HTTPConnection._on_headers
        if not async_tracker:
            return trace_app_without_body(wrapped, instance, request, args, kwargs)

        # situation 3. client send the header & body content to server for requesting data.
        return wrapped(*args, **kwargs)

    return FunctionWrapper(wrapped, wrapper)


def trace_request_execute(wrapped):
    """
    """
    def wrapper(wrapped, instance, args, kwargs):
        """
        """
        request = instance.request
        tracer = getattr(request, "_self_tracer", None)
        if not tracer:
            return wrapped(*args, **kwargs)

        name = callable_name(getattr(instance, instance.request.method.lower()))
        tracer.set_tracker_name(name, priority=3)

        with FunctionTracker(tracer, callable_name(wrapped)):
            thread_tracer = current_tracker()
            if thread_tracer:
                console.info("Ignore user code metric trace for current request, this will maybe cause lack of some "
                             "metric data. if this continues, please report to us, thank u.")
                return wrapped(*args, **kwargs)

            # at here, we get the user code. we just put the tracer to the thread for non-framework plugin use.after
            # this, we drop it again. and ignore all of the errors occurred.
            try:
                tracer.save_tracker()
            except Exception as _:
                console.error("Errors, when the tracer put into the thread, this should not occurred, if this "
                              "continues, please report to us, thank u")
            ret = wrapped(*args, **kwargs)
            try:
                tracer.drop_tracker()
            except Exception as _:
                console.error("Errors, when the tracer dropped from the thread, this should not occurred, if this "
                              "continues, please report to us, thank u")

            return ret

    return FunctionWrapper(wrapped, wrapper)


def trace_request_init(wrapped):
    """hook the __init__ just for every class instance method.
    """
    def trace_user_func(wrapped):
        """
        """
        def user_func_wrapper(wrapped, instance, args, kwargs):
            tracer = getattr(instance.request, "_self_tracer", None)
            if not tracer:
                # console.info("ignore trace func %s", callable_name(wrapped))
                return wrapped(*args, **kwargs)

            with FunctionTracker(tracer, callable_name(wrapped)):
                # console.info("---------------trace func %s", callable_name(wrapped))
                return wrapped(*args, **kwargs)

        return FunctionWrapper(wrapped, user_func_wrapper)

    def wrapper(wrapped, instance, args, kwargs):
        """
        """
        instance.prepare = trace_user_func(instance.prepare)
        instance.on_finish = trace_user_func(instance.on_finish)
        instance.on_connection_close = trace_user_func(instance.on_connection_close)
        instance.initialize = trace_user_func(instance.initialize)

        for name in instance.SUPPORTED_METHODS:
            name = name.lower()
            if hasattr(instance, name):
                setattr(instance, name, trace_user_func(getattr(instance, name)))

        return wrapped(*args, **kwargs)

    return FunctionWrapper(wrapped, wrapper)
