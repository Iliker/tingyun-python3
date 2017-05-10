# -*- coding: utf-8 -*-

"""define detector for tornado.gen
"""

import logging
from tingyun.armoury.ammunition.tornado_4.name_parser import object_name
from tingyun.armoury.ammunition.tornado_4.wrappers import wrap_function_wrapper, function_wrapper

from tingyun.armoury.ammunition.tornado_4.utils import obtain_current_tracker, NoneProxy
from tingyun.armoury.ammunition.function_tracker import FunctionTracker

console = logging.getLogger(__name__)

try:
    import sys
    get_frame = sys._getframe
except Exception, _:
    console.warning('You are using a python implementation without sys._getframe.')
    import inspect

    def _get_frame(depth):
        return inspect.stack(0)[depth]

    get_frame = _get_frame


def trace_runner_init(wrapped, instance, args, kwargs):
    """
    """
    tracker = obtain_current_tracker()
    if tracker is None:
        return wrapped(*args, **kwargs)

    try:
        frame = get_frame(1)
    except ValueError:
        console.debug('tornado.gen.Runner is being created at the top of the stack. .')
        return wrapped(*args, **kwargs)

    max_frame_depth = 5
    frame_depth = 1
    while frame and frame_depth <= max_frame_depth:
        if frame.f_globals['__name__'] == 'tornado.gen':
            break
        frame = frame.f_back
        frame_depth += 1

    def _coroutine_name(func):
        return '%s %s' % (object_name(func), '(coroutine)')

    if '__name__' in frame.f_globals and frame.f_globals['__name__'] == 'tornado.gen' and \
       'func' in frame.f_locals and 'replace_callback' in frame.f_locals and frame.f_code.co_name == 'wrapper':

        instance._nb_coroutine_name = _coroutine_name(frame.f_locals['func'])

    tracker._ref_count += 1

    return wrapped(*args, **kwargs)


def trace_runner_run(wrapped, instance, args, kwargs):
    """
    """
    result = wrapped(*args, **kwargs)

    tracker = obtain_current_tracker()
    if tracker is None:
        return result

    if result is None:
        result = NoneProxy()

    if hasattr(instance, '_nb_coroutine_name') and instance._nb_coroutine_name is not None:
        result._nb_coroutine_name = instance._nb_coroutine_name

    if instance.finished:
        tracker._ref_count -= 1

    return result


@function_wrapper
def _do_wrap_decorated(wrapped, instance, args, kwargs):
    """
    """
    tracker = obtain_current_tracker()

    if tracker is None:
        return wrapped(*args, **kwargs)

    with FunctionTracker(tracker, name=object_name(wrapped)):
        return wrapped(*args, **kwargs)


def trace_coroutine(wrapped, instance, args, kwargs):
    """
    """
    func = wrapped(*args, **kwargs)
    return _do_wrap_decorated(func)


def trace_engine(wrapped, instance, args, kwargs):
    """
    """
    func = wrapped(*args, **kwargs)
    return _do_wrap_decorated(func)


def detect_gen(module):
    """
    """
    wrap_function_wrapper(module, 'Runner.__init__', trace_runner_init)
    wrap_function_wrapper(module, 'Runner.run', trace_runner_run)
    wrap_function_wrapper(module, 'coroutine', trace_coroutine)
    wrap_function_wrapper(module, 'engine', trace_engine)
