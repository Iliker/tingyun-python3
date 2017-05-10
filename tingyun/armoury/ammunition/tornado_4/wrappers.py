# -*- coding: utf-8 -*-

import inspect

from tingyun.packages.wrapt.wrappers import wrap_object
from tingyun.packages.wrapt.wrappers import (FunctionWrapper as _FunctionWrapper, ObjectProxy as _ObjectProxy,
                                             BoundFunctionWrapper as _BoundFunctionWrapper)


class _ObjectWrapperBase(object):

    def __setattr__(self, name, value):
        if name.startswith('_nb_'):
            name = name.replace('_nb_', '_self_', 1)
            setattr(self, name, value)
        else:
            _ObjectProxy.__setattr__(self, name, value)

    def __getattr__(self, name):
        if name.startswith('_nb_'):
            name = name.replace('_nb_', '_self_', 1)
            return getattr(self, name)
        else:
            return _ObjectProxy.__getattr__(self, name)

    def __delattr__(self, name):
        if name.startswith('_nb_'):
            name = name.replace('_nb_', '_self_', 1)
            delattr(self, name)
        else:
            _ObjectProxy.__delattr__(self, name)

    @property
    def _next_object(self):
        return self.__wrapped__

    @property
    def _previous_object(self):
        try:
            return self._self_previous_object
        except AttributeError:
            self._self_previous_object = getattr(self.__wrapped__, '_previous_object', self.__wrapped__)
            return self._self_previous_object


class _NbBoundFunctionWrapper(_ObjectWrapperBase, _BoundFunctionWrapper):
    pass


class FunctionWrapper(_ObjectWrapperBase, _FunctionWrapper):
    __bound_function_wrapper__ = _NbBoundFunctionWrapper


def function_wrapper(wrapper):
    def _wrapper(wrapped, instance, args, kwargs):
        target_wrapped = args[0]
        if instance is None:
            target_wrapper = wrapper
        elif inspect.isclass(instance):
            target_wrapper = wrapper.__get__(None, instance)
        else:
            target_wrapper = wrapper.__get__(instance, type(instance))

        return FunctionWrapper(target_wrapped, target_wrapper)

    return FunctionWrapper(wrapper, _wrapper)


def wrap_function_wrapper(module, name, wrapper):
    return wrap_object(module, name, FunctionWrapper, (wrapper,))

