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

from threading import Lock

import inspect
import six

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
  a dictionary with the above format is expected for this parameter entry.
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
    params = {'a': {'method': 'create',
                    'params': {'x': 37}},
              'z': -41}

    b = mfr_b.make(method='create', params=params)
    ```

  2. A call through `Broker.make`. In this way, we need to wrap the `method` and
     `params` to a single dictionary. Note that the target class is also
     required for the broker to choose the right manufacturer.

    ```python
    params = {'method': 'create',  # Factory key w.r.t manufacturer B
              'params':
                {'a': {'method': 'create',  # Factory key w.r.t manufacturer A
                       'params': {'x': 37}},
                 'z': -41}}
    b = broker(cls=B, params=params)
    ```
  """

  def __init__(self, cls):
    """Creates a manufacturer for a class.

    Args:
      cls: The intended output class.
    """
    self._cls = cls
    self._factories = {}
    self._lock = Lock()
    self._broker = None
    self._default = None

  @property
  def cls(self):
    return self._cls

  @cls.setter
  def cls(self, value):
    raise AttributeError('Output object type of manufacturer is immutable.')

  @property
  def default(self):
    return self._default

  @default.setter
  def default(self, method):
    errors.validate_is_string(method, 'method')
    if method not in self._factories:
      raise ValueError("The method with key `{}` not found.".format(method))
    self._default = method

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
      if method in self._factories:
        raise ValueError("The method `{}` is already registered."
                         .format(method))
      self._factories[method] = {'fn': factory, 'sig': sig,
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
    if method not in self._factories:
      raise ValueError("Unregistered method in manufacturer {}: {}"
                       .format(self.cls, method))

    errors.validate_kwargs(params, 'params')

    # 1. Get factory and signature
    fty_spec = self._factories[method]
    fty = fty_spec['fn']
    sig = fty_spec['sig']
    rqd_args = fty_spec['rqd_args']
    params = params or fty_spec['params']
    errors.validate_args(params.keys(), sig.keys())

    # 2. Prepare arguments
    #   2.1. Add `None` to required arguments if not provided
    params.update({k: None for k in rqd_args if k not in params})

    #   2.2. Transform arguments
    for k, p in params.items():
      arg_type = sig[k]
      if isinstance(arg_type, list):
        arg = self._transform_arg_list(method, k, arg_type, p)
      elif isinstance(arg_type, tuple):
        arg = self._transform_arg_tuple(method, k, arg_type, p)
      elif isinstance(arg_type, dict):
        arg = self._transform_arg_dict(method, k, arg_type, p)
      else:
        arg = self._get_from_broker(arg_type, p)
      params[k] = arg

    # 3. Call factory
    result = fty(**params)
    if not isinstance(result, self.cls):
      raise TypeError("Registered factory with key `{}` does not return a "
                      "`{}` object.".format(method, self.cls.__name__))
    return result

  def _transform_arg_list(self, method, kwarg, arg_type, params):
    if len(arg_type) != 1:
      raise ValueError("Only homogeneous lists are allowed. Manufacturer: {}, "
                       "Method: {}, Argument: {}, Given: {}"
                       .format(self.cls, method, kwarg, arg_type))
    return [self._get_from_broker(arg_type[0], p) for p in params]

  def _transform_arg_tuple(self, method, kwarg, arg_type, params):
    if len(arg_type) != len(params):
      raise ValueError("Tuple argument length mismatch. Manufacturer: {}, "
                       "Method: {}, Argument: {}, Expected: {}, Given: {}"
                       .format(
          self.cls, method, kwarg, len(arg_type), len(params)))
    return tuple([self._get_from_broker(t, p) for t, p in zip(arg_type, params)])

  def _transform_arg_dict(self, method, kwarg, arg_type, params):
    if len(arg_type) != 1:
      raise ValueError("Only dictionaries with homogeneous keys and values "
                       "are allowed. Manufacturer: {}, Method: {}, "
                       "Argument: {}, Given: {}."
                       .format(self.cls, method, kwarg, arg_type))
    k_t, v_t = iter(arg_type.items()).__next__()
    return {self._get_from_broker(k_t, k):
            self._get_from_broker(v_t, v) for k, v in params.items()}

  def _get_from_broker(self, key, params):
    return self._broker.make(key, params)


def fn_args(func):
  sig = inspect.signature(func)
  required = {k for k, v in sig.parameters.items()
              if v.default == inspect.Parameter.empty}
  return required, set(sig.parameters.keys())
