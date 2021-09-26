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


class TrivialClass(object):
  pass


class ValueHolder(object):
  def __init__(self, value):
    self._val = value

  @property
  def value(self):
    return self._val


class Adder(object):
  def __init__(self, v1, v2):
    self._v1 = v1
    self._v2 = v2

  @property
  def value(self):
    return self._v1 + self._v2


FCTS = {
    ValueHolder: {
        "create/int": (
          ValueHolder,
          {
                "value": {
                    "type": int,
                    "description": "Integer. Value to be stored.",
                },
            },
        ),
        "create/float": (
          ValueHolder,
          {
                "value": {
                    "type": float,
                    "description": "Float. Value to be stored.",
                },
            },
        ),
        "sum/tuple": (
            lambda values: ValueHolder(sum(values)),
            {
                "values": {
                    "type": (int, float, int, float),
                    "description": "Tuple of (int, float, int, float)."
                },
            },
        ),
        "sum/list/int": (
            lambda values: ValueHolder(sum(values)),
            {
                "values": {
                    "type": [int],
                    "description": "LIst of int values.",
                },
            },
        ),
        "sum/list/vh": (
            lambda vhs: ValueHolder(sum(vh.value for vh in vhs)),
            {
                "vhs": {
                    "type": [ValueHolder],
                    "description": "List of value holders.",
                },
            },
        ),
        "sum/key-values/vh": (
            lambda vhd:
                ValueHolder(sum(k.value + v.value for k, v in vhd.items())),
            {
                "vhd": {
                    "type": {ValueHolder: ValueHolder},
                    "description": "Dict mapping ValueHolders to ValueHolders.",
                },
            },
        ),
    },
    Adder: {
        "create/floats": (
          Adder,
          {
                "v1": {
                    "type": float,
                    "description": "First value.",
                },
                "v2": {
                    "type": float,
                    "description": "Second value.",
                }
            },
        ),
        "create/vhs": (
            lambda vh1, vh2: Adder(vh1.value, vh2.value),
            {
                "vh1": {
                    "type": ValueHolder,
                    "description": "First value holder.",
                },
                "vh2": {
                    "type": ValueHolder,
                    "description": "Second holder.",
                },
            },
        ),
    }
}
