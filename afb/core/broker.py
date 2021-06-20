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
from threading import RLock

from afb.core import primitives
from afb.core.manufacturer import Manufacturer
from afb.core.specs import obj_
from afb.utils import decorators as dc
from afb.utils import errors
from afb.utils import fn_util
from afb.utils import misc
from afb.utils import validate


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
    return sorted(self._mfrs.keys(), key=lambda c: misc.cls_fullname(c))

  # TODO: Mark deprecated. Use `get` instead.
  def get_manufacturer(self, cls):
    return self.get(cls)

  def get(self, cls):
    if not isinstance(cls, type):
      raise TypeError("`cls` must be a type. Given: {}".format(type(cls)))
    return self._mfrs.get(cls)

  def get_or_create(self, cls):
    """Get class manufacturer. Create and register if one does not exist."""
    mfr = self.get(cls)
    if mfr is None:
      with self._lock:
        if cls not in self._mfrs:
          if primitives.is_supported(cls):
            self.register(primitives.create_mfr(cls))
          else:
            self.register(Manufacturer(cls))
      mfr = self._mfrs[cls]
    return mfr

  # TODO: Mark `sig`, `params`, `force`, `create_mfr` as deprecated
  #   `sig` -> `signature`
  #   `params` -> `defaults`
  #   `force` -> `override`
  #   `create_mfr` not used anymore
  # TODO: Breaking changes to API
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

  # TODO: Update docstring
  # TODO: Breaking changes to API
  def merge(self, broker, **kwargs):
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
    self._merge(broker, **kwargs)

  # TODO: Update docstring
  # TODO: Breaking changes to API
  def merge_mfr(self, mfr, **kwargs):
    """Merge `Manufacturer` with the same output class.

    This method merges the factories in the given `Manufacturer` to the managed
    one (an empty `Manufacturer` will be created and registered if no
    correspondence is found). The method key of the newly added factories will
    have the form:

      * "root/<method_name>"

    See docstring of `Manufacturer.merge` for more details.

    Args:
      mfr: A `Manufacturer`, or a zero-argument function that returns one,
        whose factories are to be merged.
      root: A string that serves as the root of the factories from
        `mfr`. If None, the original method name will be used directly.

    Raises:
      KeyError:
        - Any of the resulting factory keys has been registered.
      TypeError:
        - `mfr` is not a `Manufacturer` nor a function which returns one.
    """
    self._merge_mfr(mfr, **kwargs)

  # TODO: Update docstring
  def merge_mfrs(self, mfrs_dict, **kwargs):
    """Merge multiple manufacturers for each key.

    Args:
      mfrs_dict: A dictionary mapping a key to an iterable of
        `Manufacturer`s, or zero-argument functions where each returns one,
         to be merged. The key will be used across the iterable.
    """
    for root, mfrs in mfrs_dict.items():
      for mfr in mfrs:
        self.merge_mfr(mfr, root=root, **kwargs)

  def _merge(self, broker, **kwargs):
    broker = fn_util.maybe_call(broker, Broker)
    classes = broker.classes
    for cls in classes:
      mfr = broker.get(cls)
      self.merge_mfr(mfr, **kwargs)

  def _merge_mfr(self, mfr, **kwargs):
    mfr = fn_util.maybe_call(mfr, Manufacturer)
    _mfr = self.get_or_create(mfr.cls)
    _mfr.merge(mfr, **kwargs)

  def register(self, mfr, override=False):
    """TODO: Add docs"""
    self._register(mfr, override=override)

  def register_all(self, mfrs, **kwargs):
    checked = []
    for mfr in mfrs:
      mfr = fn_util.maybe_call(mfr, Manufacturer)
      checked.append(mfr)
    [self.register(mfr, **kwargs) for mfr in checked]

  def _register(self, mfr, override=False):
    validate.validate_type(mfr, Manufacturer, "mfr")
    cls = mfr.cls
    with self._lock:
      if cls in self._mfrs:
        if not override:
          raise errors.KeyConflictError(
              "Manufacturer with target class `{}` exists."
              .format(misc.cls_fullname(cls)))
        self._mfrs.pop(cls)._bind = None
      mfr._bind(self)  # pylint: disable=protected-access
      self._mfrs[cls] = mfr

  @dc.restricted
  def _detach(self, cls):
    if cls in self._mfrs:
      with self._lock:
        if cls in self._mfrs:
          self._mfrs.pop(cls)

  # TODO: Mark `spec` as deprecated. Specify `key` and `inputs` directly
  def make(self, cls, spec=None, key=None, inputs=None):
    mfr = self.get_or_create(cls)

    if spec is not None:
      # TODO: Add deprecation warning
      pass
    else:
      spec = {"key": key, "inputs": inputs}
    obj_spec = obj_.ObjectSpec.parse(spec)

    return mfr.make(**obj_spec.as_dict())

  # TODO: Mark this method deprecated. Use `export_docs` instead.
  def export_markdown(self,
                      export_dir,
                      cls_dir_fn=None,
                      cls_desc_name=None):
    if (cls_dir_fn, cls_desc_name) != (None, None):
      # TODO: Add warning
      warnings.warn("")
    return self.export_docs(export_dir)

  def export_docs(self, export_dir, **kwargs):
    for mfr in self._mfrs.values():
      mfr.export_docs(export_dir, **kwargs)
    for mfr in primitives.create_missing_mfrs(self._mfrs):
      mfr.export_docs(export_dir, **kwargs)

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
