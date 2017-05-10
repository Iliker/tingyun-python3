
"""Define this module for basic armory for bottle

"""

import logging
from tingyun.armoury.trigger.wsgi_entrance import wsgi_application_wrapper
from tingyun.armoury.ammunition.function_tracker import wrap_function_trace, FunctionTracker
from tingyun.logistics.basic_wrapper import FunctionWrapper, trace_out_function
from tingyun.armoury.ammunition.tracker import current_tracker
from tingyun.logistics.object_name import callable_name

console = logging.getLogger(__name__)


def detect_wsgi_entrance(module):
    """
    :param module:
    :return:
    """
    import bottle
    version = getattr(bottle, "__version__", 'xx')

    wsgi_application_wrapper(module.Bottle, '__call__', ('bottle', version))


def detect_templates(module):
    """
    :param module:
    :return:
    """
    # detect the template render
    if hasattr(module, 'SimpleTemplate'):
        wrap_function_trace(module, 'SimpleTemplate.render')

    if hasattr(module, 'MakoTemplate'):
        wrap_function_trace(module, 'MakoTemplate.render')

    if hasattr(module, 'CheetahTemplate'):
        wrap_function_trace(module, 'CheetahTemplate.render')

    if hasattr(module, 'Jinja2Template'):
        wrap_function_trace(module, 'Jinja2Template.render')

    if hasattr(module, 'SimpleTALTemplate'):
        wrap_function_trace(module, 'SimpleTALTemplate.render')


def route_callback_wrapper(wrapped):
    """wrap the route callback for trace the `route` performance
    :return:
    """
    def wrapper(wrapped, instance, args, kwargs):
        tracker = current_tracker()
        if not tracker:
            return wrapped(*args, **kwargs)

        tracker.set_tracker_name(callable_name(wrapped), priority=3)
        with FunctionTracker(tracker, callable_name(wrapped)):
            try:
                return wrapped(*args, **kwargs)
            except Exception as _:
                tracker.record_exception()
                raise

    return FunctionWrapper(wrapped, wrapper)


def detect_app_components(module):
    """
    :param module:
    :return:
    """
    if hasattr(module, 'Route') and hasattr(module.Route, '_make_callback'):
        trace_out_function(module, 'Route._make_callback', route_callback_wrapper)
