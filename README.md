# Abstract Factory Broker

This package provides a base mechanism of the abstract factory pattern in Python.

## Install

```bash
$ pip install afb
```

## Problem

Basically, when an object of a certain class, say class `A`, is required, other than instantiating it directly through the constructor, it is also possible to define a factory to encapsulate the object creation logic for us. This is useful especially in building execution pipelines, where we may want its behavior to be easily configurable through config files. As the simplest type of config file is text file, it would be best if we can express the config objects for the system by simply a text config file. However, sometimes the constructor or the factory for creating the desired object may depend on another object, which is not easily expressible through text. This package provides a mechanism to easily define the abstract factory for instantiating the object according to the given specification in text.

## Mechanism

There are two components in this package.

### Broker

The `Broker` serves as a switch box / proxy that delegates the object creation to the corresponding manufacturer. Each registered manufacturer is identified by their intended output object class. The Broker registers itself to each of the manufacturers in their registration, so that the manufacturers could forward the object creation during preparation of input parameters to the target factory.

### Manufacturer

The `Manufacturer` serves as a collection of factories. A manufacturer contains factories for creating objects of a single class. It does not create the object directly. Rather, it delegates the object creation requests to the registered factories. The arguments are first transformed to a `kwargs` dict according to the signature of the specified factory, after which the factory is called.

If the specified factory expects an object as one of its arguments, the manufacturer will request the object from its broker, and the broker would find a manufacturer to create the required object argument.

## Usage

An object can be created by calling the `make` method. This method accepts two arguments: `method` and `params`.

- method: The string key of the target factory.
- params: A keyword argument dictionary for the factory. This dictionary can be nested for any parameter that requires an object to be created through another manufacturer.

The arguments of the target factory may require objects other than the primitive types (such as `int`, `float`, `bool` and `str`). In such case, a dictionary with the above format is expected for this parameter entry. For example, we have two classes below:

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
mftr_a = Manufacturer(A)
mftr_a.register('create', A, {'x': float})

# Define manufacturer for class B.
mftr_b = Manufacturer(B)
mftr_b.register('create', B, {'a': A, 'z': float})
```

In order to allow the manufacturers to prepare objects required for the factories through other manufacturers, a broker is required.

```python
# Define broker
broker = Broker()

# Link manufacturers through the broker.
broker.register(mftr_a)
broker.register(mftr_b)
```

There are two ways the B object can be created:

1. A direct call through `Manufacturer.make`:

  ```python
  params = {'a': {'method': 'create',
                  'params': {'x': 37}},
            'z': -41}

  b = mftr_b.make(method='create', params=params)
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
