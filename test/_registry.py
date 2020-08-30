from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import afb

from test import tasks
from test.elements import elem_a
from test.elements import elem_b
from test.elements import elem_c


_REGISTRY = {
    elem_a.A: {
        "single_value": elem_a.get_single_value,
    },
    elem_b.B: {
        "float_adder": elem_b.get_float_adder_b,
    },
    elem_c.C: {
        "do_a_b": elem_c.get_do_a_b,
    },
    afb.app.Task: {
        "abc_task": tasks.get_abc_task,
    },
}


def make_broker():
  broker = afb.Broker()
  for cls, reg in _REGISTRY.items():
    [broker.add_factory(cls, k, **fn()) for k, fn in reg.items()]
  return broker
