from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
import inspect
import os.path
import sys

from afb.utils import const
from afb.utils import errors
from afb.utils import misc

_PY_VERSION = (sys.version_info.major, sys.version_info.minor)


class IterDfsOp(object):
  def __init__(self, proc_fn):
    self._proc_fn = proc_fn

  def __call__(self, seed):
    stack = [(lambda *x: x[0], iter((seed,)), [])]
    result = None

    while stack:
      fuse_fn, it, cache = stack[-1]

      try:
        item = next(it)
      except StopIteration:
        stack.pop()
        result = fuse_fn(*cache)
        if stack:
          stack[-1][-1].append(result)
        continue

      cache_item, stack_item = self._proc_fn(item)
      if cache_item is not misc.NONE:
        cache.append(cache_item)
      if isinstance(stack_item, tuple) and len(stack_item) == 2:
        fuse_fn, it = stack_item
        stack.append((fuse_fn, it, []))

    return result


class FuseFnCallConf(object):
  def __init__(self, fn, *args):
    self._fn = fn
    self.args = args

  def call(self):
    return self(*self.args)

  def __call__(self, *args):
    return self._fn(*args)

  @classmethod
  def partial(cls, fn):
    return lambda *args: cls(fn, *args)


def varargs_to_kwargs(*args):
  if len(args) & 1:
    raise ValueError()
  return {args[i << 1]: args[(i << 1) + 1] for i in range(len(args) // 2)}


FnArgSpec = collections.namedtuple(
    "FnArgSpec", ["required", "optional", "parameters", "kwargs"])

if _PY_VERSION == (2, 7):
  def _from_fn(fn):
    spec = inspect.getargspec(fn)
    num_defaults = len(spec.defaults)
    return FnArgSpec(required=spec.args[-num_defaults],
                     optional=spec.args[-num_defaults:],
                     parameters=spec.args,
                     kwargs=spec.keywords is not None)
elif _PY_VERSION >= (3, 5):
  def _from_fn(fn):
    sig = inspect.signature(fn)
    rqd, opt = [], []
    kw = False
    for k, p in sig.parameters.items():
      if p.kind == inspect.Parameter.POSITIONAL_ONLY:
        raise errors.SignatureError(
            "Positional-only parameter is not supported.")
      elif p.kind == inspect.Parameter.VAR_POSITIONAL:
        continue
      elif p.kind == inspect.Parameter.VAR_KEYWORD:
        kw = True
      else:
        [opt, rqd][p.default == inspect.Parameter.empty].append(k)
    return FnArgSpec(required=rqd, optional=opt, parameters=rqd+opt, kwargs=kw)
else:
  raise NotImplementedError("Unsupported Python version: %s.%s" % _PY_VERSION)


FnArgSpec.from_fn = _from_fn


def maybe_call(obj_or_fn, cls):
  obj = obj_or_fn
  if (not isinstance(obj_or_fn, cls) and
      callable(obj_or_fn) and
      len(_from_fn(obj_or_fn).parameters) == 0):
    obj = obj()

  if isinstance(obj, cls):
    return obj

  raise TypeError(
      "A `{}` or a zero-argument function that returns an instance "
      "of it is expected. Given: {}".format(misc.cls_fullname(cls), obj_or_fn))


def call_from_file(depth=0):
  f = inspect.currentframe().f_back
  for _ in range(depth):
    parent = f.f_back
    if parent is None: break
    f = parent
  return os.path.abspath(f.f_code.co_filename)


def is_called_internally(depth=1):
  call_file = call_from_file(depth=depth)
  return (call_file.startswith(const.AFB_ROOT) and
          call_file[len(const.AFB_ROOT)] == os.path.sep)
