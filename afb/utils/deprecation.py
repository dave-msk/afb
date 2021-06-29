from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import functools
import inspect
import warnings

from afb.utils import misc

_PRINTED_WARNING_LOCATIONS = set()


def handle_renamed_arg(arg_name, arg, old_name, old_arg):
  if old_arg is not None:
    warnings.warn("Parameter `{}` is deprecated. Use `{}` instead."
                  .format(old_name, arg_name),
                  category=DeprecationWarning,
                  stacklevel=3)
    arg = old_arg
  return arg


def warn(message, **kwargs):
  kwargs["category"] = DeprecationWarning
  kwargs["stacklevel"] = kwargs.get("stacklevel", 1) + 1
  call_loc = _call_location(2)
  if call_loc not in _PRINTED_WARNING_LOCATIONS:
    warnings.warn(message, **kwargs)
    _PRINTED_WARNING_LOCATIONS.add(call_loc)


def deprecated(message="",
               remove_version=None,
               stacklevel=1):
  fmt = "`{}` is deprecated and will be removed "
  if remove_version:
    fmt += "from {}.".format(remove_version)
  else:
    fmt += "in a future version."
  if message:
    fmt += " {}".format(message)

  def decorator(func):
    # TODO(david-muk): Add deprecation notes to docstring
    # TODO(david-muk): Add support for deprecated parameters
    #   1. Give warnings when used any of the deprecated elements
    #   2. Performs parameter overriding for renames
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
      warn(fmt.format(misc.qualname(func)), stacklevel=stacklevel + 1)
      return func(*args, **kwargs)
    return wrapped

  return decorator


def _call_location(stacklevel=1):
  f = inspect.currentframe()
  for _ in range(stacklevel):
    f = f.f_back
  return "{}:{}".format(f.f_code.co_filename, f.f_lineno)
