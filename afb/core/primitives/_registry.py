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

from afb.core import manufacturer
from afb.core.primitives import dict_lib
from afb.utils import misc

_REGISTRY = {
    bool: {},
    complex: {},
    dict: dict_lib.FACTORIES,
    float: {},
    int: {},
    list: {},
    str: {},
    tuple: {},
}


class _PrimitiveManufacturer(manufacturer.Manufacturer):
  def __init__(self, cls):
    if cls not in _REGISTRY:
      raise ValueError()
    super(_PrimitiveManufacturer, self).__init__(cls)

  def _install_builtins(self):
    super(_PrimitiveManufacturer, self)._install_builtins()
    for k, f in _REGISTRY[self._cls].items():
      self._register(misc.join_reserved(k), **f())


def is_supported(cls):
  return cls in _REGISTRY


def create_mfr(cls):
  assert is_supported(cls)
  return _PrimitiveManufacturer(cls)


def create_missing_mfrs(classes):
  return [_PrimitiveManufacturer(cls)
          for cls in _REGISTRY if cls not in classes]
