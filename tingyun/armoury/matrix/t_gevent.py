"""Define this module for basic armory for gevent

"""

from tingyun.armoury.trigger.wsgi_entrance import wsgi_app_wrapper_entrance
from tingyun.logistics.basic_wrapper import trace_in_function


def trace_wsgi_server(*args, **kwargs):
    def instance_parameters(instance, listener, application, *args, **kwargs):
        return instance, listener, application, args, kwargs

    self, listener, application, _args, _kwargs = instance_parameters(*args, **kwargs)

    application = wsgi_app_wrapper_entrance(application)

    _args = (self, listener, application) + _args

    return _args, _kwargs


def detect_pywsgi(module):
    """
    """
    trace_in_function(module, 'WSGIServer.__init__', trace_wsgi_server)


# this module will be deprecated after gevent v1.0.3
def detect_wsgi(module):
    """
    """
    trace_in_function(module, 'WSGIServer.__init__', trace_wsgi_server)
