# -*- coding: utf-8 -*-

import inspect

from tingyun.packages.wrapt.wrappers import wrap_object
from tingyun.packages.wrapt.wrappers import (FunctionWrapper as _FunctionWrapper, ObjectProxy as _ObjectProxy,
                                             BoundFunctionWrapper as _BoundFunctionWrapper)


class TingYunObjectWrapperBase(_ObjectProxy):
    """使用细则参考 http://wrapt.readthedocs.io/en/latest/
    """
    @property
    def _previous_object(self):
        """当一个对象wrapped的时候，可通过该方式判断是否需要再次wrap,同时，如果需要，也可将被wrap的对象返回
        :return:
        """
        try:
            return self._self_previous_object
        except AttributeError:
            self._self_previous_object = getattr(self.__wrapped__, '_previous_object', self.__wrapped__)
            return self._self_previous_object


# _TYBoundFunctionWrapper/FunctionWrapper/function_wrapper定义以及使用，参考wrapt原生的使用文档
# ########################################################################################
class TyBoundFunctionWrapper(TingYunObjectWrapperBase, _BoundFunctionWrapper):
    pass


class TyFunctionWrapper(TingYunObjectWrapperBase, _FunctionWrapper):
    __bound_function_wrapper__ = TyBoundFunctionWrapper


def function_wrapper(wrapper):
    def _wrapper(wrapped, instance, args, kwargs):
        target_wrapped = args[0]
        if instance is None:
            target_wrapper = wrapper
        elif inspect.isclass(instance):
            target_wrapper = wrapper.__get__(None, instance)
        else:
            target_wrapper = wrapper.__get__(instance, type(instance))

        return TyFunctionWrapper(target_wrapped, target_wrapper)

    return TyFunctionWrapper(wrapper, _wrapper)


def wrap_function_wrapper(module, name, wrapper):
    return wrap_object(module, name, TyFunctionWrapper, (wrapper,))
# ########################################################################################
