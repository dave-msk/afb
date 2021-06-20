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

import functools

from afb.utils import errors
from afb.utils import fn_util


class LazyProperty(object):
  """
  TODO: Add descriptions
  """
  def __init__(self, function):
    self.function = function
    self.name = function.__name__

  def __get__(self, obj, type=None):
    obj.__dict__[self.name] = self.function(obj)
    return obj.__dict__[self.name]


def restricted(msg=None):
  def decorator(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
      if not fn_util.is_called_internally(depth=2):
        raise errors.RestrictedAccessError(msg or "")
      return func(*args, **kwargs)
    return wrapped
  return decorator


class With(object):
  def __init__(self,
               ctx,
               ctx_from_attr=False,
               call=False,
               call_args=None,
               attr_call_args=None,
               as_=None):
    self._ctx = ctx
    self._call = call
    self._as = as_
    self._call_args = call_args or {}
    self._attr_call_args = attr_call_args or {}
    self._ctx_from_attr = ctx_from_attr

  def __call__(self, func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
      ctx_mgr = (getattr(args[0], self._ctx)
                 if self._ctx_from_attr
                 else self._ctx)
      if self._call:
        ctx_args = dict(self._call_args)
        ctx_args.update({k: getattr(args[0], v)
                         for k, v in self._attr_call_args.items()})
        ctx_mgr = ctx_mgr(**ctx_args)
      with ctx_mgr as ctx:
        if self._as:
          kwargs[self._as] = ctx
        return func(*args, **kwargs)

    return wrapped
