from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


class B(object):
  def do_b(self):
    raise NotImplementedError("Must be implemented in descendants.")
