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

from afb.ext.app.values import values as val_lib
from afb.utils import specs


def make_enum_values(type_spec):
  spec_repr = specs.type_spec_repr(type_spec)

  desc = {
      "short": "`{}` values provided by user".format(spec_repr),
      "long":
          """Iterates through the `{}` values provided by user."""
          .format(spec_repr),
  }

  sig = {
      "values": {
          "type": [type_spec],
          "description": "Values to be iterated over. (`{}`)".format(spec_repr),
      },
  }

  def get_enum_values():
    return {"factory": EnumValues, "sig": sig, "descriptions": desc}

  return get_enum_values


class EnumValues(val_lib.Values):
  def __init__(self, values):
    self._values = values

  def _make_iterator(self):
    for v in self._values: yield v
