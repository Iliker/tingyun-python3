# -*- coding: utf-8 -*-

"""define detector for detect stack context module
"""

import logging
from tingyun.armoury.ammunition.tornado_4.wrappers import wrap_function_wrapper
from tingyun.armoury.ammunition.tornado_4.utils import create_tracker_aware_fxn, obtain_current_tracker
from tingyun.armoury.ammunition.tornado_4.utils import record_exception

console = logging.getLogger(__name__)
fxn_cache = []


def trace_wrap(wrapped, instance, args, kwargs):
    """
    """
    def _fxn_arg_extractor(fn, *args, **kwargs):
        return fn

    unwrapped_fxn = _fxn_arg_extractor(*args, **kwargs)
    wrapped_fxn = wrapped(*args, **kwargs)
    should_trace = not hasattr(unwrapped_fxn, '_previous_object')
    tracker_aware_fxn = create_tracker_aware_fxn(wrapped_fxn, fxn_for_name=unwrapped_fxn, should_trace=should_trace)

    if tracker_aware_fxn is None:
        return wrapped_fxn

    tracker_aware_fxn._wrapped = True
    tracker_aware_fxn._nb_tracker = obtain_current_tracker()

    return tracker_aware_fxn


def trace_handle_exception(wrapped, instance, args, kwargs):
    """
    """
    def _exc_extractor(tail, exc, *args, **kwargs):
        return exc

    exc = _exc_extractor(*args, **kwargs)

    record_exception(exc)
    return wrapped(*args, **kwargs)


def detect_stack_context(module):
    """
    """
    wrap_function_wrapper(module, 'wrap', trace_wrap)
    wrap_function_wrapper(module, '_handle_exception', trace_handle_exception)
