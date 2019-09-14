from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from test.elements.elem_a import single_value


def get_single_value():
  desc = {
      "short": "Caches a single float value.",
      "long":
          """Prints the cached float value.""",
  }

  sig = {
      "value": {
          "type": float,
          "description": "Value to be cached.",
      },
  }

  return {"factory": single_value.SingleValue,
          "sig": sig,
          "descriptions": desc}
