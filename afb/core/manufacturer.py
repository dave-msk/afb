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

import collections
import copy
import inspect
import logging
import sys
import threading

from afb.core import specs
from afb.core import static
from afb.utils import errors
from afb.utils import keys
from afb.utils import types


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

    self._static = {}
    self._dynamic = {}
    self._init_static()

  @property
  def cls(self):
    return self._cls

  @property
  def default(self):
    return self._default

  @default.setter
  def default(self, method):
    with self._lock:
      self._wrap_error(lambda: errors.validate_type(method, str, "method"))
      if self._get_factory_spec(method) is None:
        self._raise_error(ValueError,
                          "The method with key `{}` not found.".format(method))
      self._default = method

  @property
  def dynamic_factories(self):
    return copy.deepcopy(self._dynamic)

  @property
  def static_factories(self):
    return copy.deepcopy(self._static)

  @property
  def factories(self):
    fcts = self.dynamic_factories
    fcts.update(self.static_factories)
    return fcts

  def has_method(self, key):
    return key in self._static or key in self._dynamic

  def _init_static(self):
    for reg in static.make_static_factories(self):
      self._register(factory_type=keys.FactoryType.STATIC, **reg)

  def _get_factory_spec(self, key):
    return self._static.get(key) or self._dynamic.get(key)

  def merge(self, root, mfr, force=False, sep="/"):
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
      root: A string that serves as the root of the factories from `mfr`.
        If empty, the original method name will be used directly.
      mfr: `Manufacturer` or a zero-argument function that returns one.
      force: If True, overwrites the original factory registration in case of
        key collision. Otherwise, an error is raised. Defaults to False.
      sep: Separator between root and method name in the resulting factory key.
        Defaults to "/".

    Raises:
      KeyError:
        - Any of the resulting keys has been registered.
      TypeError:
        - `mfr` is not a `Manufacturer` nor a zero-argument function that
            returns one.
        - Output class of `mfr` is not a subclass of this output class.
    """
    mfr = types.maybe_get_cls(mfr, Manufacturer)
    if mfr is None:
      self._raise_error(TypeError,
                        "\"mfr\" must be either a `Manufacturer` or a "
                        "zero-argument function that returns one. "
                        "Given: {}".format(mfr))
    self._validate_merge_request(root, mfr, force=force, sep=sep)
    self._merge(root, mfr, force=force, sep=sep)

  def merge_all(self, mfr_dict, force=False, sep="/"):
    """Merges multiple manufacturers.

    Args:
      mfr_dict: A dictionary mapping keys to `Manufacturer`s or zero-argument
        functions where each returns a `Manufacturer`.
      force: If `True`, overwrites the existing factory (if any). If `False`,
        raises ValueError if `key` is already registered. Defaults to `False`.
      sep: Separator between root and method name in the resulting factory key.
        Defaults to "/". See `Manufacturer.merge` for details.

    Raises:
      KeyError:
        - Any of the resulting keys has been registered.
      TypeError:
        - `mfr` is not a `Manufacturer` nor a zero-argument function that
            returns one.
        - Output class of `mfr` is not a subclass of this output class.
    """
    mfr_dict_validated = {}
    for root, mfr in mfr_dict.items():
      mfr = types.maybe_get_cls(mfr, Manufacturer)
      self._validate_merge_request(root, mfr, force=force)
      mfr_dict_validated[root] = mfr

    for root, mfr in mfr_dict_validated.items():
      self._merge(root, mfr, force=force, sep=sep)

  def _merge(self, root, mfr, force=False, sep="/"):
    factories = mfr.dynamic_factories
    for key, spec in factories.items():
      key = _merged_name(root, key, sep=sep)
      self.register(key=key,
                    factory=spec["fn"],
                    signature=spec["sig"],
                    params=spec["params"],
                    descriptions=spec["descriptions"],
                    force=force)

  def set_broker(self, broker):
    """This is intended to be called by the broker in registration."""
    self._broker = broker

  def register(self,
               key,
               factory,
               signature,
               params=None,
               descriptions=None,
               force=False):
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
      params: (Optional) Default parameters for this factory.
      descriptions: (Optional) Descriptions of this factory. If provided, it
        must a string or a dict with short description by "short" (required),
        and a long description by "long" (optional).
      force: If `True`, overwrites the existing factory (if any). If `False`,
        raises ValueError if `key` is already registered. Defaults to `False`.

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
    self._register(key,
                   factory,
                   signature,
                   params=params,
                   descriptions=descriptions,
                   force=force)

  def register_dict(self, factories_fn_dict, keyword_mode=False):
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
      factories_fn_dict: A dictionary that maps a method name to a zero-argument
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
    for k, fn in factories_fn_dict.items():
      if keyword_mode:
        kwargs = fn()
        if "sig" in kwargs:
          kwargs["signature"] = kwargs["sig"]
          del kwargs["sig"]
        self.register(k, **kwargs)
      else:
        self.register(k, *fn())

  def _register(self,
                key,
                factory,
                signature,
                params=None,
                descriptions=None,
                force=False,
                factory_type=keys.FactoryType.DYNAMIC):
    if factory_type not in (keys.FactoryType.STATIC, keys.FactoryType.DYNAMIC):
      raise ValueError("`target` must be one of FactoryType.STATIC or "
                       "FactoryType.DYNAMIC. Given: {}".format(factory_type))

    # Retrieve registry
    if factory_type == keys.FactoryType.STATIC:
      registry = self._static
    else:
      registry = self._dynamic

    # Check types
    self._wrap_error(lambda: errors.validate_type(key, str, "key"))
    self._wrap_error(
        lambda: errors.validate_is_callable(factory, "factory"), key=key)

    if not isinstance(signature, dict):
      raise self._raise_error(
          TypeError,
          "Method: {}\n`sig` must be a dict mapping factory arguments to their "
          "parameter specification, or (deprecated) type specification."
          .format(key))

    params = params or {}
    self._wrap_error(
        lambda: errors.validate_kwargs(params, "params"), key=key)

    descriptions = descriptions or factory.__doc__
    descriptions = self._wrap_error(
        lambda: _normalized_factory_descriptions(descriptions, key),
        key=key)

    # Normalize signature and determine required arguments.
    rqd_args, norm_sig = self._wrap_error(
        lambda: _format_signature(factory, signature), key=key)

    # Register factory.
    with self._lock:
      if not force and key in registry:
        raise self._raise_error(ValueError,
                                "The method `{}` is already registered."
                                .format(key))
      # TODO: Add a warning
      if force and key in registry:
        pass
      registry[key] = {"fn": factory,
                       "sig": norm_sig,
                       "rqd_args": rqd_args,
                       "params": params,
                       "descriptions": descriptions}

  def make(self, method=None, params=None):
    """Make object according to specification.

    Args:
      method: String key specifying the factory to call. If `None`, the
        default factory is used.
      params: Keyword argument dictionary for the factory. This dictionary
        can be nested for any parameter that requires an object to be created
        through another manufacturer. If `None`, the default parameters for
        the factory is used.

    Returns:
      result: An object of intended class of this manufacturer.

    Raises:
      ValueError:
        1. `method` is not registered.
        2. `params` contains invalid keyword arguments.

      TypeError:
        1. `params` is not a dictionary.
        2. Specified factory does not return the intended class object.
    """
    # 0. Sanity check
    method = method or self.default
    fct_spec = self._get_factory_spec(method)
    if fct_spec is None:
      raise self._raise_error(ValueError,
                              "Unregistered method: {}".format(method))

    self._wrap_error(lambda: errors.validate_kwargs(params, "params"),
                     key=method)

    # 1. Retrieve factory and signature
    fct = fct_spec["fn"]
    sig = fct_spec["sig"]
    rqd_args = fct_spec["rqd_args"]
    params = params or fct_spec["params"]
    self._wrap_error(lambda: errors.validate_args(params, sig), key=method)

    # 2. Prepare inputs
    # 2.1. Ensure all required args are provided and not None
    self._wrap_error(
        lambda: errors.validate_rqd_args(params, rqd_args), key=method)

    # 2.2. Validate parameter structures
    for k, p in params.items():
      type_spec = sig[k]["type"]
      self._wrap_error(lambda: errors.validate_struct(type_spec, p),
                       prefix="Method: {}\nArgument: {}".format(method, k))

    # 2.3. Construct inputs
    inputs = {}
    for k, p in params.items():
      inputs[k] = None if p is None else self._get_struct(sig[k]["type"], p)

    # 3. Call factory
    result = fct(**inputs)
    if result is not None and not isinstance(result, self.cls):
      raise self._raise_error(TypeError,
                              "Registered factory with key `{}` does not "
                              "return a `{}` object."
                              .format(method, self.cls.__name__))
    return result

  def _get_struct(self, type_spec, nested):
    if isinstance(type_spec, list) and isinstance(nested, (list, tuple)):
      t = type_spec[0]
      return [self._get_struct(t, n) for n in nested]

    if isinstance(type_spec, dict):
      kt, vt = next(iter(type_spec.items()))
      if isinstance(nested, dict):
        return {self._get_struct(kt, kn): self._get_struct(vt, vn)
                for kn, vn in nested.items()}
      elif isinstance(nested, (list, tuple)):
        return {self._get_struct(kt, kn): self._get_struct(vt, vn)
                for kn, vn in nested}
    if isinstance(type_spec, tuple) and isinstance(nested, (list, tuple)):
      return tuple(self._get_struct(t, n) for t, n in zip(type_spec, nested))
    if isinstance(type_spec, type):
      if nested is None or isinstance(nested, type_spec):
        return nested
      return self._broker.make(type_spec, nested)

    # TODO: Add error message
    # This line should be unreachable.
    raise errors.StructMismatchError()

  def _validate_merge_request(self, key, mfr, force=False, sep="/"):
    if not isinstance(key, str):
      raise self._raise_error(TypeError,
                              "`key` must be a `str`. Given: {}".format(key))

    if not isinstance(mfr, Manufacturer):
      raise self._raise_error(TypeError,
                              "`mfr` must be a `Manufacturer`. Given: {}"
                              .format(type(mfr)))
    if not issubclass(mfr.cls, self.cls):
      raise self._raise_error(TypeError,
                              "The output class of `mfr` must be a subclass of "
                              "{}, given: {}".format(self.cls, mfr.cls))
    factories = mfr.dynamic_factories
    merged_names = set(_merged_name(key, n, sep=sep) for n in factories)
    collisions = merged_names.intersection(self._dynamic)
    if collisions:
      if force:
        pass  # TODO: Give warning
      else:
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


def _format_signature(f, sig):
  sig = collections.OrderedDict(sig)
  fsig = inspect.signature(f)
  fparams = fsig.parameters

  rqd_sig = collections.OrderedDict()
  opt_sig = collections.OrderedDict()
  missing = []
  allow_implicit = False

  for k, p in fparams.items():
    if p.kind == inspect.Parameter.POSITIONAL_ONLY:
      raise errors.SignatureError("Positional-only parameter is not supported.")
    elif p.kind == inspect.Parameter.VAR_POSITIONAL:
      # TODO: Give warning that variate positionals will not be used.
      pass
    elif p.kind == inspect.Parameter.VAR_KEYWORD:
      allow_implicit = True
    else:
      if k not in sig:
        missing.append(k)
        continue

      pspec = sig.pop(k)
      if not isinstance(pspec, specs.ArgumentSpec):
        pspec = specs.ArgumentSpec.from_raw_spec(pspec)

      if p.default == inspect.Parameter.empty or pspec.forced:
        rqd_sig[k] = pspec.details
      else:
        opt_sig[k] = pspec.details

  if missing:
    raise ValueError("Missing required arguments from `signature`: {}"
                     .format(missing))
  del missing

  if sig:
    if not allow_implicit:
      raise errors.SignatureError("No such arguments: %s" % list(sig))
    for k, pspec in sig.items():
      if not isinstance(pspec, specs.ArgumentSpec):
        pspec = specs.ArgumentSpec.from_raw_spec(pspec)
      [opt_sig, rqd_sig][pspec.forced][k] = pspec.details

  rqds = set(rqd_sig)
  indexed = collections.OrderedDict(rqd_sig)
  indexed.update(opt_sig)
  return rqds, indexed


def _merged_name(root, name, sep="/"):
  return "%s%s%s" % (root, sep, name) if root else name


def _is_param_format(spec):
  if isinstance(spec, dict):
    unknown_keys = set(spec) - {"type", "description", "forced"}
    return "type" in spec and not unknown_keys
  return False


def _normalized_factory_descriptions(desc, method):
  if isinstance(desc, str):
    lines = inspect.cleandoc(desc).split("\n")
    return {"short": lines[0], "long": "\n".join(lines[1:]).strip()}

  valid_keys = {"short", "long"}
  desc = desc or {"short": ""}
  if (not isinstance(desc, dict) or
      "short" not in desc or
      (set(desc) - valid_keys)):
    raise ValueError("The factory description must either be `None`, a `str`,"
                     "or a `dict` including short description as \"short\" "
                     "(required) and long description as \"long\" (optional)."
                     "Method: {}\nGiven: {}".format(method, desc))
  short = desc["short"]
  long = desc.get("long", "")
  if not isinstance(short, str) or not isinstance(long, str):
    raise TypeError("The descriptions must be strings.\n"
                    "Method: {}\nGiven: {}".format(method, desc))
  return {"short": short, "long": long}
