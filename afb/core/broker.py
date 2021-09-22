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

import inspect
import warnings
from threading import RLock

from afb.core import primitives
from afb.core.manufacturer import Manufacturer
from afb.core.specs import obj_
from afb.utils import decorators as dc
from afb.utils import deprecation
from afb.utils import errors
from afb.utils import fn_util
from afb.utils import misc
from afb.utils import validate


class Broker(object):
  """Broker for object creation.

  The Broker serves as a switch box / proxy that delegates the object creation
  request to the corresponding `Manufacturer`. Each registered manufacturer is
  identified by their target class. The Broker binds itself to each of the
  manufacturers in their registration, so that manufacturers could get factories
  of other types required to prepare for factory call inputs.

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

  To create an object, call the `Broker.make` method. The following code snippet
  illustrates how an instance of `B` is created through the factory named
  `"create"`:

  ```python
  b = broker.make(B, key="create", inputs={...})
  ```

  See `Broker.make` and `Manufacturer.make` for details.
  """

  def __init__(self):
    self._lock = RLock()
    self._mfrs = {}

  @property
  def classes(self):
    return sorted(self._mfrs.keys(), key=lambda c: misc.qualname(c))

  @deprecation.deprecated("Use `Broker.get` instead.")
  def get_manufacturer(self, cls):
    return self.get(cls)

  def get(self, cls):
    """Retrieve registered `Manufacturer` with target class.

    Args:
      cls: Target class of desired `Manufacturer`.

    Returns:
      The registered `Manufacturer` with `cls` as target, or None if not present

    Raises:
      TypeError: `cls` is not a class.
    """
    if not inspect.isclass(cls):
      raise TypeError("`cls` must be a class. Given: {}".format(type(cls)))
    return self._mfrs.get(cls)

  def get_or_create(self, cls):
    """Get `Manufacturer`, or create and register if one does not exist.

    Args:
      cls: Target class of desired `Manufacturer`.

    Returns:
      The registered `Manufacturer` with `cls` as target.

    Raises:
      TypeError: `cls` is not a class.
    """
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

  # TODO: Breaking changes to API
  def add_factory(self, cls, key, factory, signature, **kwargs):
    """Register factory to `Manufacturer` with specified target class.

    This method is a shorthand to the following:

    ```python
    mfr = broker.get_or_create(cls)
    mfr.register(key, factory, signature, ...)
    ```

    Args:
      cls: Target class of `Manufacturer`
      key: A string key that identifies the factory.
      factory: The factory to be registered.
      signature: The signature of the input parameters. It is a dict mapping
        each factory parameter to its parameter specification.
      **kwargs: Register options:
        * defaults: (Optional) `dict` of default arguments for this factory.
        * descriptions: (Optional) Descriptions of this factory.
        * override: If `True`, overrides the existing factory (if any).
          If `False`, an error is raised in case of key collision.
          Defaults to `False`.
    """
    if "force" in kwargs:
      deprecation.warn(
          "Parameter `force` is deprecated. Use `override` instead.")
      kwargs["override"] = kwargs.pop("force")

    if "params" in kwargs:
      deprecation.warn(
        "Parameter `params` is deprecated. Use `defaults` instead.")
      kwargs["defaults"] = kwargs.pop("params")

    if "create_mfr" in kwargs:
      deprecation.warn("Parameter `create_mfr` is not used anymore.")
      kwargs.pop("create_mfr")

    self._add_factory(cls, key, factory, signature, **kwargs)

  # TODO: Breaking changes to API
  def merge(self, broker, **kwargs):
    """Merge all `Manufacturer`s from given `Broker`.

    This method merges all the `Manufacturer`s in the given `Broker` to self.
    All the `Manufacturer`s in `broker` will be merged with `key`.

    See `Manufacturer.merge` for details.

    Args:
      broker: A `Broker`, or a zero-argument function that returns an instance
        of it, whose `Manufacturer`s are to be merged.
      **kwargs: Merge options:
        * root: A string that serves as the root of the factory keys from `mfr`.
            If None, the original factory key will be used directly.
        * override: If True, overwrites the original factory in case of key
        * collision. Defaults to False. See `ignore_collision` for collision
            handling when `override` is False.
        * ignore_collision: Will only take effect when `override` is False.
            If True, the factory key collision is ignored, i.e. the original
            factory is preserved. Otherwise, an error would be raised when key
            collision occurs. Defaults to False.
        * sep: Separator between root and method name in the resulting
            factory key. Defaults to "/".

    Raises:
      KeyConflictError:
        - Any of the resulting factory keys has been registered.
      TypeError:
        - `broker` is not a `Broker` nor a function which returns
          an instance of it.
    """
    self._merge(broker, **kwargs)

  # TODO: Breaking changes to API
  def merge_mfr(self, mfr, **kwargs):
    """Merge `Manufacturer` with the same output class.

    This method merges the factories in the given `Manufacturer` to the managed
    one (an empty `Manufacturer` will be created and registered if no
    correspondence is found). The method key of the newly added factories will
    have the form:

      * "root<sep><method_name>"

    See docstring of `Manufacturer.merge` for details.

    Args:
      mfr: A `Manufacturer`, or a zero-argument function that returns an
        instance of it, whose factories are to be merged.
      **kwargs: Merge options:
        * root: A string that serves as the root of the factory keys from `mfr`.
            If None, the original factory key will be used directly.
        * override: If True, overwrites the original factory in case of key
            collision. Defaults to False. See `ignore_collision` for collision
            handling when `override` is False.
        * ignore_collision: Will only take effect when `override` is False.
            If True, the factory key collision is ignored, i.e. the original
            factory is preserved. Otherwise, an error would be raised when key
            collision occurs. Defaults to False.
        * sep: Separator between root and method name in the resulting
            factory key. Defaults to "/".

    Raises:
      KeyConflictError:
        - Any of the resulting keys has been registered when `override` and
          `ignore_collision` are both False.
      TypeError:
        - `mfr` is not a `Manufacturer` nor a zero-argument function that
           returns an instance of it.
        - Target of `mfr` is not a subclass of this target.
    """
    self._merge_mfr(mfr, **kwargs)

  def merge_mfrs(self, mfr_dict, **kwargs):
    """Merge multiple manufacturers for each key.

    Args:
      mfr_dict: A dictionary mapping a key to an iterable of `Manufacturer`s,
        or zero-argument functions where each returns instance of it, to be
        merged. The key will be used across the iterable.
      **kwargs: Merge options:
        * override: If True, overwrites the original factory in case of key
            collision. Defaults to False. See `ignore_collision` for collision
            handling when `override` is False.
        * ignore_collision: Will only take effect when `override` is False.
            If True, the factory key collision is ignored, i.e. the original
            factory is preserved. Otherwise, an error would be raised when key
            collision occurs. Defaults to False.
        * sep: Separator between root and method name in the resulting
            factory key. Defaults to "/".

    Raises:
      KeyConflictError:
        - Any of the resulting keys has been registered when `override` and
          `ignore_collision` are both False.
      TypeError:
        - Any of the elements of the iterable `dict` values is not
          `Manufacturer` or a zero-argument function that returns an instance
          of it.
    """
    for root, mfrs in mfr_dict.items():
      if not hasattr(mfrs, "__iter__") and callable(mfrs):
        mfrs = mfrs()
      for mfr in mfrs:
        self.merge_mfr(mfr, root=root, **kwargs)

  def _merge(self, broker, **kwargs):
    broker = fn_util.maybe_call(broker, Broker)
    for cls in broker.classes:
      mfr = broker.get(cls)
      self.merge_mfr(mfr, **kwargs)

  def _merge_mfr(self, mfr, **kwargs):
    mfr = fn_util.maybe_call(mfr, Manufacturer)
    _mfr = self.get_or_create(mfr.cls)
    _mfr.merge(mfr, **kwargs)

  def register(self, mfr, override=False):
    """Register a `Manufacturer`

    The `mfr` is the `Manufacturer` to be used to retrieve the factories for
    instantiation of its target class. Each `Manufacturer` can be retrieved
    by the `get` or `get_or_create` methods, through which the desired factory
    is extracted for object creation.

    Only a single `Manufacturer` instance of the same target class can be
    attached to the same `Broker` at any time. When another `Manufacturer` with
    the same target class is registered with `override=True`, the original one
    is detached.

    Args:
      mfr: An instance of `Manufacturer` or a zero-argument function that
        returns an instance of it.
      override: If True, when a `Manufacturer` with the same target class
        exists, detaches the original one and registers `mfr`. If False,
        an error is raised instead. Defaults to False.

    Raises:
      KeyConflictError:
        - `Manufacturer` class collision occurs and `override` is False.
    """
    self._register(mfr, override=override)

  def register_all(self, mfrs, **kwargs):
    """Registers multiple `Manufacturer`s at once.

    Args:
      mfrs: An iterable of `Manufacturer`s, or zero-argument functions where
        each returns an instance of it.
      **kwargs: Register options
        * override: If True, when a `Manufacturer` with the same target class
            exists, detaches the original one and registers `mfr`. If False,
            an error is raised instead. Defaults to False.

    Raises:
      KeyConflictError:
        - `Manufacturer` class collision occurs and `override` is False.
    """
    checked = []
    for mfr in mfrs:
      mfr = fn_util.maybe_call(mfr, Manufacturer)
      checked.append(mfr)
    [self.register(mfr, **kwargs) for mfr in checked]

  def _register(self, mfr, override=False):
    validate.is_type(mfr, Manufacturer, "mfr")
    cls = mfr.cls
    with self._lock:
      if cls in self._mfrs:
        if not override:
          raise errors.KeyConflictError(
              "Manufacturer with target class `{}` exists."
              .format(misc.qualname(cls)))
        self._mfrs.pop(cls)._bind = None
      mfr._bind(self)  # pylint: disable=protected-access
      self._mfrs[cls] = mfr

  @dc.restricted
  def _detach(self, cls):
    if cls in self._mfrs:
      with self._lock:
        if cls in self._mfrs:
          self._mfrs.pop(cls)

  def make(self, cls, key=None, inputs=None, spec=None):
    """Create object of specified class via factory.

    This method delegates the object creation to the `Manufacturer` of
    specified `cls` with the given arguments.

    Args:
      cls: Class or type of instance to be created.
      key: String key specifying the factory to call. If `None`, the
        default factory is used.
      inputs: Keyword argument `dict` for the factory. This `dict` is expected
        to map each factory parameter to its manifest. See `TypeSpec` for
        detailed explanation on manifests. If `None`, the default inputs for
        for the factory is used.
      spec: Deprecated. `dict`. Either `{key: inputs}` or
        `{"key": key, "inputs": inputs}` is accepted. If specified, `key` and
        `inputs` are ignored, for compatibility.

    Returns:
      A instance of `cls` created by specified factory and inputs.

    Raises:
      ArgumentError:
        - Invalid inputs for any involved factory call. (e.g. missing required
          arguments, or invalid argument exists)
      GraphError:
        - This `Manufacturer` not attached to `Broker` when calling factories
          where other classes are referenced.
      InvalidFormatError:
        - `inputs` contains arguments not conforming to the corresponding
          type spec.
      KeyError:
        - Factory with `key` not found.
      ValueError:
        - `key` and `default` both unspecified.
      TypeError:
        - `inputs` is not a kwargs dictionary.
        - Specified factory does not return an instance of the target class.
    """
    mfr = self.get_or_create(cls)

    if spec is not None:
      deprecation.warn("Parameter `spec` is deprecated. "
                       "Specify `key` and `inputs` directly.")
    else:
      spec = {"key": key, "inputs": inputs}
    obj_spec = obj_.ObjectSpec.parse(spec)

    return mfr.make(**obj_spec.as_dict())

  @deprecation.deprecated("Use `Broker.export_docs` instead.")
  def export_markdown(self,
                      export_dir,
                      cls_dir_fn=None,
                      cls_desc_name=None):
    if (cls_dir_fn, cls_desc_name) != (None, None):
      deprecation.warn(
          "Parameters `cls_dir_fn` and `cls_desc_name` are not used anymore.")
    return self.export_docs(export_dir)

  def export_docs(self, output_dir, **kwargs):
    """Export documentations of `Manufacturer`s in markdown.

    This method exports documentations of `Manufacturer`s, including registered
    ones and those of the natively supported primitive types, into `output_dir`
    in markdown format. Each `Manufacturer` will generate docs in its dedicated
    directory named after the full name of its target class. See
    `Manufacturer.export_docs` for details.

    Args:
      output_dir: Directory under which the `Manufacturer`s will output their
        generated docs folders.
      **kwargs: Export docs options:
        * overwrite: If True, replaces `output_dir/<class>` with newly generated
            directories if any of them exists. If False, an error is raised
            instead.

    Raises:
      FileExistsError:
        - Path to any `output_dir/<class>` exists and `overwrite` is False.
    """
    for mfr in self._mfrs.values():
      mfr.export_docs(output_dir, **kwargs)
    for mfr in primitives.create_missing_mfrs(self._mfrs):
      mfr.export_docs(output_dir, **kwargs)

  def _add_factory(self, cls, key, factory, signature, **kwargs):
    mfr = self.get_or_create(cls)
    mfr.register(key, factory, signature, **kwargs)
