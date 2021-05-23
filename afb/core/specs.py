# Copyright 2020 Siu-Kei Muk (David). All Rights Reserved.
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

from afb.utils import errors


class ParameterSpec(object):
  def __init__(self, type, description="", required=False):
    errors.validate_type_spec(type)
    self._type_spec = type
    self._description = description
    self._required = required

  @property
  def required(self):
    return self._required

  @property
  def details(self):
    return {"type": self._type_spec, "description": self._description}

  @classmethod
  def from_raw_spec(cls, param_or_type_spec):
    spec = param_or_type_spec
    if not _is_param_format(spec):
      spec = {"type": spec}
    _validate_raw_spec(spec)
    return cls(**spec)


def create_param_spec(maybe_raw_spec):
  if isinstance(maybe_raw_spec, ParameterSpec):
    return maybe_raw_spec
  return ParameterSpec.from_raw_spec(maybe_raw_spec)


def _is_param_format(spec):
  if isinstance(spec, dict):
    unknown_keys = set(spec) - {"type", "description", "required"}
    return "type" in spec and not unknown_keys
  return False
