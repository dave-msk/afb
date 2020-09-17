# Copyright 2020 (David) Siu-Kei Muk. All Rights Reserved.
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


def maybe_get_cls(maybe_obj, cls):
  obj = None
  if isinstance(maybe_obj, cls):
    obj = maybe_obj
  elif (callable(maybe_obj) and
        len(inspect.signature(maybe_obj).parameters) == 0):
    obj = maybe_obj()

  if isinstance(obj, cls):
    return obj

  raise TypeError("A `{}` or a zero-argument function that returns one is "
                  "expected. Given: {}".format(cls.__name__, maybe_obj))


def is_obj_spec(x):
  if isinstance(x, dict) and len(x) == 1:
    k, v = next(iter(x.items()))
    return isinstance(k, str) and isinstance(v, dict)
  return False


def is_type_spec(t):
  if isinstance(t, list) and len(t) == 1:
    return is_type_spec(t[0])
  if isinstance(t, dict) and len(t) == 1:
    k, v = next(iter(t.items()))
    return is_type_spec(k) and is_type_spec(v)
  if isinstance(t, tuple):
    return all(is_type_spec(s) for s in t)
  return isinstance(t, type)
