import functools

from tingyun.logistics.basic_wrapper import FunctionWrapper, wrap_object
from tingyun.armoury.ammunition.tracker import current_tracker


class ErrorTrace(object):
    def __init__(self, tracker, ignore_errors=None):
        self._tracker = tracker
        self._ignore_errors = ignore_errors

    def __enter__(self):
        return self

    def __exit__(self, exc, value, tb):
        if exc is None or value is None or tb is None:
            return

        if self._tracker is None:
            return

        self._tracker.record_exception(exc=exc, value=value, tb=tb, ignore_errors=self._ignore_errors)


def error_trace_wrapper(wrapped, ignore_errors=None):

    def wrapper(wrapped, instance, args, kwargs):
        tracker = current_tracker()

        if tracker is None:
            return wrapped(*args, **kwargs)

        with ErrorTrace(tracker, ignore_errors):
            return wrapped(*args, **kwargs)

    return FunctionWrapper(wrapped, wrapper)


def wrap_error_trace(module, object_path, ignore_errors=None):
    wrap_object(module, object_path, error_trace_wrapper, (ignore_errors, ))
