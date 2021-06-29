from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import functools
import inspect
import os
import warnings

from afb.utils import const
from afb.utils import misc

_PRINTED_WARNING_LOCATIONS = set()
warnings.simplefilter("always")


def handle_renamed_arg(arg_name, arg, old_name, old_arg):
  if old_arg is not None:
    warn("Parameter `{}` is deprecated. Use `{}` instead."
         .format(old_name, arg_name),
         depth=1)
    arg = old_arg
  return arg


def warn(message, depth=0):
  call_loc = _call_location(depth + 2)
  if call_loc not in _PRINTED_WARNING_LOCATIONS:
    warnings.warn(message,
                  category=DeprecationWarning,
                  stacklevel=_outer_stack_level())
    _PRINTED_WARNING_LOCATIONS.add(call_loc)


def deprecated(message="",
               remove_version=None):
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
      warn(fmt.format(misc.qualname(func)))
      return func(*args, **kwargs)
    return wrapped

  return decorator


def _call_location(stacklevel=1):
  f = inspect.currentframe()
  for _ in range(stacklevel):
    f = f.f_back
  return "{}:{}".format(f.f_code.co_filename, f.f_lineno)


def _is_internal(file):
  path = os.path.abspath(file)
  return (path.startswith(const.AFB_ROOT) and
          path[len(const.AFB_ROOT)] == os.path.sep)


def _outer_stack_level():
  f = inspect.currentframe().f_back
  stacklevel = 1
  while f and _is_internal(f.f_code.co_filename):
    f = f.f_back
    stacklevel += 1
  return stacklevel
