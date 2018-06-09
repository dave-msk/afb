from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import six


def validate_is_string(obj, name):
  if obj is not None and not isinstance(obj, six.string_types):
    raise TypeError("`{}` must be a string. Given: {}".format(name, type(obj)))


def validate_is_callable(obj, name):
  if not six.callable(obj):
    raise ValueError("`{}` must be a callable. Given: {}".format(name, obj))


def validate_args(input_args, all_args):
  inv_args = set(input_args) - set(all_args)
  if inv_args:
    raise ValueError("Invalid arguments. Expected: {}, Given: {}."
                     .format(sorted(all_args), sorted(input_args)))


def validate_kwargs(obj, name):
  if obj is None:
    return
  if not isinstance(obj, dict):
    raise TypeError("`{}` must be a dictionary of keyword arguments. "
                    "Given {}".format(name, type(obj)))
  inv_keys = []
  for k in obj:
    if not isinstance(k, six.string_types):
      inv_keys.append(k)
  if inv_keys:
    raise TypeError("Keys in `{}` must be of string type. Given: {}"
                    .format(name, inv_keys))
