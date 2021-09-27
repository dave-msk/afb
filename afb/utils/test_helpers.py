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


from afb.core import broker as bkr_lib
from afb.core import manufacturer as mfr_lib


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


def factory_spec(cls, key, **kwargs):
  spec = dict(FCTS[cls][key])
  kwargs.pop("factory", None)
  kwargs.pop("signature", None)
  spec.update(kwargs)

  return spec


def create_broker(*classes):
  bkr = bkr_lib.Broker()
  [bkr.register(mfr_lib.Manufacturer(cls)) for cls in classes]
  return bkr


FCTS = {
    ValueHolder: {
        "create/int": {
            "factory": ValueHolder,
            "signature": {
                "value": {
                    "type": int,
                    "description": "Integer. Value to be stored.",
                },
            },
            "defaults": None,
            "descriptions": {
                "short": "Creates ValueHolder with int value.",
                "long": "Stores an int into a ValueHolder instance.",
            }
        },
        "create/float": {
            "factory": ValueHolder,
            "signature": {
                "value": {
                    "type": float,
                    "description": "Float. Value to be stored.",
                },
            },
            "defaults": None,
            "descriptions": {
                "short": "Creates ValueHolder with float value.",
                "long": "Stores a float into a ValueHolder instance.",
            }
        },
        "sum/tuple": {
            "factory": lambda values: ValueHolder(sum(values)),
            "signature": {
                "values": {
                    "type": (int, float, int, float),
                    "description": "Tuple of (int, float, int, float)."
                },
            },
            "defaults": None,
            "descriptions": {
                "short": "Creates ValueHolder holding the sum of 4 values.",
                "long": "Stores the sum of values in a tuple with types "
                        "(int, float, int, float) into a ValueHolder instance.",
            }
        },
        "sum/list/int": {
            "factory": lambda values: ValueHolder(sum(values)),
            "signature": {
                "values": {
                    "type": [int],
                    "description": "LIst of int values.",
                },
            },
            "defaults": None,
            "descriptions": {
                "short": "Creates ValueHolder holding the num of int values.",
                "long": "Stores the sum of a list of int values into a "
                        "ValueHolder instance.",
            }
        },
        "sum/list/vh": {
            "factory": lambda vhs: ValueHolder(sum(vh.value for vh in vhs)),
            "signature": {
                "vhs": {
                    "type": [ValueHolder],
                    "description": "List of value holders.",
                },
            },
            "defaults": None,
            "descriptions": {
                "short": "Creates ValueHolder holding the sum of a list of "
                         "ValueHolder values.",
                "long": "Stores the sum of all given ValueHolder values.",
            }
        },
        "sum/key-values/vh": {
            "factory": lambda vhd:
                ValueHolder(sum(k.value + v.value for k, v in vhd.items())),
            "signature": {
                "vhd": {
                    "type": {ValueHolder: ValueHolder},
                    "description": "Dict mapping ValueHolders to ValueHolders.",
                },
            },
            "defaults": None,
            "descriptions": {
                "short": "Creates ValueHolder from key-value ValueHolder dict.",
                "long": "Stores the sum of all ValueHolders contained in the "
                        "given ValueHolder -> ValueHolder dict.",
            },
        },
    },
    Adder: {
        "create/floats": {
            "factory": Adder,
            "signature": {
                "v1": {
                    "type": float,
                    "description": "First value.",
                },
                "v2": {
                    "type": float,
                    "description": "Second value.",
                }
            },
            "defaults": None,
            "descriptions": {
                "short": "Creates Adder with two float values.",
                "long": "Store two float values into an Adder instance.",
            },
        },
        "create/vhs": {
            "factory": lambda vh1, vh2: Adder(vh1.value, vh2.value),
            "signature": {
                "vh1": {
                    "type": ValueHolder,
                    "description": "First value holder.",
                },
                "vh2": {
                    "type": ValueHolder,
                    "description": "Second holder.",
                },
            },
            "defaults": None,
            "descriptions": {
                "short": "Creates Adder with values taken from two "
                         "ValueHolders.",
                "long": "Store values from two ValueHolders into an "
                        "Adder instance.",
            },
        },
    }
}
