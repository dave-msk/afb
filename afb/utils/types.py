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
