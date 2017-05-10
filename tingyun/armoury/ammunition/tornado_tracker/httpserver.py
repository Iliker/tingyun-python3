
"""this module is implement some wrapper for trace the tornado httpserver module

"""

import sys
import logging
import traceback

from tingyun.battlefield.tracer import Tracer
from tingyun.battlefield.proxy import proxy_instance
from tingyun.logistics.object_name import callable_name
from tingyun.logistics.basic_wrapper import FunctionWrapper

from tingyun.armoury.ammunition.tracker import current_tracker
from tingyun.armoury.ammunition.function_tracker import FunctionTracker


console = logging.getLogger(__name__)


def request_environ(environ, request):
    """the environ in the default environ may not include our need environment variable when apply to wsgi application
    :param environ: returned environment from the container request.
    :param request:
    :return:
    """
    # we need this the build the request information. but not included in the environment.
    ret = dict(environ)
    ret["REQUEST_URI"] = request.uri
    ret["HTTP_REFERER"] = request.headers.get('Referer', '')
    ret['HTTP_X_QUEUE_START'] = request.headers.get("X-Queue-Start")

    if not environ:
        ret['PATH_INFO'] = request.path
        ret['SCRIPT_NAME'] = ""
        ret['QUERY_STRING'] = request.query

    return ret


def setup_func_for_async_trace(request, name, group='async.wait'):
    """used to suspend function between async call with function
    thread_mode: this indicate, relate the tracer to the thread.this should be used with resume_async_trace func

    request: the HTTPRequest for connection
    """
    tracer = getattr(request, '_self_tracer', None)
    if not tracer:
        console.warning("tracker lost when trace the request call chain with async, this trace for function time"
                        " metric will be interrupted. %s", ''.join(traceback.format_stack()[:-1]))
        return

    if getattr(request, "_self_async_function_tracker", None):
        console.warning("The last tracker for time metric not finished, but this should not happened."
                        "this maybe some logical error in agent. %s", ''.join(traceback.format_stack()[:-1]))
        return

    # console.info("set func for async trace with name %s", name)
    request._self_async_function_tracker = FunctionTracker(tracer, name, group)
    request._self_async_function_tracker.__enter__()


def finish_async_func_trace(request, group=None):
    """calculate the time metric for async call between func
    thread_mode: this indicate, relate the tracer to the thread.this should be used with setup_async_trace func

    request: the HTTPRequest for connection
    """
    tracer = getattr(request, '_self_tracer', None)
    if not tracer:
        console.warning("tracker lost when trace the request call chain with async, this trace for function time"
                        " metric will be interrupted. %s", ''.join(traceback.format_stack()[:-1]))
        return

    try:
        # console.info("finish async func trace with group %s", group)
        if request._self_async_function_tracker:
            request._self_async_function_tracker.__exit__(None, None, None)
            tracer.async_func_trace_time += request._self_async_function_tracker.duration

    finally:
        request._self_async_function_tracker = None

    return tracer


def stop_request_tracer(request, exc_type=None, exc_val=None, exc_tb=None, segment=None):
    """
    """
    tracer = getattr(request, '_self_tracer', None)

    try:
        if not tracer:
            console.debug("tracker lost when trace the request call chain with async, this trace for function time"
                          " metric will be interrupted. %s", ''.join(traceback.format_stack()[:-1]))
            return

        # deal the case which the tracer hold by current request saved in thread cache
        thread_tracer = current_tracker()
        if tracer == thread_tracer:
            tracer.finish_work(exc_type, exc_val, exc_tb, False)
        else:
            tracer.finish_work(exc_type, exc_val, exc_tb, True)
    except Exception as err:
        console.exception("Tornado raise error when stop the trace. %s, %s", segment, err)
    finally:
        request._self_request_finished = True
        request._self_tracer = None
        request._self_async_function_tracker = None

    # console.info("stop request tracer with segment %s", segment)


def generate_tracer(request, framework='Tornado'):
    """
    :param request: the http request for client
    :return:
    """
    tracer = Tracer(proxy_instance(), request_environ({}, request), framework)
    if not tracer.enabled:
        # console.debug("Agent not prepared, skip trace this request now.")
        return None

    try:
        tracer.start_work()
        tracer.drop_tracker()  # drop it from thread cache

        request._self_request_finished = False
        request._self_tracer = tracer
        request._self_async_function_tracker = None
    except Exception as err:
        stop_request_tracer(request, *(sys.exc_info() + ("generate-tracker-exception", )))
        console.exception("Error occurred, when generate a tracker for tornado. %s", err)
        raise

    return tracer


def connection_on_headers_wrapper(wrapped):
    """if client request server without body, so the request in connection object maybe None at there
    """
    def wrapper(wrapped, adapter, args, kwargs):
        """
        :param wrapped: the wrapped function `HTTPConnection._on_headers`
        :param adapter: the instance of the `HTTPConnection`
        :param args: args for `HTTPConnection._on_headers`
        :param kwargs: kwargs for `HTTPConnection._on_headers`
        :return: return of `HTTPConnection._on_headers` method
        """
        # add some ensurance for potential error, if this occurred, that indicate some wrong with last trace.
        # Then we drop the last trace and ignore this trace now.
        tracer = current_tracker()
        if tracer:
            console.warning("Unexpected situation arise, but no side effect to use the agent. That's only indicate "
                            "some illogicality tracker in tracer. if this continue, please report to us, thank u.")
            tracer.drop_tracker()
            return wrapped(*args, **kwargs)

        ret = wrapped(*args, **kwargs)

        # for version3.x.x
        if (hasattr(adapter, "stream") and adapter.stream.closed()) or \
           (hasattr(adapter, "_request_finished") and adapter._request_finished):

            # console.debug("stream closed(%s). in version 3", adapter.stream.closed())
            # console.debug("request finished. %s in version 3", adapter._request_finished)
            return ret

        # for version4.x.x
        if hasattr(adapter, "connection") and adapter.connection.stream.closed():
            # console.debug("stream closed(%s). .in version 4", adapter.stream.closed())
            return ret

        # Because of the asynchronous and single thread feature. we store the tracer in the request.
        # we use _self_ to prevent conflict to the wrapped func namespace.
        # request maybe empty.
        if hasattr(adapter, "connection"):
            request = adapter.request
        else:
            request = adapter._request

        if not request or hasattr(request, '_self_tracer'):
            # console.debug("request(%s) or has _self_tracer(%s)", request, hasattr(request, '_self_tracer'))
            return ret

        # when request with no body, the wrapped function will call Application.__call__, so the tracer maybe create
        # then we should skip.
        if hasattr(request, '_self_tracer'):
            # console.info("on-header returned with request has tracer before")
            return ret

        tracer = generate_tracer(request)
        if not tracer or not tracer.enabled:
            return ret

        # iostream can not fetch the _request object, so we just set a callback to the stream associate with the request
        # with closure
        def _stream_close_callback():
            if finish_async_func_trace(request, ""):
                return

            stop_request_tracer(request, segment='stream-close-callback')

        # version 4
        if hasattr(adapter, "connection"):
            adapter.connection.stream._self_stream_close_callback = _stream_close_callback
        else:
            adapter.stream._self_stream_close_callback = _stream_close_callback

        tracer.set_tracker_name(callable_name(wrapped))
        # at the start beginning, we set the track to the request object for next call-step use
        setup_func_for_async_trace(request, "connection.header-to-body")
        return ret

    return FunctionWrapper(wrapped, wrapper)


def connect_on_request_body_wrapper(wrapped):
    """
    """
    def wrapper(wrapped, adapter, args, kwargs):
        """
        """
        # in tornado 4.x.x
        if hasattr(adapter, "connection"):
            request = adapter.request
        else:
            request = adapter._request

        tracer = finish_async_func_trace(request, group='request-body-in')
        if not tracer:
            # console.info("body do not get the tracer...")
            return wrapped(*args, **kwargs)

        try:
            # console.info("execute request body...")
            ret = wrapped(*args, **kwargs)
        except Exception as err:
            console.exception("Tornado raise error in HTTPConnection on_request_body. %s", err)
            stop_request_tracer(request, *(sys.exc_info() + ("request-body-exception", )))
            raise
        else:
            if request._self_request_finished:
                return ret

            if not request.connection.stream.writing():
                stop_request_tracer(request, segment='stream-not-writing')
                return ret

            setup_func_for_async_trace(request, name="connection.body-to-finish")

        return ret

    return FunctionWrapper(wrapped, wrapper)


def connection_finish_request_wrapper(wrapped):
    """the wrapped function maybe called more than once.
    """
    def wrapper(wrapped, adapter, args, kwargs):
        """
        """
        # in tornado 4.x.x
        if hasattr(adapter, "connection"):
            request = adapter.request
        else:
            request = adapter._request

        tracer = getattr(request, "_self_tracer", None)

        if not tracer:
            # console.debug("tracer is not found maybe finished before.")
            return wrapped(*args, **kwargs)

        if request._self_request_finished:
            # console.debug("tracer for current request is finished")
            return wrapped(*args, **kwargs)

        tracer = finish_async_func_trace(request, "request-finish-in")
        if not tracer:
            # console.debug("resumed a none tracer....")
            return wrapped(*args, **kwargs)

        try:
            # console.info("execute connect finish finished....")
            ret = wrapped(*args, **kwargs)
        except Exception as _:
            stop_request_tracer(request, *(sys.exc_info() + ("connect-finished-with-exceptiono", )))
            raise
        else:
            # in tornado 4.x.x, the application.__call__ will not be called directly. but call the `execute` to call
            # the RequestHandler. so we should finish our tracker at there.
            if hasattr(adapter, "connection"):
                stop_request_tracer(request, segment='finish-app-call')

        return ret

    return FunctionWrapper(wrapped, wrapper)


def iostream_close_callback_wrapper(wrapped):
    """if client communicate with server user keep-alive protocol, the callback can not be actived.
    """

    def wrapper(wrapped, instance, args, kwargs):
        """
        """
        if not instance.closed():
            # console.debug("stream not closed, skip to finish the trace.")
            return wrapped(*args, **kwargs)

        if instance._pending_callbacks != 0:
            # console.debug("pending callback, skip to finish the trace.")
            return wrapped(*args, **kwargs)

        callback = getattr(instance, '_self_stream_close_callback', None)
        instance._self_stream_close_callback = None

        if callback:
            callback()

        return wrapped(*args, **kwargs)

    return FunctionWrapper(wrapped, wrapper)
