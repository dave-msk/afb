# Copyright 2019 Siu-Kei Muk (David). All Rights Reserved.
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

import six
from afb.manufacturer import Manufacturer


def create_mfr(cls, fct_fn_dict, keyword_mode=False):
  mfr = Manufacturer(cls)
  mfr.register_dict(fct_fn_dict, keyword_mode=keyword_mode)
  return mfr


def create_mfr_with_builtin(cls, fct_fn_dict, keyword_mode=False):
  class BuiltinManufacturer(Manufacturer):
    def _init_builtin(self):
      super(BuiltinManufacturer, self)._init_builtin()
      for k, fn in six.iteritems(fct_fn_dict):
        if keyword_mode:
          kwargs = dict(fn(), target="builtin")
          self._register(k, **kwargs)
        else:
          self._register(k, *fn(), target="builtin")

  return BuiltinManufacturer(cls)
