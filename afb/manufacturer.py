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

import copy
import inspect
import os
import six
import sys

from threading import RLock

from afb.utils import errors
from afb.utils import types


_TYPE_CHECKS = [
    lambda t: isinstance(t, type),
    lambda t: isinstance(t, list) and len(t) == 1 and isinstance(t[0], type),
    lambda t: isinstance(t, tuple) and all(isinstance(e, type) for e in t),
    lambda t: (isinstance(t, dict) and len(t) == 1 and
               all(isinstance(k, type) and
                   isinstance(v, type) for k, v in six.iteritems(t)))
]


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
  mfr_a.register('create', A, {'u': float})

  # Define manufacturer for class B.
  mfr_b = Manufacturer(B)
  mfr_b.register('create', B, {'a': A, 'z': float})
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
    params = {'a': {'create': {'u': 37.0}},
              'z': -41.0}

    b = mfr_b.make(method='create', params=params)
    ```

  2. A call through `Broker.make`. In this way, we need to wrap the `method` and
     `params` to a single dictionary. Note that the target class is also
     required for the broker to choose the right manufacturer.

    ```python
    params = {'create':  # Factory key w.r.t manufacturer B
              {'a': {'create':  # Factory key w.r.t manufacturer A
                     {'u': 37.0}},
               'z': -41.0}}
    b = broker.make(cls=B, params=params)
    ```
  """

  def __init__(self, cls):
    """Creates a manufacturer for a class.

    Args:
      cls: The intended output class.
    """
    self._cls = cls
    self._lock = RLock()
    self._broker = None
    self._default = None

    self._builtin = {}
    self._factories = {}
    self._init_builtin()

  @property
  def cls(self):
    return self._cls

  @property
  def default(self):
    return self._default

  @default.setter
  def default(self, method):
    with self._lock:
      errors.validate_is_string(method, 'method')
      if self._get_factory_spec(method) is None:
        raise ValueError("The method with key `{}` not found.".format(method))
      self._default = method

  @property
  def factories(self):
    return copy.deepcopy(self._factories)

  def has_method(self, method):
    return method in self._builtin or method in self._factories

  def _init_builtin(self):
    target = 'builtin'
    self._register(
        'from_config', self._from_config, {'config': str}, target=target)

  # TODO: Add documentations
  def _from_config(self, config):
    params = self._broker.make(dict, {'load_config': {'config': config}})
    return self._broker.make(self.cls, params)

  def _get_factory_spec(self, key):
    return self._builtin.get(key) or self._factories.get(key)

  def merge(self, key, mfr):
    """Merge another manufacturer of the same type.

    This method registers all the factories from the given Manufacturer.
    The resulting key of the merged factories will have the following form:

      * "key/<method_name>"

    This allows convenient grouping of factories by context, without the need
    to hard-code the path-like key at the time of registration. If `key` is
    `None`, the original method name is used.

    Args:
      key: A string that serves as the root of the factories from `mfr`.
        If empty, the original method name will be used directly.
      mfr: `Manufacturer` or a function that accepts nothing and returns it.

    Raises:
      KeyError:
        - Any of the resulting keys has been registered.
      TypeError:
        - `mfr` is not a `Manufacturer` nor a function that accepts nothing
            and returns it.
        - Output class of `mfr` is not a subclass of this output class.
    """
    mfr = types.maybe_get_cls(mfr, Manufacturer)
    if mfr is None:
      self._raise_error(TypeError,
                        "\"mfr\" must be either a `Manufacturer` or a "
                        "function that accepts nothing and returns it. "
                        "Given: {}".format(mfr))
    self._validate_merge_request(key, mfr)
    self._merge(key, mfr)

  def merge_all(self, mfr_dict):
    """Merges multiple manufacturers.

    Args:
      mfr_dict: A dictionary mapping keys to `Manufacturer`s or functions where
        each accepts nothing and returns a `Manufacturer`.

    Raises:
      KeyError:
        - Any of the resulting keys has been registered.
      TypeError:
        - `mfr` is not a `Manufacturer` nor a function that accepts nothing and
            returns it.
        - Output class of `mfr` is not a subclass of this output class.
    """
    mfr_dict_validated = {}
    for key, mfr in six.iteritems(mfr_dict):
      mfr = types.maybe_get_cls(mfr, Manufacturer)
      self._validate_merge_request(key, mfr)
      mfr_dict_validated[key] = mfr

    for key, mfr in six.iteritems(mfr_dict_validated):
      self._merge(key, mfr)

  def _merge(self, key, mfr):
    factories = mfr.factories
    for method, spec in six.iteritems(factories):
      method = _merged_name(key, method)
      self.register(method=method,
                    factory=spec['fn'],
                    sig=spec['sig'],
                    params=spec['params'],
                    descriptions=spec["descriptions"])

  def set_broker(self, broker):
    """This is intended to be called by the broker in registration."""
    self._broker = broker

  def register(self,
               method,
               factory,
               sig,
               params=None,
               descriptions=None):
    """Register a factory.

    Args:
      method: A string key that identifies the factory.
      factory: The factory to be registered.
      sig: The signature of the input parameters. It is a dict mapping each
        argument of factory to its expected type.
      params: (Optional) Default parameters for this factory.
      descriptions: (Optional) Descriptions of this factory. If provided, it
      must specifies the short description keyed by "short". A long description
      keyed by "long" can optionally be included.

    Raises:
      ValueError:
        1. `factory` is not a callable.
        2. The parameter keywords of `factory` does not match
                     the keys of `sig`.
        3. `method` is already registered.
        4. `descriptions` is not a `dict` with short description specified.
        5. `descriptions` contains any keys not from `("short", "long")`.
      TypeError:
        1. `method` is not a string.
        2. `sig` is not a dict with string keys.
        3. `params` is not a dict with string keys.
        4. `descriptions` contains non-string values.
    """
    self._register(method,
                   factory,
                   sig,
                   params=params,
                   descriptions=descriptions)

  def register_dict(self, factories_fn_dict, keyword_mode=False):
    """Registers factories from dictionary.

    This method allows a dictionary of factories to be registered at once.
    The argument is expected to be a dictionary that maps the method name
    for the factory to a function that accepts nothing and returns either
    a tuple in non-keyword mode:

        (factory, signature, default_params (optional), descriptions (optional))

    Or a dictionary in keyword mode:

        {"factory": factory,            # required
         "sig": signature,              # required
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
      'create': fct.create.get_create,
      'load': fct.load.get_load
    }
    ```

    whereas in `factories/create.py`:
    ```python

    def create(arg_1, arg_2, arg_3=True):
      ...
      return obj

    def get_create():
      sig = {
        'arg_1': str,
        'arg_2': [int],
        'arg_3': bool
      }
      return create, sig, {'arg_1': 'Hello World!', 'arg_2': [1, -1, 0]}
    ```

    and in `factories/load.py`:
    ```python

    def load(filename, mode):
      ...
      return obj

    def get_load():
      sig = {
        'filename': str,
        'mode': bool
      }
      return load, sig  # The default parameter is optional.
    ```

    The `REGISTRY` can then be passed to its manufacturer for registration.

    Args:
      factories_fn_dict: A dictionary that maps a method name to a function
        that accepts no argument and returns:

        * Non-keyword mode - A tuple:

          (factory, signature, default_params (opt), descriptions (opt))

        * Keyword mode - A dictionary:

          {"factory": factory,            # required
           "sig": signature,              # required
           "params": default_params,      # optional
           "descriptions": descriptions}  # optional

      keyword_mode: Boolean. Indicates the mode in which to perform factory
        registrations. See above.
    """
    for k, fn in six.iteritems(factories_fn_dict):
      if keyword_mode:
        self.register(k, **fn())
      else:
        self.register(k, *fn())

  def _register(self,
                method,
                factory,
                sig,
                params=None,
                descriptions=None,
                target='factories'):

    # Retrieve registry
    registry = getattr(self, '_%s' % target, self._factories)

    # Check types
    errors.validate_is_string(method, 'method')
    errors.validate_is_callable(factory, 'factory')

    if not isinstance(sig, dict):
      raise self._raise_error(TypeError,
                              "`sig` must be a dict mapping factory arguments "
                              "to their corresponding types.")

    params = params or {}
    errors.validate_kwargs(params, 'params')

    try:
      descriptions = _normalized_factory_descriptions(descriptions)
      sig = _parse_signature(sig)
    except:
      e = sys.exc_info()
      self._raise_error(e[0], str(e[1]))

    # Check if `sig` contains all required but no invalid arguments.
    rqd_args, all_args = fn_args(factory)
    sig_args = set(sig.keys())
    miss_args = rqd_args - sig_args
    if miss_args:
      raise self._raise_error(ValueError,
                              "Missing required arguments from `sig`."
                              "\nRequired: {}, Given: {}"
                              .format(sorted(rqd_args), sorted(sig_args)))
    errors.validate_args(sig_args, all_args)
    errors.validate_args(params.keys(), sig_args)

    # Register factory.
    with self._lock:
      if method in registry:
        raise self._raise_error(ValueError,
                                "The method `{}` is already registered."
                                .format(method))
      registry[method] = {'fn': factory,
                          'sig': sig,
                          'rqd_args': rqd_args,
                          'params': params,
                          'descriptions': descriptions}

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
    # 0. Sanity checks
    method = method or self.default
    fct_spec = self._get_factory_spec(method)
    if fct_spec is None:
      raise self._raise_error(ValueError,
                              "Unregistered method in manufacturer {}: {}"
                              .format(self.cls, method))

    errors.validate_kwargs(params, 'params')

    # 1. Retrieve factory and signature
    fct = fct_spec['fn']
    sig = fct_spec['sig']
    rqd_args = fct_spec['rqd_args']
    params = params or fct_spec['params']
    errors.validate_args(params.keys(), sig.keys())

    # 2. Prepare arguments
    #   2.1. Add `None` to required arguments if not provided
    params.update({k: None for k in rqd_args if k not in params})

    # TODO: Support types with nested structures with arbitrary depth
    #   2.2. Transform arguments
    for k, p in six.iteritems(params):
      arg_type = sig[k]['type']
      if isinstance(arg_type, list) and isinstance(p, list):
        arg = self._transform_arg_list(method, k, arg_type, p)
      elif isinstance(arg_type, tuple) and isinstance(p, tuple):
        arg = self._transform_arg_tuple(method, k, arg_type, p)
      elif isinstance(arg_type, dict) and isinstance(p, dict):
        arg = self._transform_arg_dict(method, k, arg_type, p)
      else:
        arg = self._get_obj(arg_type, p)
      params[k] = arg

    # 3. Call factory
    result = fct(**params)
    if result is not None and not isinstance(result, self.cls):
      raise self._raise_error(TypeError,
                              "Registered factory with key `{}` does not "
                              "return a `{}` object."
                              .format(method, self.cls.__name__))
    return result

  def _transform_arg_list(self, method, kwarg, arg_type, params):
    if len(arg_type) != 1:
      raise self._raise_error(ValueError,
                              "Only homogeneous lists are allowed. "
                              "Method: {}, Argument: {}, Given: {}"
                              .format(self.cls, method, kwarg, arg_type))
    return [self._get_obj(arg_type[0], p) for p in params]

  def _transform_arg_tuple(self, method, kwarg, arg_type, params):
    if len(arg_type) != len(params):
      raise self._raise_error(
          ValueError,
          "Tuple argument length mismatch. "
          "Method: {}, Argument: {}, Expected: {}, Given: {}"
          .format(method, kwarg, len(arg_type), len(params)))
    return tuple([self._get_obj(t, p) for t, p in zip(arg_type, params)])

  def _transform_arg_dict(self, method, kwarg, arg_type, params):
    if len(arg_type) != 1:
      raise self._raise_error(
          ValueError,
          "Only dictionaries with homogeneous keys and values are allowed. "
          "Method: {}, Argument: {}, Given: {}."
          .format(self.cls, method, kwarg, arg_type))
    k_t, v_t = iter(six.iteritems(arg_type)).__next__()
    return {self._get_obj(k_t, k):
            self._get_obj(v_t, v) for k, v in six.iteritems(params)}

  def _get_obj(self, cls, inputs):
    if inputs is None or isinstance(inputs, cls):
      return inputs
    return self._broker.make(cls, inputs)

  def _validate_merge_request(self, key, mfr):
    if not isinstance(key, str):
      raise self._raise_error(TypeError,
                              "`key` must be a `str`. Given: {}".format(key))

    if not isinstance(mfr, Manufacturer):
      raise self._raise_error(TypeError,
                              "`mfr` must be a `Manufacturer`. Given: {}"
                              .format(mfr))
    if not issubclass(mfr.cls, self.cls):
      raise self._raise_error(TypeError,
                              "The output class of `mfr` must be a subclass of "
                              "{}, given: {}".format(self.cls, mfr.cls))
    factories = mfr.factories
    merged_names = set(_merged_name(key, n) for n in factories)
    collisions = merged_names.intersection(self._factories)
    if collisions:
      raise self._raise_error(KeyError,
                              "Method key conflicts occurred: {}. "
                              "Please use another key for merge instead"
                              .format(sorted(collisions)))

  def _raise_error(self, err_type, message):
    message = ("Raised from \"Manufacturer\" of class {}: {}"
               .format(self.cls.__name__, message))
    raise err_type(message)


def fn_args(func):
  sig = inspect.signature(func)
  required = {k for k, v in six.iteritems(sig.parameters)
              if v.default == inspect.Parameter.empty}
  return required, set(sig.parameters.keys())


def _merged_name(key, name):
  key = key or ""
  return os.path.join(key, name)


def _parse_signature(sig):
  parsed = {}
  for k, v in six.iteritems(sig):
    v = _normalized_signature_entry(v)
    parsed[k] = v
  return parsed


def _is_valid_type(t):
  return any(check(t) for check in _TYPE_CHECKS)


def _normalized_signature_entry(v):
  valid_keys = {"type", "description"}
  if _is_valid_type(v):
    return {"type": v, "description": ""}
  elif (isinstance(v, dict) and
        _is_valid_type(v.get("type")) and
        not (valid_keys - set(six.iterkeys(v)))):
    return {"type": v["type"], "description": v.get("description", "")}

  raise ValueError("The value of an entry of the signature dictionary must "
                   "either be a type specification, or a `dict` "
                   "of length at most 2, with the type specification keyed by "
                   "\"type\", and optionally a description in `str` of the "
                   "argument keyed by \"description\".")


def _normalized_factory_descriptions(desc):
  valid_keys = {"short", "long"}
  desc = desc or {"short": ""}
  if (not isinstance(desc, dict) or
      "short" not in desc or
      (set(six.iterkeys(desc)) - valid_keys)):
    raise ValueError("The factory description must either be `None` or a `dict`"
                     " with the short description keyed as by \"short\" "
                     "included. A long description keyed by \"long\" can be "
                     "optionally provided. Given: {}".format(desc))
  short = desc["short"]
  long = desc.get("long", "")
  if not isinstance(short, str) or not isinstance(long, str):
    raise TypeError("The descriptions must be strings. Given: {}".format(desc))
  return {"short": short, "long": long}

