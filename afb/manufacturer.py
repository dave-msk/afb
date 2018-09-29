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

import copy
import inspect
import six

from threading import RLock

from afb.utils import errors


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
    def __init__(self, x):
      self._x = x

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
  mfr_a.register('create', A, {'x': float})

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
    params = {'a': {'create': {'x': 37.0}},
              'z': -41.0}

    b = mfr_b.make(method='create', params=params)
    ```

  2. A call through `Broker.make`. In this way, we need to wrap the `method` and
     `params` to a single dictionary. Note that the target class is also
     required for the broker to choose the right manufacturer.

    ```python
    params = {'create':  # Factory key w.r.t manufacturer B
              {'a': {'create':  # Factory key w.r.t manufacturer A
                     {'x': 37.0}},
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

  def _init_builtin(self):
    target = 'builtin'
    self._register(
        'from_config', self._from_config, {'config': str}, target=target)

  def _from_config(self, config):
    params = self._broker.make(dict, {'load_config': {'config': config}})
    return self._broker.make(self.cls, params)

  def _get_factory_spec(self, key):
    return self._builtin.get(key) or self._factories.get(key)

  def merge(self, key, manufacturer):
    """Merge another manufacturer of the same type.

    This method registers all the factories from the given Manufacturer.
    The resulting key of the merged factories will have the following form:

      * "key/<method_name>"

    This allows convenient grouping of factories by context, without the need
    to hard-code the path-like key at the time of registration. If `key` is
    `None`, the original method name is used.

    Args:
      key: A string that serves as the root of the factories from
       `manufacturer`. If None, the original method name will be used directly.
      manufacturer: A manufacturer whose factories are to be merged.

    Raises:
      KeyError:
        - Any of the resulting keys has been registered.
      TypeError:
        - `manufacturer` is not a `Manufacturer`.
        - Output class of `manufacturer` is not a subclass of this output class.
    """
    if not isinstance(manufacturer, Manufacturer):
      raise TypeError("`manufacturer` must be a `Manufacturer`. Given: {}"
                      .format(manufacturer))
    if not issubclass(manufacturer.cls, self.cls):
      raise TypeError("The output class of `manufacturer` must be a subclass "
                      "of {}, given: {}".format(self.cls, manufacturer.cls))
    factories = manufacturer.factories
    merged_names = set(_merged_name(key, n) for n in factories)
    collisions = merged_names.intersection(self._factories)
    if collisions:
      raise KeyError("Method key conflicts occurred: {}. Please use another "
                     "key for merge instead".format(sorted(collisions)))
    for method, spec in six.iteritems(factories):
      method = _merged_name(key, method)
      self.register(method=method,
                    factory=spec['fn'],
                    sig=spec['sig'],
                    params=spec['params'])

  def merge_all(self, mfr_dict):
    for key, mfr in six.iteritems(mfr_dict):
      self.merge(key, mfr)

  def set_broker(self, broker):
    """This is intended to be called by the broker in registration."""
    self._broker = broker

  def register(self, method, factory, sig, params=None):
    """Register a factory.

    Args:
      method: A string key that identifies the factory.
      factory: The factory to be registered.
      sig: The signature of the input parameters. It is a dict mapping each
        argument of factory to its expected type.
      params: (Optional) Default parameters for this factory.

    Raises:
      ValueError:
        1. `factory` is not a callable.
        2. The parameter keywords of `factory` does not match
                     the keys of `sig`.
        3. `method` is already registered.
      TypeError:
        1. `method` is not a string.
        2. `sig` is not a dict with string keys.
        3. `params` is not a dict with string keys.
    """
    self._register(method, factory, sig, params)

  def register_dict(self, factories_fn_dict):
    """Registers factories from dictionary.

    This method allows a dictionary of factories to be registered at once.
    The argument is expected to be a dictionary that maps the method name
    for the factory to a function that accepts nothing and returns a tuple:

        (factory, signature, (optional) default_params)

    A typical pattern one would encounter is to have a dictionary as a registry
    to manage a group of factories as "plugin"s, so that whenever a new
    factory is implemented it can be made available for the manufacturer to
    call by adding it in the dictionary. For example:

    In `registry.py`:
    ```python
    from . import factories as fty

    REGISTRY = {
      'create': fty.create.get_create,
      'load': fty.load.get_load
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
        that accepts no argument and returns a tuple of length 2 or 3:

          (factory, signature, (optional) default_params)
    """
    for k, fn in six.iteritems(factories_fn_dict):
      self.register(k, *fn())

  def _register(self, method, factory, sig, params=None, target='factories'):

    # Retrieve registry
    registry = getattr(self, '_%s' % target, self._factories)

    # Check types
    errors.validate_is_string(method, 'method')
    errors.validate_is_callable(factory, 'factory')

    if not isinstance(sig, dict):
      raise TypeError("`sig` must be a dict mapping factory arguments "
                      "to their corresponding types.")

    params = params or {}
    errors.validate_kwargs(params, 'params')

    # Check if `sig` contains all required but no invalid arguments.
    rqd_args, all_args = fn_args(factory)
    sig_args = set(sig.keys())
    miss_args = rqd_args - sig_args
    if miss_args:
      raise ValueError("Missing required arguments from `sig`.\nRequired: {}, "
                       "Given: {}".format(sorted(rqd_args),
                                          sorted(sig_args)))
    errors.validate_args(sig_args, all_args)
    errors.validate_args(params.keys(), sig_args)

    # Register factory.
    with self._lock:
      if method in registry:
        raise ValueError("The method `{}` is already registered."
                         .format(method))
      registry[method] = {'fn': factory, 'sig': sig,
                          'rqd_args': rqd_args, 'params': params}

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
    fty_spec = self._get_factory_spec(method)
    if fty_spec is None:
      raise ValueError("Unregistered method in manufacturer {}: {}"
                       .format(self.cls, method))

    errors.validate_kwargs(params, 'params')

    # 1. Retrieve factory and signature
    fty = fty_spec['fn']
    sig = fty_spec['sig']
    rqd_args = fty_spec['rqd_args']
    params = params or fty_spec['params']
    errors.validate_args(params.keys(), sig.keys())

    # 2. Prepare arguments
    #   2.1. Add `None` to required arguments if not provided
    params.update({k: None for k in rqd_args if k not in params})

    #   2.2. Transform arguments
    for k, p in six.iteritems(params):
      arg_type = sig[k]
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
    result = fty(**params)
    if result is not None and not isinstance(result, self.cls):
      raise TypeError("Registered factory with key `{}` does not return a "
                      "`{}` object.".format(method, self.cls.__name__))
    return result

  def _transform_arg_list(self, method, kwarg, arg_type, params):
    if len(arg_type) != 1:
      raise ValueError("Only homogeneous lists are allowed. Manufacturer: {}, "
                       "Method: {}, Argument: {}, Given: {}"
                       .format(self.cls, method, kwarg, arg_type))
    return [self._get_obj(arg_type[0], p) for p in params]

  def _transform_arg_tuple(self, method, kwarg, arg_type, params):
    if len(arg_type) != len(params):
      raise ValueError("Tuple argument length mismatch. Manufacturer: {}, "
                       "Method: {}, Argument: {}, Expected: {}, Given: {}"
                       .format(
          self.cls, method, kwarg, len(arg_type), len(params)))
    return tuple([self._get_obj(t, p) for t, p in zip(arg_type, params)])

  def _transform_arg_dict(self, method, kwarg, arg_type, params):
    if len(arg_type) != 1:
      raise ValueError("Only dictionaries with homogeneous keys and values "
                       "are allowed. Manufacturer: {}, Method: {}, "
                       "Argument: {}, Given: {}."
                       .format(self.cls, method, kwarg, arg_type))
    k_t, v_t = iter(six.iteritems(arg_type)).__next__()
    return {self._get_obj(k_t, k):
            self._get_obj(v_t, v) for k, v in six.iteritems(params)}

  def _get_obj(self, cls, inputs):
    if inputs is None or isinstance(inputs, cls):
      return inputs
    return self._broker.make(cls, inputs)


def fn_args(func):
  sig = inspect.signature(func)
  required = {k for k, v in six.iteritems(sig.parameters)
              if v.default == inspect.Parameter.empty}
  return required, set(sig.parameters.keys())


def _merged_name(key, name):
  if key is None: return name
  return "%s/%s" % (key, name)
