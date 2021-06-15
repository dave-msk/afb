from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from afb.utils import errors
from afb.utils import misc


def validate_is_callable(obj, name):
  if not callable(obj):
    raise TypeError("`{}` must be callable. Given: {}".format(name, obj))


def validate_type(obj, cls, name):
  if obj is not None and not isinstance(obj, cls):
    raise TypeError("\"{}\" must be a \"{}\". Given: {}"
                    .format(name, misc.cls_fullname(cls), obj))


def validate_args(input_args, all_args):
  inv_args = set(input_args) - set(all_args)
  if inv_args:
    raise errors.ArgumentError(
        "Invalid arguments.\nExpected: {}\nGiven: {}\nInvalid: {}."
        .format(sorted(all_args), sorted(input_args), sorted(inv_args)))


def validate_rqd_args(input_args, rqd_args):
  missing = set(rqd_args) - set(input_args)
  if missing:
    raise errors.ArgumentError(
        "Missing required arguments.\nRequired: {}\nGiven: {}\nMissing: {}"
        .format(sorted(rqd_args), sorted(input_args), sorted(missing)))


def validate_kwargs(obj, name):
  if obj is None:
    return
  if not isinstance(obj, dict):
    raise TypeError("`{}` must be a dictionary of keyword arguments. "
                    "Given {}".format(name, type(obj)))
  inv_keys = []
  for k in obj:
    if not isinstance(k, str):
      inv_keys.append(k)
  if inv_keys:
    raise TypeError("Keys in `{}` must be of string type. Given: {}"
                    .format(name, inv_keys))
