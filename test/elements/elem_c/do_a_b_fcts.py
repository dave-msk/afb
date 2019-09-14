from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from test.elements.elem_a import elem_a
from test.elements.elem_b import elem_b
from test.elements.elem_c import do_a_b


def get_do_a_b():
  desc = {
      "short": "Caches A and B, and call `do_a()` and `do_b()` respectively.",
      "long":
          """This object first calls `a.do_a()` followed by `b.do_b()`.""",
  }

  sig = {
      "a": {
          "type": elem_a.A,
          "description": "An instance of A to be called `do_a()` on.",
      },
      "b": {
          "type": elem_b.B,
          "description": "An instance of B to be called `do_b()` on.",
      },
  }

  return {"factory": do_a_b.DoAB, "sig": sig, "descriptions": desc}
