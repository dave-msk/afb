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

import inspect
import os
import sys

from afb.utils import const
from afb.utils import errors
from afb.utils import misc

_PY_VERSION = (sys.version_info.major, sys.version_info.minor)


class FnArgSpec(object):
  def __init__(self,
               required=None,
               optional=None,
               parameters=None,
               kwargs=None):
    self._required = required
    self._optional = optional
    self._parameters = parameters
    self._kwargs = kwargs

  @property
  def required(self):
    return self._required

  @property
  def optional(self):
    return self._optional

  @property
  def parameters(self):
    return self._parameters

  @property
  def kwargs(self):
    return self._kwargs

  if _PY_VERSION == (2, 7):
    @classmethod
    def parse(cls, fn):
      spec = inspect.getargspec(fn)
      num_defaults = len(spec.defaults)
      return FnArgSpec(required=spec.args[-num_defaults],
                       optional=spec.args[-num_defaults:],
                       parameters=spec.args,
                       kwargs=spec.keywords is not None)
  elif _PY_VERSION >= (3, 5):
    @classmethod
    def parse(cls, fn):
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
      return cls(required=rqd, optional=opt, parameters=rqd+opt, kwargs=kw)
  else:
    raise NotImplementedError("Unsupported Python version: %s.%s" % _PY_VERSION)


class FnCall(object):
  def __init__(self, fn, args=None, kwargs=None):
    self._fn = fn
    self._args = args or list(args)
    self._kwargs = kwargs or dict(kwargs)

  @property
  def args(self):
    return list(self._args)

  @property
  def kwargs(self):
    return dict(self._kwargs)

  def __call__(self, *args, **kwargs):
    return self._fn(*args, **kwargs)

  def eval(self):
    return self._fn(*self._args, **self._kwargs)

  @classmethod
  def stub(cls, fn):
    return lambda *args, **kwargs: cls(fn, args=args, kwargs=kwargs)


def varargs_to_kwargs(*args):
  if len(args) & 1:
    raise errors.ArgumentError(
        "Number of inputs must be even. Given: {}".format(len(args)))
  return {args[i << 1]: args[(i << 1) + 1] for i in range(len(args) // 2)}


def maybe_call(obj_or_fn, cls):
  obj = obj_or_fn
  if (not isinstance(obj_or_fn, cls) and
      callable(obj_or_fn) and
      len(FnArgSpec.parse(obj_or_fn).parameters) == 0):
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
