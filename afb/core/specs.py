from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from afb.utils import errors


class ParameterSpec(object):
  def __init__(self, type, description="", forced=False):
    errors.validate_type_spec(type)
    self._tspec = type
    self._description = description
    self._forced = forced

  @property
  def forced(self):
    return self._forced

  @property
  def details(self):
    return {"type": self._tspec, "description": self._description}

  @classmethod
  def from_raw_spec(cls, param_or_type_spec):
    param = param_or_type_spec
    if not _is_param_format(param):
      param = {"type": param}
    return cls(**param)


def _is_param_format(spec):
  if isinstance(spec, dict):
    unknown_keys = set(spec) - {"type", "description", "forced"}
    return "type" in spec and not unknown_keys
  return False
