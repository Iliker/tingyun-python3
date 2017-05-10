
"""this module is implement the function detector for webpy

"""
import logging
import sys
from tingyun.logistics.basic_wrapper import FunctionWrapper, wrap_object
from tingyun.logistics.object_name import callable_name
from tingyun.armoury.ammunition.function_tracker import FunctionTracker
from tingyun.armoury.ammunition.tracker import current_tracker
from tingyun.packages import six

console = logging.getLogger(__name__)


def app_delegate_wrapper(wrapped):
    """
    :param wrapped:
    :return:
    """
    def wrapper(wrapped, instance, args, kwargs):
        f, fvars, fargs = args
        tracker = current_tracker()
        if not tracker:
            return wrapped(f, fvars, fargs)

        if isinstance(f, six.string_types):
            name = f
        else:
            name = callable_name(f)

        tracker.set_tracker_name(name, 2)
        with FunctionTracker(tracker, name):
            try:
                return wrapped(*args, **kwargs)
            except Exception:
                tracker.record_exception(*sys.exc_info())
                raise

    return FunctionWrapper(wrapped, wrapper)


def trace_app_views(module, object_path):
    wrap_object(module, object_path, app_delegate_wrapper)
