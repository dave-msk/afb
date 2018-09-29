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

import six
from threading import Lock

from afb.manufacturer import Manufacturer
from afb.primitives import get_primitives_mfrs


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

  def __init__(self):
    self._lock = Lock()

    # Initialize broker
    self._manufacturers = {}
    self._initialize()

  def _initialize(self):
    # Register manufacturers of the primitives
    self.register_all(get_primitives_mfrs())

  @property
  def classes(self):
    return list(self._manufacturers.keys())

  def get_manufacturer(self, cls):
    return self._manufacturers.get(cls)

  def merge(self, key, manufacturer):
    """Merge `Manufacturer` with the same output class.

    This method merges the factories in the given Manufacturer to the registered
    one. The method key of the newly added factories will have the form:

      * "key/<method_name>"

    See docstring of `Manufacturer.merge` for more details.

    Args:
      key: A string that serves as the root of the factories from
       `manufacturer`. If None, the original method name will be used directly.
      manufacturer: A manufacturer whose factories are to be merged.

    Raises:
      KeyError:
        - Any of the resulting keys has been registered.
      TypeError:
        - `manufacturer` is not a `Manufacturer`.
      ValueError:
        - `Manufacturer` with output class of the given one is not registered.
    """
    if not isinstance(manufacturer, Manufacturer):
      raise TypeError("`manufacturer` must be a `Manufacturer`. Given: {}"
                      .format(manufacturer))
    mfr = self.get_manufacturer(manufacturer.cls)
    if mfr is None:
      raise ValueError("Manufacturer with output class {} is not registered."
                       .format(manufacturer.cls))
    mfr.merge(key=key, manufacturer=manufacturer)

  def merge_all(self, manufacturers_dict):
    """Merge multiple manufacturers.

    Args:
      manufacturers_dict: A dictionary mapping a key to an iterable of
        `Manufacturers` to be merged. The key will be used across the iterable.
    """
    for key, mfrs in six.iteritems(manufacturers_dict):
      for mfr in mfrs:
        self.merge(key, mfr)

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

    if isinstance(params, cls):
      return params

    mfr = self._manufacturers.get(cls, None)
    if mfr is None:
      raise KeyError("Unregistered manufacturer for class: {}".format(cls))

    params = params or {None: None}
    if not isinstance(params, dict) or len(params) != 1:
      raise TypeError("`params` must be either an instance of the target type "
                      "or a singleton dictionary.")

    method, params = next(six.iteritems(params))
    return mfr.make(method=method, params=params)
