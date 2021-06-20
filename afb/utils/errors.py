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

import threading


class KeyConflictError(Exception):
  pass


class RestrictedAccessError(Exception):
  pass


class SignatureError(Exception):
  pass


class ArgumentError(Exception):
  pass


class InvalidFormatError(Exception):
  pass


class GraphError(Exception):
  pass


class _ExceptionProxyContext(object):
  def __init__(self, prefix="", suffix="", depth=0):
    self.prefix = prefix
    self.suffix = suffix
    self.depth = depth


class ExceptionProxy(object):
  def __init__(self):
    self._local = threading.local()
    self._local.stack = []

  def __enter__(self):
    assert self._local.stack

    ctx = self._local.stack[-1]
    ctx.depth += 1
    return ctx

  def __exit__(self, exc_type, exc_val, exc_tb):
    assert self._local.stack
    ctx = self._local.stack[-1]
    ctx.depth -= 1
    if ctx.depth == 0:
      self._local.stack.pop()
      if exc_val:
        exc_val = "%s%s%s" % (ctx.prefix, exc_val, ctx.suffix)

    if exc_type:
      raise exc_type(exc_val)

  def __call__(self, prefix="", suffix=""):
    if self._local.stack:
      ctx = self._local.stack[-1]
      if ctx.prefix == prefix and ctx.suffix == suffix:
        return self
    self._local.stack.append(
        _ExceptionProxyContext(prefix=prefix, suffix=suffix, depth=0))
    return self
