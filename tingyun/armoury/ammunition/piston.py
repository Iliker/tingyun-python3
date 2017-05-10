
"""define this module for detect django-piston package
"""

import logging
from tingyun.logistics.object_name import callable_name
from tingyun.armoury.ammunition.tracker import current_tracker
from tingyun.logistics.basic_wrapper import wrap_function_wrapper
from tingyun.armoury.ammunition.function_tracker import FunctionTracker


console = logging.getLogger(__name__)


def trace_resource_call(wrapped, instance, args, kwargs):
    """
    :param wrapped:
    :param instance:
    :param args:
    :param kwargs:
    :return:
    """
    method_mapping = {'GET': 'read', 'POST': 'create', 'PUT': 'update', 'DELETE': 'delete'}

    def parse_request(request, *args, **kwargs):
        return request

    tracker = current_tracker()
    if not tracker:
        return wrapped(*args, **kwargs)

    request = parse_request(*args, **kwargs)
    method = request.method.upper()

    # if invalid request method, use the origin request method
    # And using high priority to set the metric name.
    name = "%s.%s" % (callable_name(instance.handler), method_mapping.get(method, method))
    tracker.set_tracker_name(name=name, priority=5)
    with FunctionTracker(tracker, name):
        return wrapped(*args, **kwargs)


def detect_piston_resource(module):
    """
    :param module:
    :return:
    """
    wrap_function_wrapper(module, "Resource.__call__", trace_resource_call)
