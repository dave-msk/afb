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

from afb.core.primitives.factories import dict_lib
from afb.utils import misc


_STATIC_FACTORIES = {
    bool: {},
    dict: {
        "load_config": dict_lib.get_load_config,
    },
    float: {},
    int: {},
    list: {},
    str: {},
    tuple: {},
}


def make_primitive_mfrs():
  return [misc.create_mfr_with_static_factories(cls, cls_reg, keyword_mode=True)
          for cls, cls_reg in _STATIC_FACTORIES.items()]
