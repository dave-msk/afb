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

from afb.core.specs import param


class SignatureMixin(object):
  """Mixin for explicit signature retrieval of constructors with inheritance.

  This mixin provides two class methods:

    * `signature`: Gets (optionally filtered) signature
    * `_base_signature`: Defines the explicit signature of the constructor.

  The method `signature` is mainly used by the client code of the class, where
  `_base_signature` is to be defined by the class developer.

  It is common (and a good practice) to include `**kwargs` in `__init__` for any
  arguments to be forwarded directly to the super classes. However, details of
  the forwarded arguments (e.g. names) would be lost and client would have to
  climb the inheritance tree to find the details themselves.

  This mixin provides support for getting the full signature (written by the
  class developer explicitly) with a single `Class.signature` call. The class
  developer would be able to get the full signature of the parent class by the
  `super(Child, Child)._base_signature()` call, so that no duplicated definition
  is required.
  """
  @classmethod
  def signature(cls, includes=None, excludes=None):
    """Retrieves signature of the constructor.

    Args:
      includes: Set of arguments to be included. If given, the returned
        signature will contain only arguments specified by `includes`.
      excludes: Set of arguments to be excluded. If given, the returned
        signature will contain only arguments NOT specified by `excludes`.
        If both `includes` and `excludes` are present, `includes` takes
        precedence.

    Returns:
      An OrderedDict mapping parameter names to their `ParameterSpec`.
    """
    sig = cls._base_signature()
    if not isinstance(sig, collections.OrderedDict):
      sig = collections.OrderedDict(sig)

    key = None
    given = None
    try:
      if includes:
        key = "includes"
        given = includes
        excludes = [k for k in sig if k not in set(includes)]
      if excludes:
        key = "excludes"
        given = excludes
        [sig.pop(k, None) for k in excludes]
    except TypeError as e:
      if "object is not iterable" in str(e):
        raise TypeError("`{}` must be iterable. Given: {}".format(key, given))
      raise

    for k, v in sig.items():
      sig[k] = param.ParameterSpec.parse(v)

    return sig

  @classmethod
  def _base_signature(cls):
    """Returns full signature of the constructor."""
    return collections.OrderedDict()
