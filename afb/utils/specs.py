# Copyright 2020 (David) Siu-Kei Muk. All Rights Reserved.
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


def type_spec_repr(type_spec):
  errors.validate_type_spec(type_spec)
  if isinstance(type_spec, list):
    return "[{}]".format(type_spec_repr(type_spec[0]))
  elif isinstance(type_spec, dict):
    k, v = next(iter(type_spec.items()))
    return "{%s: %s}" % (type_spec_repr(k), type_spec_repr(v))
  elif isinstance(type_spec, tuple):
    return "({})".format(", ".join(type_spec))
  # Here, `type_spec` has to be a type, otherwise an exception
  # would have been thrown in the initialize validation.
  return type_spec.__name__
