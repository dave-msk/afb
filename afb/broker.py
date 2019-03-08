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

import os
import six
from threading import Lock

from afb.manufacturer import Manufacturer
from afb.primitives import get_primitives_mfrs
from afb.utils import docs
from afb.utils import types


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

  def merge(self, key, brk):
    """Merge all `Manufacturer`s from a `Broker`.

    This method merges all the `Manufacturer`s in the given `Broker` to the
    managed ones. All the `Manufacturer`s in `brk` will be merged with `key`.

    See docstring of `Broker.merge` and `Manufacturer.merge` for more details.

    Args:
      key: A string that serves as the root of the factories from each
        `Manufacturer` managed by `brk`. If None, the original method name
        will be used directly.
      brk: A `Broker`, or a function that accepts nothing and returns one,
        whose `Manufacturer`s are to be merged.

    Raises:
      KeyError:
        - Any of the resulting factory keys has been registered.
      TypeError:
        - `brk` is not a `Broker` nor a function which returns one.
    """
    brk = types.maybe_get_cls(brk, Broker)
    key = types.maybe_get_cls(key, str)
    classes = brk.classes
    for cls in classes:
      mfr = brk.get_manufacturer(cls)
      self.merge_mfr(key, mfr)

  def merge_mfr(self, key, mfr):
    """Merge `Manufacturer` with the same output class.

    This method merges the factories in the given `Manufacturer` to the managed
    one (an empty `Manufacturer` will be created and registered if no
    correspondence is found). The method key of the newly added factories will
    have the form:

      * "key/<method_name>"

    See docstring of `Manufacturer.merge` for more details.

    Args:
      key: A string that serves as the root of the factories from
        `mfr`. If None, the original method name will be used directly.
      mfr: A `Manufacturer`, or a function that accepts nothing and returns one,
        whose factories are to be merged.

    Raises:
      KeyError:
        - Any of the resulting factory keys has been registered.
      TypeError:
        - `mfr` is not a `Manufacturer` nor a function which returns one.
    """
    mfr = types.maybe_get_cls(mfr, Manufacturer)
    if mfr.cls not in self._manufacturers:
      self.register(Manufacturer(mfr.cls))

    _mfr = self._manufacturers[mfr.cls]
    _mfr.merge(key=key, mfr=mfr)

  def merge_mfrs(self, mfrs_dict):
    """Merge multiple manufacturers for each key.

    Args:
      mfrs_dict: A dictionary mapping a key to an iterable of
        `Manufacturer`s, or functions each accepts nothing and returns one,
         to be merged. The key will be used across the iterable.
    """
    for key, mfrs in six.iteritems(mfrs_dict):
      for mfr in mfrs:
        self.merge_mfr(key, mfr)

  def register(self, mfr):
    if not isinstance(mfr, Manufacturer):
      raise TypeError("Only Manufacturer is allowed for registration.")
    cls = mfr.cls
    with self._lock:
      if cls in self._manufacturers:
        raise ValueError("The class `{}` is already registered.".format(cls))
      mfr.set_broker(self)
      self._manufacturers[cls] = mfr

  def register_all(self, mfrs):
    checked = []
    for mfr in mfrs:
      if not isinstance(mfr, Manufacturer):
        raise TypeError("Only Manufacturer is allowed for registration.")
      checked.append(mfr)
    [self.register(mfr) for mfr in checked]

  def make(self, cls, spec=None):
    if isinstance(spec, cls):
      if cls is not dict or len(spec) > 1:
        return spec

    mfr = self._manufacturers.get(cls, None)
    if mfr is None:
      raise KeyError("Unregistered manufacturer for class: {}".format(cls))

    spec = spec or {None: None}
    if not isinstance(spec, dict) or len(spec) != 1:
      raise TypeError("`spec` must be either:"
                      "1. An instance of the target type.\n"
                      "2. An object specification (singleton `dict` mapping a "
                      "factory to its arguments for instantiation).\n"
                      "Target Type: {}\nGiven: {}".format(cls, spec))

    method, params = next(six.iteritems(spec))
    if cls is dict and not mfr.has_method(method):
      return spec
    return mfr.make(method=method, params=params)

  # TODO: Export documentations for builtin factories
  def export_markdown(self,
                      export_dir,
                      cls_dir_fn=None,
                      cls_desc_name="description"):

    def default_cls_dir_fn(cls):
      return "%s.%s" % (cls.__module__, cls.__qualname__)

    cls_dir_fn = cls_dir_fn or default_cls_dir_fn

    def factory_doc_path_fn(key):
      return os.path.join("factories", "%s.md" % key)

    for cls in self.classes:
      mfr = self.get_manufacturer(cls)
      docs.export_class_markdown(
          mfr, export_dir, cls_dir_fn, cls_desc_name, factory_doc_path_fn)
      docs.export_factories_markdown(
          mfr, export_dir, cls_dir_fn, cls_desc_name, factory_doc_path_fn)
