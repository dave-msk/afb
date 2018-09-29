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