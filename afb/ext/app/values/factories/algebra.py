from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import copy
import itertools

from afb.ext.app.values import base as val_base


def get_zipped():
  desc = {
      "short": "",
      "long":
          """
          """,
  }

  def factory(values_map, base=None):
    return _CombinedValues(zip, values_map, base=base)

  return {"factory": factory, "sig": _CombinedValues._SIG, "descriptions": desc}  # pylint: disable=protected-access


def get_product():
  desc = {
      "short": "",
      "long":
          """
          """,
  }

  def factory(values_map, base=None):
    return _CombinedValues(itertools.product, values_map, base=base)

  return {"factory": factory, "sig": _CombinedValues._SIG, "descriptions": desc}  # pylint: disable=protected-access


class _CombinedValues(val_base.Values):
  _SIG = {
      "values_map": {
        "type": {str: val_base.Values},
        "description": "",
      },
      "base": {
        "type": dict,
        "description": "",
      },
  }

  def __init__(self, combine_fn, values_map, base=None):
    self._combine_fn = combine_fn
    self._values_map = values_map
    self._base = base or {}

  def _make_iterator(self):
    keys, vals = list(zip(*list(self._values_map.items())))
    its = [v.make_iterator() for v in vals]

    for comb in self._combine_fn(*its):
      out = copy.deepcopy(self._base)
      out.update(dict(zip(keys, comb)))
      yield out

    del its[:]
