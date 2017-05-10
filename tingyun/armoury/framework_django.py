
"""Define this module for basic armory for django

"""
from tingyun.armoury.trigger.wsgi_entrance import wsgi_application_wrapper
from tingyun.armoury.ammunition.django_tracker import trace_middleware_wrapper, trace_view_dispatch
from tingyun.armoury.ammunition.django_tracker import trace_template_block_render, trace_django_template
from tingyun.armoury.ammunition.django_tracker import should_ignore, trace_django_urlresolvers
from tingyun.armoury.ammunition.django_tracker import trace_urlresolvers_resolve_xxx, trace_uncaught_exception
from tingyun.armoury.ammunition.function_tracker import wrap_function_trace
from tingyun.armoury.ammunition.error_tracker import wrap_error_trace


# Wrap the WSGI application entry point for django.
def detect_wsgi_entrance(module):
    import django

    framework = 'Django'
    version = django.get_version()

    wsgi_application_wrapper(module.WSGIHandler, "__call__", (framework, version))
    trace_uncaught_exception(module.WSGIHandler, "handle_uncaught_exception")


# Post import hooks for modules.
def detect_middleware(module):
    """process the http/response middleware
    :param module: the module need to detect
    :return:
    """
    trace_middleware_wrapper(module, 'BaseHandler.load_middleware')


def detect_views_dispatch(module):
    """process the views info
    :param module: the views module
    :return:
    """
    trace_view_dispatch(module, "View.dispatch")


def detect_urlresolvers(module):
    """process the url
    :param module:
    :return:
    """
    # for grab the resolver map error. detect the function name mapping to views, this is base call for resolver
    wrap_error_trace(module, 'get_callable', ignore_errors=should_ignore)

    # wrap the regex url mapping to views. get_callable is used inline
    module.RegexURLResolver.resolve = trace_django_urlresolvers(module.RegexURLResolver.resolve)

    if hasattr(module.RegexURLResolver, 'resolve403'):
        module.RegexURLResolver.resolve403 = trace_urlresolvers_resolve_xxx(module.RegexURLResolver.resolve403, priority=3)

    if hasattr(module.RegexURLResolver, 'resolve404'):
        module.RegexURLResolver.resolve404 = trace_urlresolvers_resolve_xxx(module.RegexURLResolver.resolve404, priority=3)

    if hasattr(module.RegexURLResolver, 'resolve500'):
        module.RegexURLResolver.resolve500 = trace_urlresolvers_resolve_xxx(module.RegexURLResolver.resolve500, priority=1)


def detect_template_block_render(module):
    """
    :param module:
    :return:
    """
    trace_template_block_render(module, "BlockNode.render")


def detect_django_template(module):
    """ detect the template render
    :param module:
    :return:
    """
    if hasattr(module.Template, '_render'):
        trace_django_template(module, 'Template._render')

    if hasattr(module.Template, 'render'):
        trace_django_template(module, 'Template.render')


def detect_http_multipartparser(module):
    """ detect for file upload
    :param module:
    :return:
    """
    wrap_function_trace(module, 'MultiPartParser.parse')


def detect_core_mail(module):
    """
    :param module:
    :return:
    """
    wrap_function_trace(module, 'mail_admins')
    wrap_function_trace(module, 'mail_managers')
    wrap_function_trace(module, 'send_mail')


def detect_core_mail_message(module):
    """
    :param module:
    :return:
    """
    wrap_function_trace(module, 'EmailMessage.send')
