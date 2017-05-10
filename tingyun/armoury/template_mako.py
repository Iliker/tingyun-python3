
"""Define this module for basic armory for detect mako

"""

from tingyun.armoury.ammunition.function_tracker import wrap_function_trace


def detect_template(module):
    """
    :param module:
    :return:
    """
    def template_name(template, text, filename, *args):
        """
        :param template:
        :param text:
        :param filename:
        :param args: compatible with _compile_text and _compile_module_file
        :return:
        """
        return filename

    def template_name_in_render(instance, *args, **kwargs):
        return getattr(instance, 'filename', "template")

    wrap_function_trace(module, '_compile_text', name=template_name, group='Template.compile')
    wrap_function_trace(module, '_compile_module_file', name=template_name, group='Template.compile')
    wrap_function_trace(module, 'Template.render', name=template_name_in_render, group='Template.render')
