from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from test.elements.elem_c import elem_c


class DoAB(elem_c.C):
  def __init__(self, a, b):
    self._a = a
    self._b = b

  def do_c(self):
    print("DoAB:", flush=True)
    self._a.do_a()
    self._b.do_b()
