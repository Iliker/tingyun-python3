"""this module is implement the data input read for wsgi

"""
import sys
import threading
import logging

from tingyun.armoury.ammunition.function_tracker import FunctionTracker, wrap_function_trace
from tingyun.logistics.basic_wrapper import FunctionWrapper, wrap_object
from tingyun.logistics.object_name import callable_name
from tingyun.armoury.ammunition.tracker import current_tracker


middleware_detected_lock = threading.Lock()
console = logging.getLogger(__name__)


def should_ignore(exc, value, tb, ignore_status_code=[]):
    from django.http import Http404

    if isinstance(value, Http404) and 404 in ignore_status_code:
        return True

    return False


def _do_wrap_middleware(middleware, detect_name=False):
    """
    :param middleware: the middleware list in django setting
    :return:
    """
    def wrapper(wrapped):
        name = callable_name(wrapped)

        def wrapper(wrapped, instance, args, kwargs):
            tracker = current_tracker()
            if tracker is None:
                return wrapped(*args, **kwargs)

            before_name = "%s.%s" % (tracker.name, tracker.group)
            with FunctionTracker(tracker, name=name):
                try:
                    return wrapped(*args, **kwargs)
                finally:
                    after_name = "%s.%s" % (tracker.name, tracker.group)
                    if before_name == after_name and detect_name:
                        tracker.set_tracker_name(name, priority=2)

        return FunctionWrapper(wrapped, wrapper)

    for wrapped in middleware:
        yield wrapper(wrapped)


def middleware_wrapper_intermediary(handler, *args, **kwargs):
    """Avoiding two threads deal it in same time
    :param handler: the base handler of http
    :return:
    """
    global middleware_detected_lock
    if not middleware_detected_lock:
        return

    lock = middleware_detected_lock
    lock.acquire()
    if not middleware_detected_lock:
        lock.release()
        return

    middleware_detected_lock = None
    try:
        # for inserting RUM header and footer. indicate it's wrapped and timed as well
        if hasattr(handler, '_response_middleware'):
            pass

        if hasattr(handler, '_request_middleware'):
            handler._request_middleware = list(_do_wrap_middleware(handler._request_middleware, True))

        if hasattr(handler, '_view_middleware'):
            handler._view_middleware = list(_do_wrap_middleware(handler._view_middleware, True))

        if hasattr(handler, '_template_response_middleware'):
            handler._template_response_middleware = list(_do_wrap_middleware(handler._template_response_middleware))

        if hasattr(handler, '_response_middleware'):
            handler._response_middleware = list(_do_wrap_middleware(handler._response_middleware))

        if hasattr(handler, '_exception_middleware'):
            handler._exception_middleware = list(_do_wrap_middleware(handler._exception_middleware))
    finally:
        lock.release()


def middleware_wrapper(wrapped, wrapper_function):
    """
    :return:
    """
    def dynamic_wrapper(wrapped, instance, args, kwargs):
        """
        """
        result = wrapped(*args, **kwargs)

        if instance is not None:
            wrapper_function(instance, *args, **kwargs)
        else:
            wrapper_function(*args, **kwargs)
        return result

    return FunctionWrapper(wrapped, dynamic_wrapper)


def trace_middleware_wrapper(module, object_path):
    """embed the middleware tracker to the django middleware
    :param module:
    :param object_path:
    :return:
    """
    return wrap_object(module, object_path, middleware_wrapper, (middleware_wrapper_intermediary,))


def trace_view_dispatch(module, object_path):
    """django view dispatch trace entrance.
    :param module:
    :param object_path:
    :return:
    """
    def view_dispatch_name(instance, request, *args, **kwargs):
        """The following params in django.views.generic.base.View.dispatch
        :param instance:
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        if request.method.lower() in instance.http_method_names:
            handler = getattr(instance, request.method.lower(), instance.http_method_not_allowed)
        else:
            handler = instance.http_method_not_allowed

        name = callable_name(handler)
        return name

    return wrap_function_trace(module, object_path, name=view_dispatch_name)


def trace_template_block_render(module, object_path):
    """ wrap the django template load tags times.
    :param module:
    :param object_path:
    :return:
    """
    def block_name(instance, *args, **kwargs):
        """ The following params in django.template.loader_tags.BlockNode.render
        :param instance:
        :param args:
        :param kwargs:
        :return:
        """
        return instance.name or "default-template"

    return wrap_function_trace(module, object_path, name=block_name, group='Template.Block')


def trace_django_template(module, object_path):
    """
    :param modules:
    :param object_path:
    :return:
    """

    def template_name(instance, *args, **kwargs):
        """ The following params in django.template.base.Template._render/Template.render
        :param instance:
        :param args:
        :param kwargs:
        :return:
        """
        return instance.name or "default-template"

    return wrap_function_trace(module, object_path, name=template_name, group='Template/Render')


def wrap_view_handler(wrapped, priority=3):
    """
    :param wrapped:
    :param priority:
    :return:
    """
    # views handler maybe called twice on same ResolverMatch. so mark it
    if hasattr(wrapped, '_self_django_view_handler_wrapped'):
        return wrapped

    name = callable_name(wrapped)

    def wrapper(wrapped, instance, args, kwargs):
        tracker = current_tracker()

        if tracker is None:
            return wrapped(*args, **kwargs)

        tracker.set_tracker_name(name, priority=priority)
        with FunctionTracker(tracker, name=name):
            try:
                return wrapped(*args, **kwargs)
            except:  # Catch all
                tracker.record_exception(ignore_errors=should_ignore)
                raise

    result = FunctionWrapper(wrapped, wrapper)
    result._self_django_view_handler_wrapped = True

    return result


def trace_django_urlresolvers(wrapped):
    """
    :param wrapped:
    :return:
    """
    name = callable_name(wrapped)

    def wrapper(wrapped, instance, args, kwargs):
        tracker = current_tracker()

        if tracker is None:
            return wrapped(*args, **kwargs)

        if hasattr(tracker, '_self_django_url_resolver_wrapped'):
            return wrapped(*args, **kwargs)

        # mark the top level(views maybe has inline local url resolver operate) url resolver. and use it as the
        tracker._self_django_url_resolver_wrapped = True

        def _wrapped(path):
            with FunctionTracker(tracker, name=name, label=path):
                result = wrapped(path)

                if isinstance(type(result), tuple):
                    callback, callback_args, callback_kwargs = result
                    result = (wrap_view_handler(callback, priority=4), callback_args, callback_kwargs)
                else:
                    result.func = wrap_view_handler(result.func, priority=4)

                return result

        try:
            return _wrapped(*args, **kwargs)
        finally:
            del tracker._self_django_url_resolver_wrapped

    return FunctionWrapper(wrapped, wrapper)


def trace_urlresolvers_resolve_xxx(wrapped, priority):
    """
    :param wrapped:
    :param priority:
    :return:
    """
    name = callable_name(wrapped)

    def wrapper(wrapped, instance, args, kwargs):
        tracker = current_tracker()

        if tracker is None:
            return wrapped(*args, **kwargs)

        with FunctionTracker(tracker, name=name):
            callback, param_dict = wrapped(*args, **kwargs)
            return wrap_view_handler(callback, priority=priority), param_dict

    return FunctionWrapper(wrapped, wrapper)


def uncaught_exception_wrapper(wrapped):
    """
    :param wrapped:
    :return:
    """
    def wrapper(wrapped, instance, args, kwargs):
        name = callable_name(wrapped)
        tracker = current_tracker()

        if tracker is None:
            return wrapped(*args, **kwargs)

        def _wrapped(request, resolver, exc_info):
            tracker.set_tracker_name(name, priority=1)
            tracker.record_exception(*exc_info)

            try:
                return wrapped(request, resolver, exc_info)
            except:  # Catch all
                tracker.record_exception(*sys.exc_info())
                raise

        with FunctionTracker(tracker, name=name):
            return _wrapped(*args, **kwargs)

    return FunctionWrapper(wrapped, wrapper)


def trace_uncaught_exception(module, object_path):
    """
    :param module:
    :param object_path:
    :return:
    """
    return wrap_object(module, object_path, uncaught_exception_wrapper)
