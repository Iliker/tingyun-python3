"""This module implements functions for deriving the full name of an object.

"""

import sys
import types
import inspect
import logging
from tingyun.packages import six

console = logging.getLogger(__name__)
cached_module_name = {}


def get_module_name(target):
    module_name = None

    if hasattr(target, '__objclass__'):
        module_name = getattr(target.__objclass__, '__module__', None)

    if module_name is None:
        module_name = getattr(target, '__module__', None)

    # An exception to that is builtins or any types which are implemented in C code. For that we need to grab the module
    # name from the __class__.
    if module_name is None and hasattr(target, '__class__'):
        module_name = getattr(target.__class__, '__module__', None)

    # Finally, if the module name isn't in sys.modules, we will format it to indicate that it is a generated
    # class of some sort where a fake namespace was used. This happens for example with namedtuple classes in Python 3.
    if module_name and module_name not in sys.modules:
        module_name = '<%s>' % module_name

    if not module_name:
        module_name = '<unknown>'

    return module_name


def _object_context_py2(obj):

    cname = None
    fname = None

    if inspect.isclass(obj) or isinstance(obj, type):
        # Old and new style class types.
        cname = obj.__name__

    elif inspect.isfunction(obj):
        # Normal functions and static methods. For a static we method don't know of any way of being able to work out
        # the name of the class the static method is against.
        fname = obj.__name__

    elif inspect.ismethod(obj):
        if obj.im_self is not None:
            cname = getattr(obj.im_self, '__name__', None)
            if cname is None:
                cname = getattr(obj.im_self.__class__, '__name__')

        else:
            cname = obj.im_class.__name__

        fname = obj.__name__

    elif inspect.isbuiltin(obj):
        # Builtin function. Can also be be bound to class to create a method. Uses __self__ instead of im_self. The
        # rules around whether __self__ is an instance or a class type are strange so need to cope with both.

        if obj.__self__ is not None:
            cname = getattr(obj.__self__, '__name__', None)
            if cname is None:
                cname = getattr(obj.__self__.__class__, '__name__')

        fname = obj.__name__

    elif isinstance(obj, types.InstanceType):
        fname = getattr(obj, '__name__', None)
        if fname is None:
            cname = obj.__class__.__name__

    elif hasattr(obj, '__class__'):

        fname = getattr(obj, '__name__', None)
        if fname is not None:
            if hasattr(obj, '__objclass__'):
                cname = obj.__objclass__.__name__
            elif not hasattr(obj, '__get__'):
                cname = obj.__class__.__name__
        else:
            cname = obj.__class__.__name__

    path = ''
    if cname:
        path = cname

    if fname:
        if path:
            path += '.'
        path += fname

    module_name = get_module_name(obj)

    return module_name, path


def _object_context_py3(obj):
    # functions and methods the __qualname__ attribute gives the name.
    path = getattr(obj, '__qualname__', None)

    # If there is no __qualname__ it maybe mean it is a type object of some sort.
    if path is None and hasattr(obj, '__class__'):
        path = getattr(obj.__class__, '__qualname__')

    module_name = get_module_name(obj)

    return module_name, path


def object_context(target):
    """Returns a tuple identifying the supplied object. This will be of
    the form (module, object_path).

    """
    cache_key = str(target)
    if cache_key in cached_module_name:
        return cached_module_name[cache_key]

    if six.PY3:
        details = _object_context_py3(target)
    else:
        details = _object_context_py2(target)

    if str(target) not in cached_module_name:
        cached_module_name[str(target)] = details

    return details


def callable_name(obj, separator=':'):
    """Returns a string name identifying the supplied object. the form is 'module:object_path'.

    If object were a function, then the name would be 'module:function.
    If a class, 'module:class'.
    If a member function, 'module:class.function'.
    """
    context = object_context(obj)

    return separator.join(context)
