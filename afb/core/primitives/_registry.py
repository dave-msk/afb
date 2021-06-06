from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from afb.core import manufacturer
from afb.core.primitives import dict_lib
from afb.utils import keys

_REGISTRY = {
    bool: {},
    complex: {},
    dict: dict_lib.FACTORIES,
    float: {},
    int: {},
    list: {},
    str: {},
    tuple: {},
}


class _PrimitiveManufacturer(manufacturer.Manufacturer):
  def __init__(self, cls):
    if cls not in _REGISTRY:
      raise ValueError()
    super(_PrimitiveManufacturer, self).__init__(cls)

  def _install_builtins(self):
    super(_PrimitiveManufacturer, self)._install_builtins()
    for k, f in _REGISTRY[self._cls].items():
      self._register(keys.join_reserved(k), **f())


def is_supported(cls):
  return cls in _REGISTRY


def create_mfr(cls):
  assert is_supported(cls)
  return _PrimitiveManufacturer(cls)
