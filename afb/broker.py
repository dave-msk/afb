# Copyright 2018 Siu-Kei Muk (David). All Rights Reserved.
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

from threading import Lock

from afb.manufacturer import Manufacturer
from afb.utils import errors


class Broker(object):
  """Broker for object creation.

  The Broker serves as a switch box / proxy that delegates the object creation
  to the corresponding manufacturer. Each registered manufacturer is identified
  by their intended output object class. The Broker registers itself to each of
  the manufacturers in their registration, so that the manufacturers could
  forward the object creation during preparation of input parameters to the
  target factory.

  To link manufacturers through a Broker, call the `register` method:

  ```python
  mfr_a = Manufacturer(A)
  mfr_b = Manufacturer(B)

  afb = Broker()

  afb.register(mfr_a)
  afb.register(mfr_b)
  # Or one can simply call the `register_all` method to register an iterable
  # of `Manufacturer`s.
  # afb.register_all([mfr_a, mfr_b])
  ```
  """

  PRIMITIVES = {int, float, bool, str, list, tuple, dict}

  def __init__(self):
    self._manufacturers = {}
    self._lock = Lock()

  @property
  def classes(self):
    return list(self._manufacturers.keys())

  def get_manufacturer(self, cls):
    return self._manufacturers.get(cls)

  def register(self, manufacturer):
    if not isinstance(manufacturer, Manufacturer):
      raise TypeError("Only Manufacturer is allowed for registration.")
    cls = manufacturer.cls
    with self._lock:
      if cls in self._manufacturers:
        raise ValueError("The class `{}` is already registered.".format(cls))
      manufacturer.set_broker(self)
      self._manufacturers[cls] = manufacturer

  def register_all(self, manufacturers):
    checked = []
    for mfr in manufacturers:
      if not isinstance(mfr, Manufacturer):
        raise TypeError("Only Manufacturer is allowed for registration.")
      checked.append(mfr)
    [self.register(mfr) for mfr in checked]

  def make(self, cls, params=None):

    if cls in self.PRIMITIVES:
      return cls(params) if params is not None else None

    mfr = self._manufacturers.get(cls, None)
    if mfr is None:
      raise KeyError("Unregistered manufacturer for class: {}".format(cls))

    params = params or {}
    errors.validate_kwargs(params, 'params')

    return mfr.make(**params)
