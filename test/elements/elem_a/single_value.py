from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from test.elements.elem_a import elem_a


class SingleValue(elem_a.A):
  def __init__(self, value):
    self._val = value

  def do_a(self):
    print("IntA - <value: %s>" % self._val, flush=True)
