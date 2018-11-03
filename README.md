# Abstract Factory Broker

## Introduction

Abstract Factory Broker (`afb`) is a library that facilitates abstract factory management. It introduces a mechanism for transforming configuration files into Python objects through a network of abstract factories, allowing flexible specification of execution behavior.

## Installation

This library supports Python 3.3+.

```bash
$ pip install afb
```

## Mechanism

This package consists of two classes:

  - `Manufacturer`:
    - Collection of factories of the same class.
  - `Broker`:
    - Collection of `Manufacturer`s.

### `Manufacturer`

A `Manufacturer` is a collection of factories of a class. It is responsible for delegating the object creation requests to the specified factories. The process go as follows:

  1. Retrieves the factory, along with other information, according to the given key.
  2. Prepares the arguments required by the factory, according to its signature.
  3. Calls the factory and returns the result.

Each request is done by a call to method `make` with parameters:

  - `method`: The key of the factory.
  - `params`: A `dict` of keyword argument values.

It is not uncommon that a factory depends on objects that are not directly representable in text, such as string or numbers. In this case, the request for the required object could be nested in the current request. The `Manufacturer` would first prepare the arguments by passing the sub-requests to the `Manufacturer` of the required classes through the network established by `Broker` (see below). After that, the factory is called to return the desired result.

### `Broker`

A `Broker` is a collection of `Manufacturer`s. It defines a network of `Manufacturer`s where they are able to pass object creation sub-requests to each other. It consists of a Class-to-Manufacturer mapping to pass the requests to their responsible `Manufacturer` to process.

It also accepts object creation requests through its `make` method, where an additional `cls` parameter is required to determine the right `Manufacturer` to use.

Let's take a look at an example. Suppose there are two classes, `A` and `B`. `A` has a factory `fa` that depends on a `B` object along with a `float`:

```python
def fa(b, x):
  """Creates an `A` object.
  
  Args:
    b: An instance of `B` object.
    x: A float.
  """
  ...
  return A(...)
```

And `B` has a factory `fb` that depends on a string:

```python
def fb(s):
  """Creates a `B` object.

  Args:
    s: String.
  """
  ...
  return B(...)
```

An instance of `A` can be created by first creating a `B` object, and passes it to `fa` with a `float`.

```python
# Create a `B` object
s = "some string"
b = fb(s)

# Create an `A` object
x = 3.14
a = fa(b, x)
```

Suppose the above factories are registered in their respective `Manufacturer`s (`mfr_a`, `mfr_b`) in a network defined by a `Broker` (`bkr`), `a` can be created by the following call:

```python
params = {
  "fa": {
    "b": {
      "fb": {"s": "some string"}
    },
    "x": 3.14}}

a = bkr.make(cls=A, params=params)
```

This allows us to export the object specification to an external configuration file provided by at execution time (or even dynamically generated), giving the program a notable configurability.

---

## Base Usage

It is best to illustrate how it works with an example. Suppose we have the following classes:

```python
# Class definitions
class A(object):
  ...

class B(object):
  ...

class C(object):
  ...
```

Each class has a factory, say:

```python
# Factories
def fa(x: int, y: float) -> A:
  return A(...)

def fb(z: str, a: A) -> B:
  return B(...)

def fc(x: float, b: B) -> C:
  return C(...)
```

**Note:** Here we are using the type hints available from Python 3.5 for easy illustration. In the actual code they are NOT required.

Now we have three classes, with a factory for each of them. The first thing we need to do is to create a `Manufacturer` for each class, and register their factories.

```python
# Manufacturer for class B
# ---------------------------
# 1.1 Create Manufacturer
mfr_b = Manufacturer(B)

# 1.2 Register `fb` into `mfr_b`
# 1.2.1 Provide descriptions for `fa`.
descriptions = {
    "short": "Creates B from z, a."
    "long":
        """Creates B from z, a, where ..."""
}

# 1.2.2 Provide signature, with descriptions
sig_b = {
    "z": {
        "type": str,
        "description": "Input mode of ..."
    },
    "a": {
        "type": A,
        "description": "Logic block A which ..."
    }
}

# 1.2.3 Register factory.
# We use the key "fact_b" to refer to the factory `fb`
mfr_a.register("fact_b", fb, sig_b, descriptions=descriptions)
```

Finally, register all the `Manufacturer`s to a `Broker`:

```python
# Create a Broker
broker = Broker()

# Register Manufacturers
broker.register(mfr_a)
broker.register(mfr_b)
broker.register(mfr_c)
# Or one can make a single function call:
#   `broker.register_all([mfr_a, mfr_b, mfr_c])
```

From this point, `broker`, as well as the registered `Manufacturer`s, can be used to make objects. For example, an instance of `A` can be created in the following ways:

```python
# 1. Create by `Manufacturer.make` call
params = {
    "x": -2,
    "y": 3.14
}

a = mfr_a.make("fact_a", params)

# 2. Create by `Broker.make` call
spec = {
    "fact_a": params
}

a = broker.make(A, spec)
```

The `Broker.make` method accepts two arguments:

  1. Target class
  2. Object specification

The target class (`cls`) is for the `Broker` to retrieve the right `Manufacturer`, while the object speicifcation is a singleton `dict` that specifies:

  1. The factory to use as the key
  2. The parameters to pass to the factory as the value

The object specification can be nested. Consider making an object `C`, which uses `fb` for the required `B` in `fc`, and `fa` for the required `A` in `fb`:

```python
spec = {
  "fact_c": {
    "x": 2.7183
    "b": {
      "fact_b": {
        "z": "Some mode",
        "a": {
          "fact_a": {
            "x": -2,
            "y": 3.1416
          }
        }
      }
    }
  }
}

c = broker.make(C, spec)
```

The execution goes as follows:

  1. `Broker` retrieves `Manufacturer` of `C`, `mfr_c`, and calls `mfr_c.make`
  2. `mfr_c` retrieves factory keyed by `"fact_c"`, `fc`, and prepares the arguments `x` and `b` for it.
  3. As `fc` requires `x` as a `float`, and the given value is itself a `float`, it proceeds to the next parameter.
  4. `fc` requires `b` as a `B`, and the given value is a singleton `dict`, `spec_b`, it is interpreted as an object specification. `mfr_c` then makes a `Broker.make` call for object instantiation.
  5. `Broker` retrieves `Manufacturer` of `B`, `mfr_b`, and calls `mfr_b.make` with `spec_b`.
  6. `mfr_b` retrieves factory keyed by `"fact_b"`, `fb`, and prepares the arguments `z` and `a` for it.
  7. As `fb` requires `z` as a `str`, and the given value is itself a `str`, it proceeds to the next parameter.
  8. `fb` requires `a` as an `A`, and the given value is a singleton `dict`, `spec_a`, it is interpreted as an object specification. `mfr_b` then makes a `Broker.make` call for object instantiation.
  9. `Broker` retrieves `Manufacturer` of `A`, `mfr_a`, and calls `mfr_a.make` with `spec_a`.
  10. `mfr_a` retrieves factory keyed by `"fact_a"`, `fa`, and prepares the arguments `x` and `y` for it.
  11. As `fa` requires `x` as an `int`, and the given value is itself an `int`, it proceeds to the next parameter.
  12. `fa` requires `y` as a `float`, and the given value is itself a `float`, parameter preparation is done for `fa`.
  13. `mfr_a` calls `fa` with the prepared `x` and `y`, and returns the result `obj_a` from `fa` to the caller.
  14. `Broker` returns the `obj_a` to the caller.
  15. `mfr_b` completes its parameter preparation. It calls `fb` with the prepared `z` and `a`, and returns the result `obj_b` to the caller.
  16. `Broker` returns the `obj_b` to the caller.
  17. `mfr_c` completes its parameter preparation. It calls `fc` with the prepared `x` and `b`, and returns the result `obj_c` to the caller.
  18. `Broker` returns the `obj_c` to the caller.

**Note:** The above is only for illustration purpose. In real applications, the specifications are usually loaded from configuration files, and the classes and factories are defined in dedicated packages and modules with a registry for management.

