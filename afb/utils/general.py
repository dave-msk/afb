from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


def val_or_default(val, default):
  return val if val is not None else default
