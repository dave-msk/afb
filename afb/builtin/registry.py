from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from afb.builtin import factories as fct


_FCTS = {
    "from_config": fct.from_config.create_from_config,
}


def get_registrants(mfr):
  regs = []
  for method, create_fn in _FCTS.items():
    regs.append(dict(method=method, **create_fn(mfr)))
  return regs
