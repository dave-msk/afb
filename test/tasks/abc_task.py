from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import pprint

import afb


class ABCTask(afb.app.Task):
  def __init__(self, a, b, c):
    super(ABCTask, self).__init__("Trivial ABC Task")
    self._a = a
    self._b = b
    self._c = c

  def _run(self, *args, **kwargs):
    pp = pprint.PrettyPrinter(indent=2)
    print("=" * 80)
    print("args:")
    pp.pprint(args)
    print()
    print("kwargs:")
    pp.pprint({k: kwargs[k] for k in sorted(kwargs)})

    print()
    print("A.do_a():")
    self._a.do_a()
    print()
    print("B.do_b():")
    self._b.do_b()
    print()
    print("C.do_c():")
    self._c.do_c()
    print(flush=True)
