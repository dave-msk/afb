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

from afb.utils import const
from afb.utils import errors


class ObjectSpec(object):
  """Class instance specification.

  This class represents an object by a factory key and inputs to be used for
  its creation. It is the manifest corresponding to the type specs for direct
  classes. The inputs are expected to be a dictionary mapping factory parameters
  to their expected inputs, either in directly value or manifest expected by
  the parameter's type spec. The specified factory will be retrieved and called
  in `Manufacturer.make` with the all the inputs realized to their expected form
  according to the type specs.

  Do NOT instantiate this class with the constructor. Use `ObjectSpec.parse` to
  create one instead.

  `ObjectSpec.parse` accepts a single argument which can be in either of the
  following format:

    * Singleton dictionary with a factory key as key, and inputs value.
    * Dictionary with the following items:
      * `"key"`: Factory key
      * `"inputs"`: Inputs (`dict` mapping factory parameters to manifests)

  As an illustration, the following two formats are equivalent:

  ```python
  # Singleton dict format
  {
    "some_factory": {
      "arg1": value1,
      "arg2": value2,
    },
  }

  # Explicit key-value format
  {
    "key": "some_factory",
    "inputs": {
      "arg1": value1,
      "arg2": value2,
    },
  }
  ```

  The above spec represents an object created by a factory registered with key
  `"some_factory"` called with `arg1=value1, arg2=value2` as arguments. This is
  a highly simplified description. In reality the values `value1` and `value2`
  might be manifests as well, which would be transformed into direct objects
  before feeding into the factory.

  The object creation of `dict` is handled in a slightly different way.
  Normally, if the value of an argument is already an instance of the target
  type, it will be used directly as an input without further processing.
  However, as `ObjectSpec` uses `dict` as its raw representation, there might be
  situations where the intended direct value is in exactly the same formats
  described above. To disambiguate between `ObjectSpec` and direct values of
  `dict`, it will see if the given `key` corresponds to a factory. If so, the
  factory is used, otherwise it is treated as a direct value.

  However, if the direct value of a valid `ObjectSpec` raw format is expected,
  the above mechanism is still not applicable. To tackle this, `afb` provides
  the factory `afb/direct` for users to specify the direct value of the
  dictionary. See the docs for `afb/direct` for details.
  """
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
      raise errors.InvalidFormatError(
          "`spec` is expected to be in one of the following format:\n"
          "1. {{factory key (str): {{arg: manifest, ...}}}},\n"
          '2. {{"key": factory key (str), '
          '"inputs": {{arg: manifest, ...}}}}\n'
          "Given: {}".format(spec))
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
