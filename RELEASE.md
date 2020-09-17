# Release 1.4
## Major Features And Improvements
- Released factory raw signature restrictions. `Manufacturer` now supports callables with `**kwargs` in its signature, which allows additional parameters to be specified in `signature`, so constructors of inherited classes could be more compact.
- Added `Broker.get_or_create` which creates a `Manufacturer` for the given class if one does not exist.
- Added `ArgumentSpec` for argument specification.
- Arguments can now be forced to be treated as required if `forced=True` is specified in the argument specification (defaults to `False`)
- Order of arguments listed in exported markdown documentation follows the scheme:
  1. Required explicit argument
  2. Required implicit argument
  3. Optional explicit argument
  4. Optional implicit argument

  where "explicit" refers to its presence in the factory's raw signature, and its requiredness depends on whether it is an explicit positional or marked `forced=True` in its specification.

## Bug Fixes and Other Changes
- Marked `Broker.get_manufacturer` as deprecated, use `Broker.get` instead.
- Added `create_mfr` switch to `Broker.add_factory` which allows an error to be raised if the class's `Manufacturer` is not found.

## Breaking Changes
- Changed `sig` to `signature` in `Manufacturer.register`.

# Release 1.3
## Major Features And Improvements
- `Manufacturer` now supports multi-level nested type specification.
- **From 1.3.1:** `Broker` now includes builtin factories in the documentation generation.

## Bug Fixes and Other Changes
- Included `Manufacturer`, `method` and `argument` information in error messages to help debugging.
- **From 1.3.1:** Added tuple/list form to object spec for `dict`-nested type specs. The original dict-form did not take care of the non-hashability of an object spec (which is a `dict`).

## Thanks to our Contributors
My sincere gratitude to the contributors:

Jasmine Li

# Release 1.2
## Major Features And Improvements
- Added indicator of which `Manufacturer` has raised exception for easier debugging.
- The argument `mfr` now accepts callable that takes no argument and returns a `Manufacturer`, other then a direct `Manufacturer` object for lazy evaluation.
- **From 1.2.2:** Added `Broker`-level merge. See below for API changes.

## Breaking Changes
- All occurrances of the keyword argument `manufacturer` has been changed to `mfr`.
- **From 1.2.1:** `params` in `Broker.make` is renamed to `spec`.
- **From 1.2.2:** `fty_fn_dict` in `utils.create_mfr` is renamed to `fct_fn_dict`.
- **From 1.2.2:** Original `Broker.merge` & `Broker.merge_all` for `Manufacturer` merging is renamed to `Broker.merge_mfr` and `Broker.merge_mfrs`. The method `Broker.merge` now performs `Broker`-level merges.

## Bug Fixes and Other Changes
- `Manufacturer.merge_all` will now check if there is any key collision before performing actual merges.
- **From 1.2.1:** Fixed `Broker.merge` to support function wrapped `Manufacturer`.
- **From 1.2.1:** Exported `misc` module that contains convenient helper functions for `Manufacturer` construction.

# Release 1.1
## Major Features And Improvements
- Adding `"from_config"` as a builtin factory that accepts a config file for instantiation.
- Supports merge between `Manufacturer`s
- `Broker` now comes with `Manufacturer`s for `int`, `float`, `bool`, `str`, `list`, `tuple` and `dict` as default members

## Breaking Changes
- The implicit conversions between basic types, such as `int`, `float` `bool` & `str` will not work. The user will have to specify their values in their respective format explicitly. For example, `1.0` will be interpreted as a `float`, `1` as an `int`, and `"1"` as a `str`. Specifying the value `1` for `float` will result in an error.

## Bug Fixes and Other Changes
- Changed the error to `TypeError` for mistyped `params` argument in `Broker.make`.

# Release 1.0
## Major Features And Improvements
- Changed input format from `{'method': method, 'params': params}` to `{method: params}`. (i.e., the dictionary now maps directly from method string to its parameters)
- Added bulk factory registration `register_dict` for manufacturers.

# Release 0.4
## Major Features And Improvements
- Added support for **default factory** for each manufacturer.
- Added support for **defualt parameters** for each factory.

## Bug Fixes and Other Changes
- Grouped some of the validation codes in `utils.errors`.

# Release 0.3
## Bug Fixes and Other Changes
- Fixed signature checking. Now the signature is not required to cover all the parameters of the factory. However, it is required to cover all the positional arguments.

# Release 0.2
## Bug Fixes and Other Changes

- Fixed homogeneous dictionary argument preparation.
- Supports `None` for primitive typed arguments.


# Release 0.1

Initial release of Abstract Factory Broker.
