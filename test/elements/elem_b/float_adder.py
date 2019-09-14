from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from test.elements.elem_b import elem_b


class FloatAdderB(elem_b.B):
  def __init__(self, v1, v2):
    self._v1 = v1
    self._v2 = v2

  def do_b(self):
    print("FloatAdderB: %s + %s = %s" %
          (self._v1, self._v2, self._v1 + self._v2),
          flush=True)
