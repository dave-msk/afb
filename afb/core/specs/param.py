from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import warnings

import deprecated as dp

from afb.core.specs import type_
from afb.utils import errors


class ParameterSpec(object):
  def __init__(self, type, description="", required=True, forced=None):
    self._type_spec = type_.TypeSpec.create(type)
    self._description = description

    if forced is not None:
      warnings.warn(
          "The parameter `forced` is deprecated. Use `required` instead.")
      self._required = bool(forced)
    else:
      self._required = required

  @property
  @dp.deprecated(version="1.5.0",
                 reason="Use property `required` instead.")
  def forced(self):
    return self.required

  @property
  def required(self):
    return self._required

  @property
  def type(self):
    return self._type_spec

  @property
  def description(self):
    return self._description

  @classmethod
  def from_raw(cls, raw):
    if isinstance(raw, cls):
      return raw

    if not _is_param_format(raw):
      # TODO: Add deprecation warning for old format
      raw = {"type": raw}
    _validate_raw_spec(raw)
    return cls(**raw)


def _validate_raw_spec(raw_spec):
  if "type" not in raw_spec:
    raise errors.SignatureError(
        "Missing type specification `type`. Given: {}".format(raw_spec))

  if not isinstance(raw_spec.get("description", ""), str):
    raise errors.SignatureError(
        "`description` must be a string. Given: {}".format(raw_spec))
  if not isinstance(raw_spec.get("required", True), bool):
    raise errors.SignatureError(
        "`required` must be a bool. Given: {}".format(raw_spec))


def _is_param_format(spec):
  if isinstance(spec, dict):
    unknown_keys = set(spec) - {"type", "description", "required"}
    return "type" in spec and not unknown_keys
  return False
