
"""define a hook module for framework web2py. only support 0.3
"""

import logging
from tingyun.logistics.basic_wrapper import trace_out_function
from tingyun.armoury.trigger.wsgi_entrance import wsgi_app_wrapper_entrance
from tingyun.armoury.ammunition.webpy_tracker import trace_app_views
from tingyun.armoury.ammunition.function_tracker import wrap_function_trace

console = logging.getLogger(__name__)


def detect_wsgi_entrance(module):
    """
    :param module:
    :return:
    """
    trace_out_function(module, 'application.wsgifunc', wsgi_app_wrapper_entrance)


def detect_application(module):
    """
    :param module:
    :return:
    """
    # we caught the error through try/catch in views.
    trace_app_views(module, 'application._delegate')


def detect_app_template(module):
    """
    :param module:
    :return:
    """
    def template_name(instance, name):
        """
        :param instance: the instance of the Render
        :return: the template name
        """
        return name

    wrap_function_trace(module, "Render.__getattr__", name=template_name, group='Template.Render')
    wrap_function_trace(module, "Template.compile_template", name=template_name, group='Template.compile')
