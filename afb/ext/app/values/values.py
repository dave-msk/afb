# Copyright 2019 Siu-Kei Muk (David). All Rights Reserved.
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

import collections


class Values(object):
  def make_iterator(self):
    iterator = self._make_iterator()
    if not isinstance(iterator, collections.Iterator):
      raise TypeError("\"_make_iterator\" must return an Iterator. "
                      "Given: {}".format(type(iterator)))

    return iterator

  def _make_iterator(self):
    raise NotImplementedError("Must be implemented in descendants.")
