from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from afb.utils import const


class ObjectSpec(object):
  def __init__(self, raw, key, inputs):
    self._raw = raw
    self._key = key
    self._inputs = inputs

  @property
  def raw(self):
    return self._raw

  @property
  def key(self):
    return self._key

  @property
  def inputs(self):
    return self._inputs

  def as_dict(self):
    return {const.KEY: self._key, const.INPUTS: self._inputs}

  @classmethod
  def parse(cls, spec):
    if isinstance(spec, cls):
      return spec
    if not is_object_spec(spec):
      # TODO: Define parse error and raise here
      raise TypeError()
    if len(spec) == 2:
      return cls(spec, **spec)
    return cls(spec, *next(iter(spec.items())))


def is_direct_object(obj, cls):
  if obj is None: return True
  if not isinstance(obj, cls): return False
  if cls is not dict: return True
  return not is_object_spec(obj)


def is_object_spec(obj):
  """Shallow format check"""
  if isinstance(obj, ObjectSpec): return True
  if not isinstance(obj, dict): return False
  l = len(obj)
  if l not in (1, 2): return False
  if l == 1: return isinstance(next(iter(obj)), str)
  return set(obj) == const.KEY_INPUTS
