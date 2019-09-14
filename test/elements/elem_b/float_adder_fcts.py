from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from test.elements.elem_b import float_adder


def get_float_adder_b():
  desc = {
      "short": "Caches two floats and prints its sum.",
      "long":
          """Prints "v1 + v2 = sum".""",
  }

  sig = {
      "v1": {
          "type": float,
          "description": "First value.",
      },
      "v2": {
          "type": float,
          "description": "Second value.",
      },
  }

  return {"factory": float_adder.FloatAdderB,
          "sig": sig,
          "descriptions": desc}
