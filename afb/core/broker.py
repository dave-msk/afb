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

import warnings
from threading import RLock

from deprecated import deprecated

from afb.core.manufacturer import Manufacturer
from afb.core import primitives
from afb.utils import decorators as dc
from afb.utils import fn_util


class Broker(object):
  """Broker for object creation.

  The Broker serves as a switch box / proxy that delegates the object creation
  to the corresponding manufacturer. Each registered manufacturer is identified
  by their target class. The Broker binds itself to each of the manufacturers
  in their registration, so that the manufacturers could get factories of other
  types required in preparation of factory inputs.

  To link manufacturers through a Broker, call the `register` method:

  ```python
  import afb

  mfr_a = Manufacturer(A)
  mfr_b = Manufacturer(B)

  broker = Broker()

  broker.register(mfr_a)
  broker.register(mfr_b)
  # Or one can simply call the `register_all` method to register an iterable
  # of `Manufacturer`s.
  # broker.register_all([mfr_a, mfr_b])
  ```

  Starting from `1.4.0`, a `Manufacturer` can be created and registered directly
  through `Broker.get_or_create(cls)`:

  ```python
  broker = Broker()
  mfr_a = broker.get_or_create(A)
  mfr_b = broker.get_or_create(B)
  ```
  """

  def __init__(self):
    self._lock = RLock()
    self._mfrs = {}

  @property
  def classes(self):
    return list(self._mfrs.keys())

  @deprecated(version="1.4.0", reason="Use `get` or `get_or_create` instead.")
  def get_manufacturer(self, cls):
    return self.get(cls)

  def get(self, cls):
    return self._mfrs.get(cls)

  def get_or_create(self, cls):
    """Get class manufacturer. Create and register if one does not exist."""
    if not isinstance(cls, type):
      # TODO: Add error message
      raise TypeError()
    if cls not in self._mfrs:
      with self._lock:
        if cls not in self._mfrs:
          if primitives.is_supported(cls):
            self.register(primitives.create_mfr(cls))
          else:
            self.register(Manufacturer(cls))
    return self._mfrs[cls]

  def add_factory(self,
                  cls,
                  key,
                  factory,
                  signature,
                  defaults=None,
                  descriptions=None,
                  override=False,
                  sig=None,
                  params=None,
                  force=None,
                  create_mfr=None):
    """Register factory to Manufacturer of given class.

    """
    # TODO: Add deprecation warning
    if sig is not None:
      signature = sig

    if force is not None:
      override = force

    if params is not None:
      defaults = params

    if create_mfr is not None:
      pass

    self._add_factory(cls,
                      key,
                      factory,
                      signature,
                      defaults=defaults,
                      descriptions=descriptions,
                      override=override)

  def merge(self, root, broker):
    """Merge all `Manufacturer`s from a `Broker`.

    This method merges all the `Manufacturer`s in the given `Broker` to the
    managed ones. All the `Manufacturer`s in `broker` will be merged with `key`.

    See docstring of `Broker.merge` and `Manufacturer.merge` for more details.

    Args:
      root: A string that serves as the root of the factories from each
        `Manufacturer` managed by `broker`. If None, the original method name
        will be used directly.
      broker: A `Broker`, or a zero-argument function that returns one,
        whose `Manufacturer`s are to be merged.

    Raises:
      KeyError:
        - Any of the resulting factory keys has been registered.
      TypeError:
        - `broker` is not a `Broker` nor a function which returns one.
    """
    self._merge(root, broker)

  def merge_mfr(self, root, mfr):
    """Merge `Manufacturer` with the same output class.

    This method merges the factories in the given `Manufacturer` to the managed
    one (an empty `Manufacturer` will be created and registered if no
    correspondence is found). The method key of the newly added factories will
    have the form:

      * "root/<method_name>"

    See docstring of `Manufacturer.merge` for more details.

    Args:
      root: A string that serves as the root of the factories from
        `mfr`. If None, the original method name will be used directly.
      mfr: A `Manufacturer`, or a zero-argument function that returns one,
        whose factories are to be merged.

    Raises:
      KeyError:
        - Any of the resulting factory keys has been registered.
      TypeError:
        - `mfr` is not a `Manufacturer` nor a function which returns one.
    """
    self._merge_mfr(root, mfr)

  def merge_mfrs(self, mfrs_dict):
    """Merge multiple manufacturers for each key.

    Args:
      mfrs_dict: A dictionary mapping a key to an iterable of
        `Manufacturer`s, or zero-argument functions where each returns one,
         to be merged. The key will be used across the iterable.
    """
    for key, mfrs in mfrs_dict.items():
      for mfr in mfrs:
        self.merge_mfr(key, mfr)

  def _merge(self, root, broker):
    broker = fn_util.maybe_call(broker, Broker)
    root = fn_util.maybe_call(root, str)
    classes = broker.classes
    for cls in classes:
      mfr = broker.get(cls)
      self.merge_mfr(root, mfr)

  def _merge_mfr(self, root, mfr):
    mfr = fn_util.maybe_call(mfr, Manufacturer)
    if mfr.cls not in self._mfrs:
      self.register(Manufacturer(mfr.cls))

    _mfr = self._mfrs[mfr.cls]
    _mfr.merge(root=root, mfr=mfr)

  def register(self, mfr, override=False):
    """TODO: Add docs"""
    self._register(mfr, override=override)

  def register_all(self, mfrs, override=False):
    checked = []
    for mfr in mfrs:
      if not isinstance(mfr, Manufacturer):
        raise TypeError("Only Manufacturer is allowed for registration.")
      checked.append(mfr)
    [self.register(mfr, override=override) for mfr in checked]

  def _register(self, mfr, override=False):
    if not isinstance(mfr, Manufacturer):
      raise TypeError("Only Manufacturer is allowed for registration.")
    cls = mfr.cls
    with self._lock:
      if cls in self._mfrs and not override:
        raise ValueError("The class `{}` is already registered.".format(cls))
      mfr._bind = self  # pylint: disable=protected-access
      self._mfrs[cls] = mfr

  @dc.restricted
  def _detach(self, cls):
    if cls in self._mfrs:
      with self._lock:
        if cls in self._mfrs:
          self._mfrs.pop(cls)

  def make(self, cls, spec=None):
    if isinstance(spec, cls):
      if cls is not dict or len(spec) > 1:
        return spec

    mfr = self._mfrs.get(cls, None)
    if mfr is None:
      raise KeyError("Unregistered manufacturer for class: {}".format(cls))

    spec = spec or {None: None}
    if not isinstance(spec, dict) or len(spec) != 1:
      raise TypeError("`spec` must be either:"
                      "1. An instance of the target type.\n"
                      "2. An object specification (singleton `dict` mapping a "
                      "factory to its arguments for instantiation).\n"
                      "Target Type: {}\nGiven: {}".format(cls, spec))

    method, params = next(iter(spec.items()))
    if cls is dict and method not in mfr:
      return spec
    return mfr.make(method=method, params=params)

  @deprecated(version="1.5.0",
              reason="")
  def export_markdown(self,
                      export_dir,
                      cls_dir_fn=None,
                      cls_desc_name=None):
    if (cls_dir_fn, cls_desc_name) != (None, None):
      # TODO: Add warning
      warnings.warn("")
    return self.export_docs(export_dir)

  def export_docs(self, export_dir):
    for mfr in self._mfrs.values():
      mfr.export_docs(export_dir)
    for mfr in primitives.create_missing_mfrs(self._mfrs):
      mfr.export_docs(export_dir)

  def _add_factory(self,
                   cls,
                   key,
                   factory,
                   signature,
                   defaults=None,
                   descriptions=None,
                   override=False):
    mfr = self.get_or_create(cls)
    mfr.register(key,
                 factory,
                 signature,
                 defaults=defaults,
                 descriptions=descriptions,
                 override=override)
