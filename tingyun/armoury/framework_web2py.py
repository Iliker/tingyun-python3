
"""define a module for detect framework web2py. only support 2.8.1 upon
"""

from tingyun.armoury.trigger.wsgi_entrance import wsgi_application_wrapper
from tingyun.armoury.ammunition.web2py_trakcer import trace_serve_controller
from tingyun.armoury.ammunition.function_tracker import wrap_function_trace


def detect_wsgi_entrance(module):
    """
    :param module:
    :return:
    """
    version = 'xx'

    try:
        import gluon.main
        version = gluon.main.web2py_version.strip()
        version = version[: 5]
    except Exception as _:
        pass

    wsgi_application_wrapper(module, 'wsgibase', ('web2py', version))
    trace_serve_controller(module, 'serve_controller')


def detect_compileapp(module):
    """
    :param module:
    :return:
    """
    def get_name_in_controller(controller, function, environment):
        """more detail in gluon.compileapp.run_controller_in
        """
        return '%s.%s' % (controller, function)

    def get_name_in_model(environment):
        """more detail in gluon.compileapp.run_model_in
        """
        return '%s.%s' % (environment['request'].controller, environment['request'].function)

    def get_name_in_view(environment):
        """more detail in gluon.compileapp.run-view-in
        """
        return '%s.%s' % (environment['request'].controller, environment['request'].function)

    wrap_function_trace(module, 'run_controller_in', get_name_in_controller, group='web2py.controllers')
    wrap_function_trace(module, 'run_models_in', get_name_in_model, group='web2py.models')
    wrap_function_trace(module, 'run_view_in', get_name_in_view, group='web2py.views')


def detect_template(module):
    """
    :param module:
    :return:
    """
    def get_template_name(filename, *args, **kwargs):
        """
        """
        return filename

    wrap_function_trace(module, 'parse_template', get_template_name, group='template.compile')
