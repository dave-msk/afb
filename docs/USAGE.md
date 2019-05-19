# Usage Guide

This document describes the usage of **AFB**.

## Construction

TODO

### Description

The description of a factory is expected to be a `dict` with a `short` and a `long` description `str`:

```python
descriptions = {
    "short": "Brief description about the factory / returned object.",
    "long":
        """Detailed description about the factory / returned object.

        It is common that an abstract class / interface is used as the target
        type of a `Manufacturer`. In such case, factories are likely to be
        the constructor of subclasses that implement the base class.

        Therefore, one may provide descriptions on the behavior of the specific
        implementation.
        """,
}
```

The factory description is used in documentation generation, see the **Documentation** section below.

### Signature

The signature of a factory is expected to be a `dict` mapping each function argument to its details, which is a `dict` containing its **Type Specification** (see below) and description:

```python
def factory(arg_name_1, arg_name_2, ...):
  obj = ...  # Creates the object
  return obj


sig = {
    "arg_name_1": {
        "type": <Type Specification for arg_name_1>,
        "description": "Description of `arg_name_1`.",
    },
    "arg_name_2": {
        "type": <Type Specification for arg_name_2>,
        "description": "Description of `arg_name_2`.",
    },
    ...
}
```

#### Type Specification

The type of an argument is specified through a **Type Specification**, which is defined as either of the following:

1. A `type` instance (e.g. class);
2. A singleton `list` of type specification;
3. A singleton `dict` with type specification as key and value;
4. A tuple of type specifications.

For instance:

```python
class Example(object):
  pass


sig = {
    # Case 1: `type` instance
    "name": {
        "type": str,
        "description": "A string",
    },
    "example": {
        "type": Example,
        "description": "An instance of `Example`.",
    },
    # Case 2: Singleton `list` of type speicifcation
    "examples": {
        "type": [Example],
        "description": "A list of instances of `Example`.",
    },
    "nested_list_arg": {
        "type": [[str]],
        "description": "A list of lists of strings.",
    },
    # Case 3: Singleton `dict` with type specification as key and value
    "regex_map": {
        "type": {str: str},
        "description": "A dict mapping strings to strings",
    },
    "example_id_map": {
        "type": {Example: str},
        "description": "A dict mapping instaces of `Example` to strings",
    },
    # Case 4: Tuple of type specifications
    "example_pair": {
        "type": (Example, Example),
        "description": "A 2-tuple of `Example`s.",
    },
    "complicated_tuple": {
        "type": (int, [float], [[str]], {str: Example}),
        "description": 
            "A 4-tuple of "
            "(int, list of float, list of lists of str, dict: str -> Example)."
    },
    ...
}
```

**AFB** supports nested type specifications where each form could be nested in one another, as illustrated above. Each input argument is expected to be either `None`, or conform to the specified structure. The `Manufacturer` takes care of the argument preparation that gives a value in the exact same structure as the required type specification. See the section **Object Specification** below for details.

## Application

TODO

## Documentation

TODO