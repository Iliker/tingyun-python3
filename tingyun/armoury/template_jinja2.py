
"""Define this module for basic armory for detect jinja2

"""

from tingyun.armoury.ammunition.function_tracker import wrap_function_trace


def detect_template_loader(module):
    """
    :param module:
    :return:
    """
    if hasattr(module, 'BaseLoader.load'):
        wrap_function_trace(module, 'BaseLoader.load')


def detect_jinja2(module):
    """
    """
    def parse_tempate_name(instance, *args, **kwargs):
        return instance.name or instance.filename

    wrap_function_trace(module, 'Template.render', parse_tempate_name, 'Template.Render')

    def parse_template_for_env(instance, source, name=None, *args, **kwargs):
        """
        :param instance:
        :param args:
        :param kwargs:
        :return:
        """
        return name or 'template'

    wrap_function_trace(module, 'Environment.compile', parse_template_for_env, 'Template.compile')
