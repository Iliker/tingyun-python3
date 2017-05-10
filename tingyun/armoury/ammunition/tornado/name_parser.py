# -*- coding: utf-8 -*-

"""该模块用于解析对象的名称
"""

import sys
import types
import inspect
import functools

from tingyun.packages import six


def parse_module_name(obj):
    module_name = None

    if hasattr(obj, '__objclass__'):
        module_name = getattr(obj.__objclass__, '__module__', None)

    if module_name is None:
        module_name = getattr(obj, '__module__', None)

    if module_name is None:
        self = getattr(obj, '__self__', None)
        if self is not None and hasattr(self, '__class__'):
            module_name = getattr(self.__class__, '__module__', None)

    if module_name is None and hasattr(obj, '__class__'):
        module_name = getattr(obj.__class__, '__module__', None)

    if module_name and module_name not in sys.modules:
        module_name = '<%s>' % module_name

    if not module_name:
        module_name = '<unknown>'

    return module_name


def _object_context_py2(obj):
    class_name = None
    func_name = None

    if inspect.isclass(obj) or isinstance(obj, type):
        class_name = obj.__name__

    elif inspect.ismethod(obj):
        if obj.im_self is not None:
            class_name = getattr(obj.im_self, '__name__', None)
            if class_name is None:
                class_name = getattr(obj.im_self.__class__, '__name__')

        else:
            class_name = obj.im_class.__name__

        func_name = obj.__name__

    elif inspect.isfunction(obj):
        func_name = obj.__name__

    elif inspect.isbuiltin(obj):
        if obj.__self__ is not None:
            class_name = getattr(obj.__self__, '__name__', None) or getattr(obj.__self__.__class__, '__name__')

        func_name = obj.__name__

    elif isinstance(obj, types.InstanceType):
        func_name = getattr(obj, '__name__', None)

        if func_name is None:
            class_name = obj.__class__.__name__

    elif hasattr(obj, '__class__'):
        func_name = getattr(obj, '__name__', None)

        if func_name:
            if hasattr(obj, '__objclass__'):
                class_name = obj.__objclass__.__name__
            elif not hasattr(obj, '__get__'):
                class_name = obj.__class__.__name__
        else:
            class_name = obj.__class__.__name__

    path = class_name if class_name else ''
    if func_name:
        if path:
            path += '.'
        path += func_name

    owner = ''
    if inspect.ismethod(obj):
        if obj.__self__ is not None:
            class_name = getattr(obj.__self__, '__name__', None)
            if class_name is None:
                owner = obj.__self__.__class__  # bound method
            else:
                owner = obj.__self__  # class method
        else:
            owner = getattr(obj, 'im_class', None)  # unbound method

    module_name = parse_module_name(owner or obj)

    return module_name, path


def object_context(target):
    """
    :param target: 目标对象
    :return: (module, object_path)
    """

    # 对象被 functools.partial 打包
    if isinstance(target, functools.partial):
        target = target.func

    target_name = getattr(target, '_nb_object_name', None)
    if target_name:
        return target_name

    org_object = getattr(target, '_previous_object', None)
    if org_object:
        target_name = getattr(org_object, '_nb_object_name', None)

        if target_name:
            return target_name
    else:
        org_object = target

    # 没有被缓存，重新计算, 暂未考虑py3
    target_name = _object_context_py2(org_object)

    try:
        # 缓存当前名称
        if target is not org_object:
            target._nb_object_name = target_name

        org_object._nb_object_name = target_name
    except Exception as _:
        pass

    return target_name


def object_name(obj, separator=':'):
    """
    :param obj:
    :param separator:
    :return: module:object_path
    """
    return separator.join(object_context(obj))
