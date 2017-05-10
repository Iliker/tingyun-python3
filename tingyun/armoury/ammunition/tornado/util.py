# -*- coding: utf-8 -*-

import logging
import threading
import weakref

from tingyun.battlefield.tracer import Tracer
from tingyun.battlefield.proxy import proxy_instance
from tingyun.armoury.ammunition.tracker import current_tracker

console = logging.getLogger(__name__)
ty_local = threading.local()


def is_websocket(request):
    """Now web ignore websocket feature. it's not in our current conversation.
    :param request: HTTP request header
    :return:
    """
    if request.headers.get('Upgrade', '').lower() == 'websocket':
        console.debug("current request is web socket, agent will ignore this tracker.")
        return True

    return False


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


def drop_current_tracer():
    """ separate the tracker from agent thread
    :return:
    """
    old_tracker = obtain_current_tracker()
    if old_tracker is not None:
        old_tracker.drop_tracker()
    return old_tracker


def replace_current_tracer(new_tracker):
    """ Set the current tracer into agent thread and return the old one.
    :param new_tracker:
    :return:
    """
    old_tracker = drop_current_tracer()
    if new_tracker:
        new_tracker.save_tracker()

    return old_tracker


def obtain_request(tracker):
    """obtain the request object from tracker. which is attached at began
    :param tracker:
    :return:
    """
    # its' weakref
    request = getattr(tracker, "_nb_request", None)
    return request() if request else None


class TrackerTransferContext(object):
    def __init__(self, tracer):
        self.tracer = tracer

    def __enter__(self):
        self.old_tracer = replace_current_tracer(self.tracer)

    def __exit__(self, exc_type, exc_value, traceback):
        replace_current_tracer(self.old_tracer)


def record_exception(exc_info, tracker=None):
    """
    :return:
    """
    import tornado.web
    exc = exc_info[0]

    # Not an error so we just return.
    if exc is tornado.web.Finish:
        return

    tracker = tracker or obtain_current_tracker()
    if tracker:
        tracker.record_exception(*exc_info)


def obtain_tracker_from_request(request):
    """
    :param request: httpserver request
    :return:
    """
    tracker = getattr(request, '_nb_tracker', None)
    if not tracker:
        console.debug("No tracker found in request[%s], if this continues, please report to us.", request)

    return tracker


def generate_tracer(request, framework='Tornado'):
    """
    :param request: the http request for client
    :param framework: framework name
    :return:
    """
    old_tracker = drop_current_tracer()
    tracker = Tracer(proxy_instance(), request_environ({}, request), framework)
    if not tracker.enabled:
        return None

    tracker.start_work()
    drop_current_tracer()  # drop it from thread cache
    tracker._nb_request = weakref.ref(request)
    request._nb_tracker = tracker

    replace_current_tracer(old_tracker)

    return tracker


def finish_tracker(tracker, exc_type=None, exc_val=None, exc_tb=None):
    if not tracker:
        console.error("Tracker is None, shit maybe some trace strategy issue. if this continues. please report to us.")
        return

    if getattr(tracker, "_is_finalized", None):
        console.error("This errors maybe caused by some agent logic trace error. if this continues, please report to"
                      " us for further investigation.")
        return

    old_tracker = replace_current_tracer(tracker)
    try:
        tracker.finish_work(exc_type, exc_val, exc_tb, async=True)
    finally:
        setattr(tracker, "_is_finalized", True)

        if getattr(tracker, "_nb_request", None):
            setattr(tracker, "_nb_request", None)

        request = getattr(tracker, "_nb_request", None)
        if hasattr(request, "_nb_tracker"):
            setattr(request, "_nb_tracker", None)

        # put back the previous tracker to tracker cache.
        if tracker != old_tracker:
            replace_current_tracer(old_tracker)
