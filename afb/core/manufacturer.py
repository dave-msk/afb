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

import copy
import math
import os
import shutil
import tempfile
import threading
import warnings
import weakref

from afb.core import factory as fct_lib
from afb.core import builtins_
from afb.core.specs import obj_
from afb.core.specs import type_
from afb.utils import decorators as dc
from afb.utils import errors
from afb.utils import fn_util
from afb.utils import keys
from afb.utils import misc
from afb.utils import validate


class Manufacturer(object):
  """An abstract factory of a class.

  A manufacturer contains factories for creating objects of a single class.
  It does not create the object directly. Rather, it delegates the object
  creation requests to the registered factories. The arguments are first
  transformed to a kwargs dict according to the signature of the specified
  factory, after which the factory is called.

  An object can be created by calling the `make` method. This method accepts
  two arguments: `key` and `inputs`.

    * key: The string key of the target factory.
    * inputs: A dictionary of keyword arguments for the factory. This dictionary
              can be nested for any parameter that requires an object to be
              created through another factory.

  The arguments of the target factory may require objects other than the
  primitive types (such as `int`, `float`, `bool` and `str`). In such case,
  a **Manifest** is required. See the detailed explanation described in the
  `TypeSpec`. For example, we have two classes below:

  ```python
  class A(object):
    def __init__(self, u):
      self._x = u

    @property
    def value(self):
      return self._x

  class B(object):
    def __init__(self, a, z=0):
      self._a = a
      self._z = z

    @property
    def value(self):
      return self._a.value + self._z
  ```

  The manufacturers could be defined as follows:

  ```python
  # Define manufacturer for class A.
  mfr_a = Manufacturer(A)
  # Register a factory to mfr_a. Here, constructor of A is registered as factory
  mfr_a.register("create", A, {"u": float})

  # Define manufacturer for class B.
  mfr_b = Manufacturer(B)
  # Register a factory to mfr_b. Here, constructor of B is registered as factory
  mfr_b.register("create", B, {"a": A, "z": float})
  ```

  In order to allow the manufacturers to prepare objects required for the
  factories through other manufacturers, a broker is required.

  ```python
  # Define broker
  broker = Broker()

  # Link manufacturers through the broker.
  broker.register(mfr_a)
  broker.register(mfr_b)
  ```

  > **Note:** From 1.4.0, the create and registration of `Manufacturer` can be
  done by `mfr = broker.get_or_create(cls)` directly.

  There are two ways the B object can be created:

  1. A direct call through `Manufacturer.make`:

    ```python
    inputs = {
      "a": {
        "create": {
          "u": 37.0,
        },
      },
      "z": -41.0,
    }

    b = mfr_b.make(key="create", inputs=inputs)
    ```

  2. A call through `Broker.make`. In this way, we need to wrap the `key` and
     `inputs` to a single dictionary. Note that the target class is also
     required for the broker to choose the right manufacturer.

    ```python
    spec = {
      # Factory key w.r.t manufacturer B
      "create": {
        "a": {
          # Factory key w.r.t manufacturer A
          "create": {
            "u": 37.0,
          },
        },
        "z": -41.0,
      },
    }
    b = broker.make(cls=B, spec=spec)
    ```
  """

  _mark_target_class_in_exc = dc.With("_exc_proxy",
                                      ctx_from_attr=True,
                                      call=True,
                                      attr_call_args={"prefix": "_exc_prefix"})
  _lock = dc.With("_lock", ctx_from_attr=True)

  def __init__(self, cls):
    """Creates a manufacturer for a class.

    Args:
      cls: The target class.
    """
    if not isinstance(cls, type):
      raise TypeError("`cls` must be a type. Given: {}".format(type(cls)))

    self._cls = cls
    self._lock = threading.RLock()
    self._broker_ref = None
    self._default = None

    self._exc_proxy = errors.ExceptionProxy()
    self._exc_prefix = "[{}] ".format(misc.cls_fullname(cls))

    self._builtin_fcts = {}
    self._user_fcts = {}
    self._install_builtins()

  @property
  def cls(self):
    return self._cls

  @dc.restricted("Do not bind `Broker` directly. Use `Broker.register`")
  @_lock
  def _bind(self, broker):
    _broker = self._broker
    if _broker:
      _broker._detach(self._cls)  # pylint: disable=protected-access
    self._broker_ref = weakref.ref(broker) if broker else None

  @property
  @_lock
  def _broker(self):
    if self._broker_ref:
      _broker = self._broker_ref()
      if _broker: return _broker
      self._broker_ref = None
    return None

  @property
  def default(self):
    return self._default

  @default.setter
  @_mark_target_class_in_exc
  @_lock
  def default(self, key):
    validate.validate_type(key, str, "key")
    if key is not None and key not in self:
      raise KeyError("Factory not found: {}".format(key))
    self._default = key

  # TODO: Mark as deprecated.
  @property
  def factories(self):
    return copy.deepcopy(self._user_fcts)

  def keys(self):
    return self._user_fcts.keys()

  def __contains__(self, key):
    return key in self._builtin_fcts or key in self._user_fcts

  # TODO: Mark deprecated. v=1.5.0, use `in` operator instead.
  def has_method(self, key):
    return key in self._builtin_fcts or key in self._user_fcts

  def _install_builtins(self):
    for k, make_fct in builtins_.FACTORY_MAKERS.items():
      self._register(keys.join_reserved(k), _builtins=True, **make_fct(self))

  def get(self, key):
    reg = self._builtin_fcts if keys.is_reserved(key) else self._user_fcts
    return reg.get(key)

  # TODO: Mark `force` as deprecated. Use `override` instead.
  @_mark_target_class_in_exc
  def merge(self,
            mfr,
            root=None,
            override=False,
            ignore_collision=True,
            sep="/",
            force=None):
    """Merge another manufacturer of the same type.

    This method registers all the factories from the given `Manufacturer`.
    The resulting key of the merged factories will have the following form:

      * "root<sep><factory_key>"

    For instance, using the default `sep="/"`, the merged factory key becomes:

      * "root/<factory_key>"

    This allows convenient grouping of factories by context, without the need
    to hard-code the path-like key at registration. If `root` is `None`, the
    original method name is used.

    Args:
      mfr: `Manufacturer` or a zero-argument function that returns an
        instance of it.
      root: A string that serves as the root of the factories from `mfr`.
        If None, the original factory will be used directly.
      override: If True, overwrites the original factory in case of key
        collision. Defaults to False. See `ignore_collision` for collision
        handling when `override` is False.
      ignore_collision: Will only take effect when `override` is False.
        If True, the factory key collision is ignored, i.e. the original factory
        is preserved. Otherwise, an error would be raised. Defaults to False.
      sep: Separator between root and method name in the resulting factory key.
        Defaults to "/".
      force: Deprecated. Use `override` instead. If specified, this overrides
        `override` for backwards compatibility.

    Raises:
      KeyError:
        - Any of the resulting keys has been registered.
      TypeError:
        - `mfr` is not a `Manufacturer` nor a zero-argument function that
            returns an instance of it.
        - Target of `mfr` is not a subclass of this target.
    """
    if force is not None:
      # TODO: Add deprecation warning
      override = force

    mfr = fn_util.maybe_call(mfr, Manufacturer)

    self._validate_merge(mfr, root, override, ignore_collision, sep)
    self._merge(root,
                mfr,
                override=override,
                ignore_collision=ignore_collision,
                sep=sep)

  # TODO: Mark `force` as deprecated. Use `override` instead
  @_mark_target_class_in_exc
  def merge_all(self,
                mfr_dict,
                override=False,
                ignore_collision=False,
                sep="/",
                force=None):
    """Merges multiple manufacturers.

    Args:
      mfr_dict: A dictionary mapping keys to `Manufacturer`s or zero-argument
        functions where each returns a `Manufacturer`.
      override: If True, overwrites the original factory registration in case of
        key collision. Defaults to False. See `raise_on_collision` for
        collision handling if not `override`.
      ignore_collision: If True, the factory key collision is ignored when
        `override` is False, and the original factory is preserved. Otherwise,
        an error would be raised. Defaults to False.
      sep: Separator between root and method name in the resulting factory key.
        Defaults to "/". See `Manufacturer.merge` for details.
      force: Deprecated. Use `override` instead. If specified, this overrides
        `override` for backwards compatibility.

    Raises:
      KeyError:
        - Any of the resulting keys has been registered.
      TypeError:
        - `mfr` is not a `Manufacturer` nor a zero-argument function that
            returns one.
        - Target of `mfr` is not a subclass of this target.
    """
    if force is not None:
      # TODO: Add deprecation warning
      override = force

    mfr_dict_validated = {}
    for root, mfr in mfr_dict.items():
      mfr = fn_util.maybe_call(mfr, Manufacturer)
      self._validate_merge(mfr, root, override, ignore_collision, sep)
      mfr_dict_validated[root] = mfr

    for root, mfr in mfr_dict_validated.items():
      self._merge(root,
                  mfr,
                  override=override,
                  ignore_collision=ignore_collision,
                  sep=sep)

  def _merge(self, root, mfr, override=False, ignore_collision=True, sep="/"):
    for key in mfr.keys():
      fct = mfr.get(key)
      key = _merged_name(root, key, sep=sep)
      try:
        self._register(key=key,
                       factory=fct,
                       signature=None,
                       override=override)
      except errors.KeyConflictError:
        if ignore_collision: continue
        raise

  # TODO: Mark deprecated.
  @_lock
  def set_broker(self, broker):
    """This is intended to be called by the broker in registration."""
    self._bind = broker

  # TODO: Mark `params` and `force` as deprecated.
  #   Use `defaults` and `override` instead.
  @_mark_target_class_in_exc
  def register(self,
               key,
               factory,
               signature,
               defaults=None,
               descriptions=None,
               override=False,
               params=None,
               force=None):
    """Register a factory.

    The `factory` is the callable to be used for object creation. The details of
    each of the factory arguments needs to be specified in `signature`.

    ----------------------------------------------------------------------------

    Signature
    =========

    The required signature is a `dict` mapping in the following format:

      {
        <parameter>: `ParameterSpec` (or its raw format) / Type Specification,
        ...
      }

    The raw format of `ParameterSpec` is `dict` in the following format:

      {
        "type": Type Specification,
        "description": (optional) "Description of the argument",
        "required": (optional) True / False (default)
      }

    The description will be rendered in the exported documentation.
    The `required` switch indicates whether the parameter should be registered
    as required. If `True`, the argument is required by when calling this
    factory through `Manufacturer.make`. If `False`, its requirement will be
    inferred from the factory's raw signature.

    A type specification is either of the following:

      - Singleton `dict` where the key and value are both type specifications;
      - Singleton `list`, where the content is a type specification;
      - `tuple` of type specifications; or
      - A class or type.

    For example, the type specification of a dict mapping a string to
    `TestClass` objects would be `{str: TestClass}`. See `TypeSpec` for
    detailed description.

    ----------------------------------------------------------------------------

    Args:
      key: A string key that identifies the factory.
      factory: The factory to be registered.
      signature: The signature of the input parameters. It is a dict mapping
        each argument of factory to its parameter specification.
      defaults: (Optional) Default arguments for this factory.
      descriptions: (Optional) Descriptions of this factory. If provided, it
        must a string or a dict with short description by "short" (required),
        and a long description by "long" (optional).
      override: If `True`, overwrites the existing factory (if any). If `False`,
        raises ValueError if `key` is already registered. Defaults to `False`.
      params: Deprecated. Use `defaults` instead.
      force: Deprecated. Use `override` instead.

    Raises:
      ValueError:
        2. The parameter keywords of `factory` does not match the keys of `sig`.
        3. `key` is already registered when `force` is `False`.
        4. `descriptions` is not a `dict` with short description specified.
        5. `descriptions` contains any keys not from `("short", "long")`.
      TypeError:
        1. `key` is not a string.
        2. `factory` is not a callable.
        2. `signature` is not a dict with string keys.
        3. `defaults` is not a dict with string keys.
        4. `descriptions` contains non-string values.
    """
    if force is not None:
      # TODO: Add deprecation warning
      override = force
    if params is not None:
      # TODO: Add deprecation warning
      defaults = params
    self._register(key,
                   factory,
                   signature,
                   defaults=defaults,
                   descriptions=descriptions,
                   override=override)

  # TODO: Mark `keyword_mode` as deprecated. Not used anymore
  @_mark_target_class_in_exc
  def register_dict(self, registrants, keyword_mode=None):
    """Registers factories from dictionary.

    This method allows a dictionary of factories to be registered at once.
    The argument is expected to be a dictionary that maps factory keys to
    arguments for the `Manufacturer.register` call, either in tuple or
    dictionary, or a zero-argument function that returns either of them.
    For instance, the value can be a tuple:

        (factory, signature,
         defaults (optional), descriptions (optional), override (optional))

    Or a dictionary:

        {"factory": factory,            # required
         "signature": signature,        # required
         "defaults": defaults,          # optional
         "descriptions": descriptions,  # optional
         "override": override}          # optional

    Or a zero-argument function that returns either of the above.

    A typical pattern one would encounter is to have a dictionary as a registry
    to manage a group of factories as "plugin"s, so that whenever a new
    factory is implemented it can be made available for the manufacturer to
    call by adding it in the dictionary. For example:

    `registry.py`
    ```python
    from . import factories as fct

    REGISTRY = {
      "create": fct.create.get_create,
      "load": fct.load.get_load,
    }
    ```

    `factories/create.py`:
    ```python
    def create(arg_1, arg_2, arg_3=True):
      ...
      return obj

    def get_create():
      sig = {
          "arg_1": {
              "type": str,
              "description": "Some string",
              "required": True,
          },
          "arg_2": {
              "type": [int],
              "description": "List of ints",
              "required": True,
          },
          "arg_3": {
              "type": bool,
              "description": "Some boolean",
              "required": False,
          },
      }
      return create, sig, {"arg_1": "Hello World!", "arg_2": [1, -1, 0]}
    ```

    `factories/load.py`:
    ```python
    def load(filename, mode):
      ...
      return obj

    def get_load():
      sig = {
        "filename": str,
        "mode": bool
      }
      return load, sig  # The default parameter is optional.
    ```

    The `REGISTRY` can then be passed to its manufacturer for registration.

    Args:
      registrants: A dictionary that maps each factory key to its
        `Manufacturer.register` call arguments (or zero-argument function that
        returns it).
      keyword_mode: Deprecated. Has no effect at all.
    """
    if keyword_mode is not None:
      # TODO: Add deprecation warning
      pass

    validate.validate_type(registrants, dict, "registrants")
    reg_dicts = [_prep_reg_args(k, r) for k, r in registrants.items()]

    [self.register(**kwargs) for kwargs in reg_dicts]

  @_mark_target_class_in_exc
  def _register(self,
                key,
                factory,
                signature,
                defaults=None,
                descriptions=None,
                override=False,
                _builtins=False):
    key_is_reserved = keys.is_reserved(key)
    if _builtins and not key_is_reserved:
      key = keys.join_reserved(key)
    elif not _builtins and key_is_reserved:
      # TODO: Add warning - reserved namespace
      pass

    if signature is None and isinstance(factory, fct_lib.Factory):
      # This block is for Manufacturer merges
      with self._lock:
        if key in self._user_fcts and not override:
          raise errors.KeyConflictError("Factory key `{}` exists.".format(key))
        self._user_fcts[key] = factory
      return

    # Retrieve registry
    registry = self._builtin_fcts if _builtins else self._user_fcts

    # Validate arguments
    # .1 Validate `key`
    validate.validate_type(key, str, "key")

    # .2 Validate `factory` and `signature`
    with self._exc_proxy(prefix="[key: {}] ".format(key)):
      validate.validate_is_callable(factory, "factory")
      validate.validate_type(signature, dict, "signature")
      defaults = defaults or {}
      validate.validate_kwargs(defaults, "defaults")

    # Register factory.
    with self._lock:
      if key in registry:
        if not override:
          raise errors.KeyConflictError(
              "The factory `{}` is already registered.".format(key))
        # TODO: Add a warning
      if not isinstance(factory, fct_lib.Factory):
        factory = fct_lib.Factory(self._cls,
                                  factory,
                                  signature,
                                  descriptions=descriptions,
                                  defaults=defaults)
      registry[key] = factory

  def make(self, key=None, inputs=None, method=None, params=None):
    """Make object according to specification.

    Args:
      key: String key specifying the factory to call. If `None`, the
        default factory is used.
      inputs: Keyword argument dictionary for the factory. This dictionary
        can be nested for any parameter that requires an object to be created
        through another manufacturer. If `None`, the default parameters for
        the factory is used.
      method: Deprecated. Use `key` instead. Overrides `key` if specified.
      params: Deprecated. Use `inputs` instead. Overrides `params` if specified.

    Returns:
      result: An object of intended class of this manufacturer.

    Raises:
      ValueError:
        1. `key` and `default` both not given.
        2. `key` is not registered.
        3. `inputs` contains invalid keyword arguments.

      TypeError:
        1. `inputs` is not a dictionary.
        2. Specified factory does not return the intended class object.
    """
    if method is not None:
      # TODO: Add deprecation warning
      key = method
    else:
      key = self.default if key is None else key

    if key is None:
      raise ValueError("[{}] Factory key unspecified."
                       .format(misc.cls_fullname(self._cls)))

    if params is not None:
      # TODO: Add deprecation warning
      inputs = params
    return self._make(key, inputs)

  def _make(self, key, inputs):
    fct = self.get(key)
    if fct is None:
      raise KeyError("[{}] Factory not found: {}"
                     .format(misc.cls_fullname(self._cls), key))

    with self._exc_proxy(prefix="[key: {}]".format(key)):
      validate.validate_kwargs(inputs, "inputs")

    # Hold a strong reference of `Broker` if one is bound to avoid
    # unexpected garbage collection during factory tree traversal.
    _broker = self._broker
    root = self._create_exec_tree(key, inputs)

    iter_fn = fn_util.PostorderDFS(_run_exec_tree_proc)
    return iter_fn(root)

  def _create_exec_tree(self, key, inputs):
    ts = type_.TypeSpec.parse(self._cls)
    iter_fn = fn_util.PostorderDFS(self._create_exec_tree_proc)
    return iter_fn((ts, {key: inputs}))

  def _create_exec_tree_proc(self, item):
    ts_or_cls, obj_or_spec = item
    if ts_or_cls is None:
      return fn_util.ItemResult(obj_or_spec)

    if isinstance(ts_or_cls, type_.TypeSpec):
      return fn_util.NodeResult(
          fn_util.FuseCallInfo.partial(ts_or_cls.pack),
          ts_or_cls.parse_manifest(obj_or_spec))

    assert isinstance(ts_or_cls, type)
    if obj_or_spec is None:
      return fn_util.ItemResult(obj_or_spec)

    if obj_.is_direct_object(obj_or_spec, ts_or_cls):
      return fn_util.ItemResult(obj_or_spec)

    assert isinstance(obj_or_spec, obj_.ObjectSpec)

    _broker = self._broker
    if _broker is None:
      raise errors.GraphError("Broker not found. Target: {}"
                              .format(misc.cls_fullname(self._cls)))

    mfr = self._broker.get_or_create(ts_or_cls)
    fct = mfr.get(obj_or_spec.key)

    if fct is None:
      if ts_or_cls is dict:
        return fn_util.ItemResult(obj_or_spec.raw)
      # TODO: Invalid object spec
      raise KeyError("No such factory for class {}: {}"
                     .format(misc.cls_fullname(ts_or_cls), obj_or_spec.key))

    return fn_util.NodeResult(
        fn_util.FuseCallInfo.partial(fct.call_as_fuse_fn),
        fct.parse_inputs(obj_or_spec.inputs))

  def _all_factory_items(self):
    dynamic_keys = sorted(self._user_fcts)
    for k in dynamic_keys:
      yield k, self._user_fcts[k]

    static_keys = sorted(self._builtin_fcts)
    for k in static_keys:
      yield k, self._builtin_fcts[k]

  def export_docs(self, output_dir, overwrite=False):
    target = os.path.join(output_dir, misc.cls_fullname(self._cls))
    if not overwrite and os.path.exists(target):
      raise FileExistsError("\"{}\". Pass `overwrite=True` to overwrite."
                            .format(target))

    num_fcts = len(self._builtin_fcts) + len(self._user_fcts)
    digits = math.ceil(math.log10(num_fcts))
    fct_file_fmt = os.path.join(".", "{:0%sd}.md" % digits)

    with tempfile.TemporaryDirectory() as tmp_dir:
      dynamic_fct_items = []
      static_fct_items = []
      idx = 0

      # 1. Generate factory docs
      for k, f in self._all_factory_items():
        tmpl, classes = f.markdown_doc_tmpl()
        args = {"class_name": self._cls.__name__, "factory_key": k}
        for c in classes:
          ckey = misc.cls_to_qualname_id(c)
          dest = "description.md"
          if c != self._cls:
            dest = os.path.join("..", misc.cls_fullname(c), dest)
          args[ckey] = dest
        fct_file = fct_file_fmt.format(idx)
        with open(os.path.join(tmp_dir, fct_file), "w") as fout:
          fout.write(tmpl.format(**args))
        tmpls = dynamic_fct_items if k in self._user_fcts else static_fct_items
        tmpls.append(f.markdown_item_tmpl().format(key=k, path=fct_file))
        idx += 1

      # 2. Generate description file
      with open(os.path.join(tmp_dir, "description.md"), "w") as fout:
        fout.write("# %s\n\n" % self._cls.__name__)
        fout.write("## Description\n\n%s\n\n" % self._cls.__doc__)
        fout.write("## Factories\n\n")
        [fout.write("- %s\n" % item) for item in dynamic_fct_items]
        fout.write("\n## Builtins\n\n")
        [fout.write("- %s\n" % item) for item in static_fct_items]

      # 3. Copy to output directory
      if os.path.exists(target):
        shutil.rmtree(target) if os.path.isdir(target) else os.remove(target)
      shutil.copytree(tmp_dir, target)

  @classmethod
  def from_dict(cls, klass, registrants):
    mfr = cls(klass)
    mfr.register_dict(registrants)
    return mfr

  def _validate_merge(self, mfr, key, override, ignore_collision, sep):
    validate.validate_type(key, str, "key")

    if not issubclass(mfr.cls, self.cls):
      raise TypeError(
          "The target of `mfr` must be a subclass of {}. Given: {}"
          .format(misc.cls_fullname(self.cls), misc.cls_fullname(mfr.cls)))

    if override or ignore_collision:
      return

    merged_names = set(_merged_name(key, n, sep=sep) for n in mfr.keys())
    collisions = merged_names.intersection(self._user_fcts)
    if collisions:
      raise errors.KeyConflictError(
          "Factory key conflicts detected, "
          "please use another key for merge instead: {}"
          .format(sorted(collisions)))


_reg_params = fn_util.FnArgSpec.from_fn(Manufacturer.register).parameters[2:]


def _merged_name(root, name, sep="/"):
  return name if root is None else "%s%s%s" % (root, sep, name)


def _prep_reg_args(key, registrant):
  if callable(registrant):
    registrant = registrant()

  if isinstance(registrant, dict):
    registrant = dict(registrant)
  elif isinstance(registrant, (tuple, list)):
    registrant = {kw: arg for kw, arg in zip(_reg_params, registrant)}
  else:
    raise TypeError("Invalid registrant. Expected a list, tuple or dict. "
                    "Given: {} ".format(registrant))

  if "sig" in registrant:
    # TODO: Add compatibility warning
    registrant["signature"] = registrant.pop("sig")

  if any(p not in set(_reg_params) for p in registrant):
    invalids = sorted(set(registrant) - set(_reg_params))
    raise errors.ArgumentError("Invalid parameters - key: {}, args: {}"
                               .format(key, invalids))
  registrant["key"] = key
  return registrant


def _run_exec_tree_proc(item):
  if isinstance(item, fn_util.FuseCallInfo):
    return fn_util.NodeResult(item, iter(item.args))
  return fn_util.ItemResult(item)
