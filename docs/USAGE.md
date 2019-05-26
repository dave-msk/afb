# Usage Guide

This document describes the usage of **AFB**.

## Construction

The construction of the `Manufacturer` network involves two steps:

1. Register factories of each class to its `Manufacturer`.
2. Register the resulting `Manufacturer`s to a `Broker`.

Most of the work goes to step 1 as step 2 involves only a series of `Broker.register` (or a `Broker.register_all`) calls on the existing `Manufacturer`s.

Each `Manufacturer` is responsible for making factory calls that creates instance of a particular type (or class). The constructor demands a type for instantiation:

```python
import afb

class TargetType(object):
  ...

mfr = Manufacturer(TargetType)
```

Once we have a `Manufacturer`, we can start registering factories to it. The registration of a factory involves a `Manufacturer.register` call, which accepts the following arguments:

- `name`: The name of factory. This is used in `Manufacturer.make` for retrieving the factory for the object creation.
- `factory`: The function that returns a target-typed object.
- `sig`: The signature of the function. This is used for automatic instantiation of argument objects through the `Manufacturer` network.
- `params`: (Optional) Default parameters, used when `params` is not provided in the `Manfuacturer.make` call.
- `descriptions`: (Optional) Descriptions of the factory. Used in documentation generation.

### Factory

The factory is a callable that returns the target-typed object. It can be a normal function, a callable object, or a class (constructor). It is common to define the target type as an interface / pure abstract class, and use the subclasses directly as the factories.

For example:

```python
import afb

class BinaryOperator(object):
  def compute(first, second):
    raise NotImplementedError("Must be implemented in descendants.")


class AddAndScale(BinaryOperator):
  # Signature of the factory, see below
  signature = {
      "scale": {
          "type": float,
          "description": "Scale to apply on the sum of inputs",
      },
  }

  # Descriptions of the factory, see below
  descriptions = {
      "short": "Computes the scaled sum of inputs.",
      "long": 
          """This operator computes the following value:
          
          result = (first + second) * scale
          """,
  }

  def __init__(self, scale):
    self._scale = scale

  def compute(first, second):
    return (first + second) * self._scale


mfr = afb.Manufacturer(BinaryOperator)
mfr.register("add_n_scale", AddAndScale, AddAndScale.signature,
             descriptions=AddAndScale.descriptions)
```

The `AddAndScale` class is registered as a factory of `BinaryOperator` with the name `"add_n_scale"`.


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

Once the `Broker` has been built, objects can be created either through `Manufacturer.make` or `Broker.make`. 

The `Manufacturer.make` method accepts two arguments:

- `method`: The name of the factory to be used to create the target object.
- `params`: The parameters for the factory call.

The `params` is a dictionary mapping each argument name to its value for the factory call. The values could be either objects of the arguments' expected types, or **Object Specification**s (see below).

The `Broker.make` method also accepts two arguments:

- `cls`: Type of target object
- `spec`: **Object Specification** (see below)

### Object Specification

An object specification is a singleton `dict` that maps the registered name of the factory to its input parameters:

```python
spec = {
    "factory_name": {
        "arg_1": value_1,
        "arg_2": value_2,
        ...
    },
}
```

Using the above `BinaryOperator` example, to create an `AddAndScale` object with `scale = 1.7`, an object specification would be:

```python
spec = {
    "add_n_scale": {
        "scale": 1.7,
    },
}
```

It is common for a factory to accept class objects as arguments. In such case, an object specification can be used as the value for the argument.

```python
spec = {
    "fct_name": {
        "arg_1": {
            "fct_for_arg_1": {
                "a_11": ...,
                "a_12": ...,
                ...
            }
        },
        "arg_2": ...,
    }
}
```

While specifying the value of an argument, it must conform to the structure imposed by its **Type Specification** (see above). The following describes the accepted value structures for each form of type specifications.

#### Direct Type

If a direct type (e.g. `str`, `ClassName`, etc) is used as the type specification, then the value could be either:

- an object of the target type, or
- an object specification

#### Nested Type

- Homogeneous List: A list of values in the form accepted by the content type specification.
- Homogeneous Dictionary: Either of the following is accepted:
  1. A dictionary with keys and values accepted by their respective type specifications.
  2. A list/tuple of `(key, value)` pairs (mixture of `list`s or `tuple`s of length 2) with its elements conforming the their respective type specifications.
- Tuple: A list/tuple of values in the same size as the required type spec, each conform to their respective type spec.

For example:

```python
order_spec = {
    # 1. Homogeneous List
    # Type spec of "burgers" is `[Burger]`.
    "burgers": [
        "cheese_burger": {
            "num_cheese": 3,
            "num_beef": 2,
        },
        "spicy_chicken": {
            "spicyness": 7.1,
            "with_cheese": True,
        },
    ],
    # 2. Homogeneous Dictionary
    # Type spec of "sets" is `{str: [Set]}`
    # There are two forms. The following is the dict form:
    # "sets": {
    #     "table_1": [
    #         {
    #              "happy_meal": {
    #                  ...
    #              }
    #         },
    #         {
    #              "big_mac": {
    #                  ...
    #              }
    #         },
    #     ],
    #     "table_2": ...
    # },
    # The above form will not be feasible if the key needs to use an object
    # specification. In such cases, use the list/tuple form:
    "sets": [
        ["table_1",
            [
                {"happy_meal": {...}},
                {"big_mac": {...}},
            ]
        ],
        ["table_2", ...]
    ],
    # The list/tuple form takes a list/tuple containing `(key, value)` pairs
    # (list/tuple of length 2).
}

subway_order = {
    # 3. Tuple
    # Type spec of "sandwiches" is `(Bread, str, bool, [str], [str], str)`
    # Representing:
    # Type of Bread : Meat : With Cheese : Extras : Veggies : Sauce
    "sandwiches": [
        ({"parmesan_oregano": {"size": "6-inch"}},
         "Turkey Breast",
         True,
         ["bacon"],
         ["Onions", "Cucumbers", "Olives", "Pickles", "Lettuce"],
         "BBQ Sauce"),
        [{"honey_oat": {"size": "footlong"}},
         "Roasted Chicken",
         False,
         None,
         ["Green Peppers", "Japapenos", "Onions", "Pickles", "Tomatoes"],
         "Thousand Island Dressing"]
    ],
}
```

## Documentation

**AFB** supports documentation generation. A document directory will be generated for each `Manufacturer` with the following structure:

```
full_class_name/
|- description.md
|- factories/
|  |- fct_name_1.md
|  |- fct_name_2.md
|  |- ...
```

The `full_class_name` is the full name of the `Manufacturer`'s target class. The `description.md` file contains description of the target class, and `factories` consists description files for each factory member.

The generated documents form a cookbook of the `Manufacturer` network that can be used to look up descriptions for each class, factories, and their arguments. 

### Class Description

The format of the class description is as follows:

```md
# <Class Name>

## Description

<Class Docstring>

## Factories

- <Factory 1 with link>: <Short description of factory 1>
- <Factory 2 with link>: <Short description of factory 2>
- <Factory 3 with link>: <Short description of factory 3>
...

## Builtin
- <Builtin Factory 1 with link>: <Short description of builtin factory 1>
- <Builtin Factory 2 with link>: <Short description of builtin factory 2>
- <Builtin Factory 3 with link>: <Short description of builtin factory 3>
...
```

A list of factories is provided in the section `Factories`. Each item is formatted as

```
factory_name: short description
```

where the factory name contains a hyperlink to its description file.

The `Builtin` section provides a list of builtin factories. The details are identical to the `Factories` section.

### Factory Description (Factories & Builtin)

The format of each factory description file is as follows:

```md
# <Class Name> - <Factory Name>

## Description

**<Short description>**

<Long description>

## Arguments

- <Arg 1>:
  - Type: <Type of arg 1 with link>
  - Full Type: <Full type of arg 1 with link>
  - Description: <Arg 1 description>
- <Arg 2>:
  - Type: <Type of arg 2 with link>
  - Full Type: <Full Type of arg 2 with link>
  - Description: <Arg 2 description>
...
```

The long and short descriptions are taken from the `descriptions` passed in factory registration. The each item in the argument list consists of three pieces of information:

1. Type: Type specification of the argument. A hyperlink is included for every direct type in the type spec.
2. Full Type: Same as above, with every direct type expressed in full name.
3. Description: Argument description.
