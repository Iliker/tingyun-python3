# -*- coding: utf-8 -*-

"""define some common method for tornado tracker
"""

import sys
import logging
import weakref
from tingyun.battlefield.tracer import Tracer
from tingyun.battlefield.knapsack import knapsack
from tingyun.battlefield.proxy import proxy_instance
from tingyun.armoury.ammunition.tornado_4.name_parser import object_name
from tingyun.armoury.ammunition.tornado_4.wrappers import function_wrapper
from tingyun.armoury.ammunition.tracker import current_tracker
from tingyun.armoury.ammunition.function_tracker import FunctionTracker

console = logging.getLogger(__name__)


def is_websocket(request):
    """Now web ignore websocket feature. it's not in our current conversation.
    :param request:
    :return:
    """
    if request.headers.get('Upgrade', '').lower() == 'websocket':
        console.info("current request is web socket, agent will ignore this tracker.")
        return True

    return False


class NoneProxy(object):
    pass


def record_exception(exc_info):
    """
    :return:
    """
    import tornado.web
    exc = exc_info[0]

    # Not an error so we just return.
    if exc is tornado.web.Finish:
        return

    tracker = obtain_current_tracker()
    if tracker:
        tracker.record_exception(*exc_info)


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


def obtain_current_tracker():
    """ Get the tracker from tracer cache.
    :return:
    """
    return current_tracker()


def obtain_tracker_from_request(request):
    """
    :param request: httpserver request
    :return:
    """
    tracker = getattr(request, '_nb_tracker', None)
    if not tracker:
        console.debug("No tracker found in request[%s], if this continues, please report to us.", request)

    return tracker


def obtain_request(tracker):
    """obtain the request object from tracker. which is attached at began
    :param tracker:
    :return:
    """
    # its' weakref
    request = getattr(tracker, "_nb_request", None)
    return request() if request else None


def current_thread_id():
    return knapsack().current_thread_id()


def drop_current_tracer():
    """ separate the tracker from agent thread
    :return:
    """
    old_tracker = obtain_current_tracker()
    if old_tracker is not None:
        old_tracker.drop_tracker()
    return old_tracker


def finish_tracker(tracker, exc_type=None, exc_val=None, exc_tb=None):
    if not tracker:
        console.error("Tracker is None, shit maybe some trace strategy issue. if this continues. please report to us.")
        return

    if getattr(tracker, "_is_finalized"):
        console.error("This errors maybe caused by some agent logic trace error. if this continues, please report to"
                      " us for further investigation.")
        return

    # check the tracker status.
    if not (getattr(tracker, "_can_finalize") and getattr(tracker, "_ref_count") == 0):
        console.debug("tracker can not finished. because of the some trace still in work.")
        return

    old_tracker = replace_current_tracer(tracker)
    try:
        tracker.finish_work(exc_type, exc_val, exc_tb, async=False)
    finally:
        setattr(tracker, "_is_finalized", True)
        request = obtain_request(tracker)
        if request:
            setattr(request, "_nb_tracker", None)

        setattr(tracker, "_nb_request", None)

        # put back the previous tracker to tracker cache.
        if tracker != old_tracker:
            replace_current_tracer(old_tracker)


def replace_current_tracer(new_tracker):
    """ Set the current tracer into agent thread and return the old one.
    :param new_tracker:
    :return:
    """
    old_tracker = drop_current_tracer()
    if new_tracker:
        new_tracker.save_tracker()

    return old_tracker


def generate_tracer(request, framework='Tornado'):
    """
    :param request: the http request for client
    :return:
    """
    drop_current_tracer()
    tracer = Tracer(proxy_instance(), request_environ({}, request), framework)
    if not tracer.enabled:
        return None

    tracer.start_work()
    drop_current_tracer()  # drop it from thread cache
    tracer._nb_request = weakref.ref(request)

    # when 'finish' or 'on_connection_close' is called on server requests. tracer should be finished trace.
    tracer._is_finalized = False
    tracer._ref_count = 0  # count the reference.
    tracer._can_finalize = False

    return tracer


class TrackerTransferContext(object):
    def __init__(self, tracer):
        self.tracer = tracer

    def __enter__(self):
        self.old_tracer = replace_current_tracer(self.tracer)

    def __exit__(self, exc_type, exc_value, traceback):
        replace_current_tracer(self.old_tracer)


def create_tracker_aware_fxn(fxn, fxn_for_name=None, should_trace=True):
    if fxn is None or hasattr(fxn, '_nb_tracker'):
        return None

    if fxn_for_name is None:
        fxn_for_name = fxn

    tracker = [obtain_current_tracker()]

    @function_wrapper
    def tracker_aware(wrapped, instance, args, kwargs):
        # Variables from the outer scope are not assignable in a closure, so we use a mutable object to hold the
        # tracker, so we can change it if we need to.
        inner_tracker = tracker[0]

        if inner_tracker is not None:
            # Callback run outside the main thread must not affect the cache
            if inner_tracker.thread_id != current_thread_id():
                return fxn(*args, **kwargs)

        if inner_tracker is not None and inner_tracker._is_finalized:
            inner_tracker = None
            tracker[0] = None

        with TrackerTransferContext(inner_tracker):
            if inner_tracker is None:
                # A tracker will be None for fxns scheduled on the ioloop not associated with a tracker.
                ret = fxn(*args, **kwargs)
            elif should_trace is False:
                try:
                    ret = fxn(*args, **kwargs)
                except:
                    record_exception(sys.exc_info())
                    wrapped._nb_recorded_exception = True
                    raise

            else:
                name = object_name(fxn_for_name)
                with FunctionTracker(inner_tracker, name=name) as ft:

                    try:
                        ret = fxn(*args, **kwargs)
                    except:
                        record_exception(sys.exc_info())
                        wrapped._nb_recorded_exception = True
                        raise
                    if ft is not None and ret is not None and hasattr(ret, '_nb_coroutine_name'):
                        ft.name = ret._nb_coroutine_name

                        if type(ret) == NoneProxy:
                            ret = None

        if inner_tracker and inner_tracker._ref_count == 0:
            finish_tracker(inner_tracker)

        return ret

    return tracker_aware(fxn)
