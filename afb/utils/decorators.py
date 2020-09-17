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


def lazyprop(func):
  """Decorator that makes a property lazy-evaluated.

  Credits go to Aran-Frey on StackOverflow:
  https://stackoverflow.com/questions/3012421/python-memoising-deferred-lookup-property-decorator

  Args:
    func: Zero-argument method to be decorated as lazy property.

  Returns:
    Lazy property that takes value from `func`.
  """
  attr_name = "_lazy_" + func.__name__

  @property
  def _lazy_property(self):
    if not hasattr(self, attr_name):
      setattr(self, attr_name, func(self))
    return getattr(self, attr_name)
  return _lazy_property
