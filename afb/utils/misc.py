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

from afb.core import manufacturer as mfr_lib
from afb.utils import keys


def create_mfr(cls, fct_fn_dict, keyword_mode=False):
  mfr = mfr_lib.Manufacturer(cls)
  mfr.register_dict(fct_fn_dict, keyword_mode=keyword_mode)
  return mfr


def create_mfr_with_static_factories(cls, fct_fn_dict, keyword_mode=False):
  class StaticManufacturer(mfr_lib.Manufacturer):
    def _init_static(self):
      super(StaticManufacturer, self)._init_static()
      for k, fn in fct_fn_dict.items():
        if keyword_mode:
          kwargs = dict(fn(), factory_type=keys.FactoryType.STATIC)
          self._register(k, **kwargs)
        else:
          self._register(k, *fn(), factory_type=keys.FactoryType.STATIC)

  return StaticManufacturer(cls)
