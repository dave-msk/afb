from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import inspect
import six


def maybe_get_cls(maybe_obj, cls):
  obj = None
  if isinstance(maybe_obj, cls):
    obj = maybe_obj
  elif (six.callable(maybe_obj) and
        len(inspect.signature(maybe_obj).parameters) == 0):
    obj = maybe_obj()

  if isinstance(obj, cls):
    return obj

  raise TypeError("A `{}` or a function that accepts nothing and "
                  "returns one is expected. Given: {}"
                  .format(cls.__name__, maybe_obj))


def is_obj_spec(x):
  if isinstance(x, dict) and len(x) == 1:
    k, v = next(six.iteritems(x))
    return isinstance(k, str) and isinstance(v, dict)
  return False


def is_type_spec(t):
  if isinstance(t, list) and len(t) == 1:
    return is_type_spec(t[0])
  if isinstance(t, dict) and len(t) == 1:
    k, v = next(six.iteritems(t))
    return is_type_spec(k) and is_type_spec(v)
  if isinstance(t, tuple):
    return all(is_type_spec(s) for s in t)
  return isinstance(t, type)
