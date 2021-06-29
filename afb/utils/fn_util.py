# Copyright 2021 (David) Siu-Kei Muk. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
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


class PostorderDFS(object):
  def __init__(self, proc_fn):
    self._proc_fn = proc_fn

  def __call__(self, seed):
    stack = collections.deque()
    stack.append(PostorderDFSNode(lambda *x: x[0], (seed,)))
    result = None

    while stack:
      node = stack[-1]

      try:
        item = node.next()
      except StopIteration:
        stack.pop()
        result = node.fuse()
        if stack:
          stack[-1].add_fuse_item(result)
        continue

      proc_result = self._proc_fn(item)
      if proc_result.has_item():
        node.add_fuse_item(proc_result.item)
      if proc_result.node:
        stack.append(proc_result.node)

    return result


class PostorderDFSNode(object):
  def __init__(self, fuse_fn, items):
    self._fuse = fuse_fn
    self._items = items if hasattr(items, "__next__") else iter(items)
    self._fuse_items = []

  def next(self):
    return next(self._items)

  def add_fuse_item(self, item):
    self._fuse_items.append(item)

  def fuse(self):
    return self._fuse(*self._fuse_items)


class ProcResult(object):
  def __init__(self, item=misc.NONE, node=None):
    self._item = item
    self._node = node

  def has_item(self):
    return self._item is not misc.NONE

  @property
  def item(self):
    return self._item

  @property
  def node(self):
    return self._node


class ItemResult(ProcResult):
  def __init__(self, item):
    super(ItemResult, self).__init__(item=item)


class NodeResult(ProcResult):
  def __init__(self, fuse_fn, items):
    super(NodeResult, self).__init__(node=PostorderDFSNode(fuse_fn, items))


class FuseCallInfo(object):
  def __init__(self, fn, *args):
    self._fn = fn
    self.args = args

  def __call__(self, *args):
    return self._fn(*args)

  @classmethod
  def partial(cls, fn):
    return lambda *args: cls(fn, *args)


def varargs_to_kwargs(*args):
  if len(args) & 1:
    raise errors.ArgumentError("Number of inputs must be even. Given: {}"
                               .format(len(args)))
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
      "of it is expected. Given: {}".format(misc.qualname(cls), obj_or_fn))


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
