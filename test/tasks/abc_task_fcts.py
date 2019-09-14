from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from test.elements import elem_a
from test.elements import elem_b
from test.elements import elem_c
from test.tasks import abc_task


def get_abc_task():
  desc = {
      "short": "Prints input arguments and calls `do_a`, `do_b` & `do_c`.",
      "long":
          """The input arguments are first printed out, followed by called to
          `a.do_a()`, `b.do_b()` and `c.do_c()` on the given `a`, `b` & `c`
          objects.
          """,
  }

  sig = {
      "a": {
          "type": elem_a.A,
          "description": "An instance of A for `do_a()` call.",
      },
      "b": {
          "type": elem_b.B,
          "description": "An instance of B for `do_b()` call.",
      },
      "c": {
          "type": elem_c.C,
          "description": "An instance of C for `do_c()` call.",
      },
  }

  return {"factory": abc_task.ABCTask, "sig": sig, "descriptions": desc}
