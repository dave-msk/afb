# Copyright 2021 (David) Siu-Kei Muk. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import warnings

from afb.core.specs import type_
from afb.utils import errors
from afb.utils import validate


class ParameterSpec(object):
  def __init__(self, type, description="", required=False, forced=None):
    self._type_spec = type_.TypeSpec.parse(type)
    self._description = description
    if forced is not None:
      # TODO: Add deprecation warning. Use `required` instead
      required = forced
    self._required = required

  # TODO: Add deprecation warning. Use property `required` instead.
  @property
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

  # TODO: Add deprecation warning. Use `ParameterSpec.parse` instead.
  @classmethod
  def from_raw(cls, raw):
    return cls.parse(raw)

  @classmethod
  def parse(cls, spec):
    if isinstance(spec, cls):
      return spec

    if not _is_param_format(spec):
      # TODO: Add deprecation waring for old format
      spec = {"type": spec}
    _validate_param_spec(spec)
    return cls(**spec)


def _validate_param_spec(spec):
  assert isinstance(spec, dict)

  if "description" in spec:
    validate.validate_type(spec["description"], str, "description")
  if "required" in spec:
    validate.validate_type(spec["required"], bool, "required")
  if "forced" in spec:
    validate.validate_type(spec["forced"], bool, "forced")


def _is_param_format(spec):
  if isinstance(spec, dict):
    unknown_keys = set(spec) - {"type", "description", "required", "forced"}
    return "type" in spec and not unknown_keys
  return False
