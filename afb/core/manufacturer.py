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

import copy
import math
import os
import shutil
import sys
import tempfile
import threading
import warnings

from afb.core import factory as fct_lib
from afb.core import builtins_
from afb.core.specs import obj_
from afb.core.specs import type_
from afb.utils import errors
from afb.utils import fn_util
from afb.utils import keys
from afb.utils import misc


class Manufacturer(object):
  """An abstract factory of a class.

  A manufacturer contains factories for creating objects of a single class.
  It does not create the object directly. Rather, it delegates the object
  creation requests to the registered factories. The arguments are first
  transformed to a kwargs dict according to the signature of the specified
  factory, after which the factory is called.

  An object can be created by calling the `make` method. This method accepts
  two arguments: `method` and `params`.

    method: The string key of the target factory.
    params: A keyword argument dictionary for the factory. This dictionary can
            be nested for any parameter that requires an object to be created
            through another manufacturer.

  The arguments of the target factory may require objects other than the
  primitive types (such as `int`, `float`, `bool` and `str`). In such case,
  a singleton dictionary with method name as key and a dictionary of parameters
  as value, is expected for this parameter entry.
  For example, we have two classes below:

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
  mfr_a.register("create", A, {"u": float})

  # Define manufacturer for class B.
  mfr_b = Manufacturer(B)
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

  There are two ways the B object can be created:

  1. A direct call through `Manufacturer.make`:

    ```python
    params = {"a": {"create": {"u": 37.0}},
              "z": -41.0}

    b = mfr_b.make(method="create", params=params)
    ```

  2. A call through `Broker.make`. In this way, we need to wrap the `method` and
     `params` to a single dictionary. Note that the target class is also
     required for the broker to choose the right manufacturer.

    ```python
    params = {"create":  # Factory key w.r.t manufacturer B
              {"a": {"create":  # Factory key w.r.t manufacturer A
                     {"u": 37.0}},
               "z": -41.0}}
    b = broker.make(cls=B, params=params)
    ```
  """

  def __init__(self, cls):
    """Creates a manufacturer for a class.

    Args:
      cls: The intended output class.
    """
    self._cls = cls
    self._lock = threading.RLock()
    self._broker = None
    self._default = None

    self._builtin_fcts = {}
    self._user_fcts = {}
    self._install_builtins()

  @property
  def cls(self):
    return self._cls

  @decorators.SetterProperty
  def _bind(self, broker):
    # TODO: Add warning or raise error if not called internally
    self._broker = broker

  @property
  def default(self):
    return self._default

  @default.setter
  def default(self, method):
    with self._lock:
      self._wrap_error(lambda: errors.validate_type(method, str, "method"))
      if self._get_factory(method) is None:
        self._raise_error(ValueError,
                          "The method with key `{}` not found.".format(method))
      self._default = method

  @property
  def factories(self):
    return copy.deepcopy(self._user_fcts)

  def has_method(self, key):
    return key in self._builtin_fcts or key in self._user_fcts

  def _install_builtins(self):
    for k, make_fct in builtins_.FACTORY_MAKERS.items():
      self._register(keys.join_reserved(k), _builtins=True, **make_fct(self))

  def _get_factory(self, key):
    if key is None: key = self._default
    reg = self._builtin_fcts if keys.is_reserved(key) else self._user_fcts
    return reg.get(key)

  def merge(self,
            mfr,
            root=None,
            override=False,
            ignore_collision=True,
            sep="/",
            force=None):
    """Merge another manufacturer of the same type.

    This method registers all the factories from the given Manufacturer.
    The resulting key of the merged factories will have the following form:

      * "root<sep><method_name>"

    For instance, using the default `sep="/"`, the factory key becomes:

      * "root/<method_name>"

    This allows convenient grouping of factories by context, without the need
    to hard-code the path-like key at the time of registration. If `key` is
    `None`, the original method name is used.

    Args:
      mfr: `Manufacturer` or a zero-argument function that returns one.
      root: A string that serves as the root of the factories from `mfr`.
        If None, the original method name will be used directly.
      override: If True, overwrites the original factory registration in case of
        key collision. Defaults to False. See `raise_on_collision` for
        collision handling if not `override`.
      ignore_collision: If True, the factory key collision is ignored when
        `override` is False, and the original factory is preserved. Otherwise,
        an error would be raised. Defaults to False.
      force: Deprecated. Use `override` instead.
      sep: Separator between root and method name in the resulting factory key.
        Defaults to "/".

    Raises:
      KeyError:
        - Any of the resulting keys has been registered.
      TypeError:
        - `mfr` is not a `Manufacturer` nor a zero-argument function that
            returns an instance of it.
        - Output class of `mfr` is not a subclass of this output class.
    """
    if force is not None:
      # TODO: Add deprecation warning
      override = force
    mfr = fn_util.maybe_call(mfr, Manufacturer)  # TODO: Investigate
    if mfr is None:
      self._raise_error(TypeError,
                        "\"mfr\" must be either a `Manufacturer` or a "
                        "zero-argument function that returns an instance of it."
                        " Given: {}".format(mfr))
    self._validate_merge(mfr, root, override, ignore_collision, sep)
    self._merge(root,
                mfr,
                override=override,
                ignore_collision=ignore_collision,
                sep=sep)

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
      force: If `True`, overwrites the existing factory (if any). If `False`,
        raises ValueError if `key` is already registered. Defaults to `False`.

    Raises:
      KeyError:
        - Any of the resulting keys has been registered.
      TypeError:
        - `mfr` is not a `Manufacturer` nor a zero-argument function that
            returns one.
        - Output class of `mfr` is not a subclass of this output class.
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
    for key, fct in mfr.factories.items():
      key = _merged_name(root, key, sep=sep)
      try:
        self._register(key=key,
                       factory=fct,
                       signature=None,
                       override=override)
      except ValueError as e:
        if (ignore_collision and
            "The method `{}` is already registered.".format(key) in str(e)):
          continue
        raise

  def set_broker(self, broker):
    """This is intended to be called by the broker in registration."""
    self._broker = broker

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
        <arg-name>: `ParameterSpec` (or its raw format) / Type Specification,
        ...
      }

    The raw format of `ParameterSpec` is `dict` in the following format:

      {
        "type": Type Specification,
        "description": (optional) "Description of the argument",
        "forced": (optional) True / False (default)
      }

    The description will be rendered in the exported documentation.
    The `forced` switch indicates whether the argument should be registered
    as required. If `True`, the argument is required by when calling this
    factory through `Manufacturer.make`. If `False`, its requirement will be
    inferred from the factory's raw signature.

    A type specification is either of the following:

      - Singleton `dict` where the key and value are both type specifications;
      - Singleton `list`, where the content is a type specification;
      - `tuple` of type specifications; or
      - A class or type.

    For example, the type specification of a dict mapping a string to
    `TestClass` objects would be `{str: TestClass}`.

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
        1. `factory` is not a callable.
        2. The parameter keywords of `factory` does not match the keys of `sig`.
        3. `key` is already registered when `force` is `False`.
        4. `descriptions` is not a `dict` with short description specified.
        5. `descriptions` contains any keys not from `("short", "long")`.
      TypeError:
        1. `key` is not a string.
        2. `sig` is not a dict with string keys.
        3. `params` is not a dict with string keys.
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

  def register_dict(self, registrants, keyword_mode=None):
    """Registers factories from dictionary.

    This method allows a dictionary of factories to be registered at once.
    The argument is expected to be a dictionary that maps the method name
    for the factory to a zero-argument function returns either a tuple in
    non-keyword mode:

        (factory, signature, default_params (optional), descriptions (optional))

    Or a dictionary in keyword mode:

        {"factory": factory,            # required
         "signature": signature,        # required
         "params": default_params,      # optional
         "descriptions": descriptions}  # optional

    A typical pattern one would encounter is to have a dictionary as a registry
    to manage a group of factories as "plugin"s, so that whenever a new
    factory is implemented it can be made available for the manufacturer to
    call by adding it in the dictionary. For example:

    In `registry.py`:
    ```python
    from . import factories as fct

    REGISTRY = {
      "create": fct.create.get_create,
      "load": fct.load.get_load
    }
    ```

    whereas in `factories/create.py`:
    ```python

    def create(arg_1, arg_2, arg_3=True):
      ...
      return obj

    def get_create():
      sig = {
        "arg_1": str,
        "arg_2": [int],
        "arg_3": bool
      }
      return create, sig, {"arg_1": "Hello World!", "arg_2": [1, -1, 0]}
    ```

    and in `factories/load.py`:
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
      registrants: A dictionary that maps a method name to a zero-argument
        function that returns:

        * Non-keyword mode - A tuple:

          (factory, signature, default_params (opt), descriptions (opt))

        * Keyword mode - A dictionary:

          {"factory": factory,            # required
           "signature": signature,        # required
           "params": default_params,      # optional
           "descriptions": descriptions}  # optional

      keyword_mode: Boolean. Indicates the mode in which to perform factory
        registrations. See above.
    """
    if keyword_mode is not None:
      # TODO: Add deprecation warning
      pass

    if not isinstance(registrants, dict):
      raise TypeError()

    reg_dicts = [_prep_reg_args(k, r) for k, r in registrants.items()]
    [self.register(**kwargs) for kwargs in reg_dicts]

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
      with self._lock:
        if key in self._user_fcts and not override:
          raise self._raise_error(ValueError,
                                  "The method `{}` is already registered."
                                  .format(key))
        self._user_fcts[key] = factory
      return

    # Retrieve registry
    registry = self._builtin_fcts if _builtins else self._user_fcts

    # Check types
    self._wrap_error(lambda: errors.validate_type(key, str, "key"))
    self._wrap_error(
        lambda: errors.validate_is_callable(factory, "factory"), key=key)

    if not isinstance(signature, dict):
      raise self._raise_error(
          TypeError,
          "Method: {}\n`signature` must be a dict mapping factory arguments to "
          "their parameter specification, or (deprecated) type specification."
          .format(key))

    defaults = defaults or {}
    self._wrap_error(
        lambda: errors.validate_kwargs(defaults, "defaults"), key=key)

    # Register factory.
    with self._lock:
      if key in registry:
        if not override:
          raise self._raise_error(ValueError,
                                  "The method `{}` is already registered."
                                  .format(key))
        # TODO: Add a warning
      if not isinstance(factory, fct_lib.Factory):
        factory = fct_lib.Factory(factory,
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
        1. `key` is not registered.
        2. `inputs` contains invalid keyword arguments.

      TypeError:
        1. `inputs` is not a dictionary.
        2. Specified factory does not return the intended class object.
    """
    if method is not None:
      # TODO: Add deprecation warning
      key = method
    if params is not None:
      # TODO: Add deprecation warning
      inputs = params
    return self._make(key, inputs)

  def _make(self, key, inputs):
    # 0. Sanity check
    key = key or self.default
    fct = self._get_factory(key)
    if fct is None:
      raise self._raise_error(ValueError,
                              "Unregistered key: {}".format(key))

    self._wrap_error(lambda: errors.validate_kwargs(inputs, "inputs"),
                     key=key)
    conf = self._create_exec_conf(key, inputs)

    iter_fn = fn_util.IterDfsOp(_exec_conf_proc_fn)
    result = iter_fn(conf)

    if result is not None and not isinstance(result, self.cls):
      raise self._raise_error(TypeError,
                              "Registered factory with key `{}` does not "
                              "return a `{}` object."
                              .format(key, self.cls.__name__))
    return result

  def _create_exec_conf(self, method, args):
    ts = type_.TypeSpec.create(self._cls)
    iter_fn = fn_util.IterDfsOp(self._create_exec_conf_proc_fn)
    return iter_fn((ts, {method: args}))

  def _create_exec_conf_proc_fn(self, item):
    ts_or_cls, obj_or_spec = item
    if ts_or_cls is None:
      return obj_or_spec, misc.NONE

    if isinstance(ts_or_cls, type_.TypeSpec):
      fuse_fn = fn_util.FuseFnCallConf.partial(ts_or_cls.fuse_inputs)
      stack_item = (fuse_fn, ts_or_cls.parse_input_spec(obj_or_spec))
      return misc.NONE, stack_item

    assert isinstance(ts_or_cls, type)
    if obj_or_spec is None:
      return obj_or_spec, misc.NONE

    cls = ts_or_cls
    if obj_.is_direct_object(obj_or_spec, cls):
      return obj_or_spec, misc.NONE

    assert isinstance(obj_or_spec, obj_.ObjectSpec)

    mfr = self._broker.get_or_create(ts_or_cls)
    fct = mfr._get_factory(obj_or_spec.key)

    if fct is None:
      if cls is dict:
        return obj_or_spec.raw, misc.NONE
      # TODO: Invalid object spec
      raise KeyError(
          "No such factory for class {}: {}".format(cls, obj_or_spec.key))

    fuse_fn = fn_util.FuseFnCallConf.partial(fct.call_as_fuse_fn)
    input_spec = fct.parse_inputs(obj_or_spec.inputs)
    return misc.NONE, (fuse_fn, input_spec)

  def _all_factory_items(self):
    dynamic_keys = sorted(self._user_fcts)
    for k in dynamic_keys:
      yield k, self._user_fcts[k]

    static_keys = sorted(self._builtin_fcts)
    for k in static_keys:
      yield k, self._builtin_fcts[k]

  def export_docs(self, output_dir, replace=False):
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
      target = os.path.join(output_dir, misc.cls_fullname(self._cls))
      if replace and os.path.exists(target):
        shutil.rmtree(target) if os.path.isdir(target) else os.remove(target)
      shutil.copytree(tmp_dir, target)

  @classmethod
  def from_dict(cls, klass, registrants):
    mfr = cls(klass)
    mfr.register_dict(registrants)
    return mfr

  def _validate_merge(self, mfr, key, override, ignore_collision, sep):
    if key is not None and not isinstance(key, str):
      raise self._raise_error(
          TypeError,  "`key` must be a `str` or None. Given: {}".format(key))

    if not isinstance(mfr, Manufacturer):
      raise self._raise_error(TypeError,
                              "`mfr` must be a `Manufacturer`. Given: {}"
                              .format(type(mfr)))
    if not issubclass(mfr.cls, self.cls):
      raise self._raise_error(TypeError,
                              "The output class of `mfr` must be a subclass of "
                              "{}, given: {}".format(self.cls, mfr.cls))

    if override or ignore_collision:
      return

    factories = mfr.factories
    merged_names = set(_merged_name(key, n, sep=sep) for n in factories)
    collisions = merged_names.intersection(self._user_fcts)
    if collisions:
      raise self._raise_error(KeyError,
                              "Method key conflicts occurred: {}. "
                              "Please use another key for merge instead"
                              .format(sorted(collisions)))

  def _wrap_error(self, fn, prefix=None, suffix=None, key=None):
    try:
      return fn()
    except:
      e = sys.exc_info()
      message = str(e[1])
      if key: message = "Factory: {}\n{}".format(key, message)
      if prefix: message = "%s\n%s" % (prefix, message)
      if suffix: message = "%s\n%s" % (message, suffix)
      self._raise_error(e[0], message)

  def _raise_error(self, err_type, message):
    message = ("Raised from \"Manufacturer\" of class {}:\n{}"
               .format(self.cls, message))
    raise err_type(message)


_reg_argspec = fn_util.FnArgSpec.from_fn(Manufacturer.register)


def _merged_name(root, name, sep="/"):
  return "%s%s%s" % (root, sep, name) if root else name


def _prep_reg_args(key, registrant):
  if callable(registrant):
    registrant = registrant()

  _reg_params = _reg_argspec.parameters[2:]
  if isinstance(registrant, dict):
    registrant = dict(registrant)
  elif isinstance(registrant, (tuple, list)):
    registrant = {kw: arg for kw, arg in zip(_reg_params, registrant)}

  if not isinstance(registrant, dict):
    raise TypeError()

  if "sig" in registrant:
    # TODO: Add compatibility warning
    registrant["signature"] = registrant["sig"]
    del registrant["sig"]

  if any(p not in set(_reg_params) for p in registrant):
    invalids = sorted(set(registrant) - set(_reg_params))
    raise KeyError("Invalid arguments - key: {}, args: {}"
                   .format(key, invalids))
  registrant["key"] = key
  return registrant


def _exec_conf_proc_fn(item):
  if isinstance(item, fn_util.FuseFnCallConf):
    return misc.NONE, (item, iter(item.args))
  return item, misc.NONE
