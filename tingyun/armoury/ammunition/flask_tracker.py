
"""this module is implement the function detector for flask

"""
import logging
from tingyun.logistics.basic_wrapper import FunctionWrapper
from tingyun.logistics.object_name import callable_name
from tingyun.armoury.ammunition.function_tracker import FunctionTracker
from tingyun.armoury.ammunition.tracker import current_tracker

console = logging.getLogger(__name__)


def _wrapper_deco(priority=None):
    def _wrapper(wrapped, instance, args, kwargs):
        """
        :param wrapped:
        :param instance:
        :param args:
        :param kwargs:
        :return:
        """
        tracker = current_tracker()
        if not tracker:
            return wrapped(*args, **kwargs)

        tracker.set_tracker_name(callable_name(wrapped), priority=priority)
        with FunctionTracker(tracker, callable_name(wrapped)):
            return wrapped(*args, **kwargs)

    return _wrapper


def add_url_rule_wrapper(wrapped, instance, args, kwargs):
    """used to trace the views metric
    :param wrapped:
    :param instance:
    :return:
    """
    def parse_view_func(rule, endpoint=None, view_func=None, **options):
        return rule, endpoint, view_func, options

    rule, endpoint, view_func, options = parse_view_func(*args, **kwargs)

    return wrapped(rule, endpoint, FunctionWrapper(view_func, _wrapper_deco(4)), **options)


def handle_exception_wrapper(wrapped, instance, args, kwargs):
    """used to trace the exception errors.
    :param wrapped:
    :param instance:
    :param args:
    :param kwargs:
    :return:
    """
    tracker = current_tracker()
    if not tracker:
        return wrapped(*args, **kwargs)

    # just record the exception info
    tracker.record_exception()

    return wrapped(*args, **kwargs)


def wrap_register_error(wrapped, instance, args, kwargs):
    """
    :param module:
    :return:
    """
    def parse_func_params(key, code_or_exception, f, *args, **kwargs):
        return key, code_or_exception, f, args, kwargs

    key, code_or_exception, f, _args, _kwargs = parse_func_params(*args, **kwargs)

    return wrapped(key, code_or_exception, FunctionWrapper(f, _wrapper_deco()), *_args, **_kwargs)


def wrap_func_with_request(wrapped, instance, args, kwargs):
    """
    :param wrapped:
    :param instance:
    :param args:
    :param kwargs:
    :return:
    """
    def parse_func_params(f, *args, **kwargs):
        return f, args, kwargs

    f, _args, _kwargs = parse_func_params(*args, **kwargs)
    return wrapped(FunctionWrapper(f, _wrapper_deco()), *_args, **_kwargs)


def wrap_template_filter(wrapped, instance, args, kwargs):
    """
    :param wrapped:
    :param instance:
    :param args:
    :param kwargs:
    :return:
    """
    def parse_func_params(name, *args, **kwargs):
        return name, args, kwargs

    name, _args, _kwargs = parse_func_params(*args, **kwargs)
    return FunctionWrapper(wrapped(name, *_args, **_kwargs), _wrapper_deco())
