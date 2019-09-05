from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


def lazyprop(func):
  """Decorator that makes a property lazy-evaluated."""
  attr_name = "_lazy_" + func.__name__

  @property
  def _lazy_property(self):
    if not hasattr(self, attr_name):
      setattr(self, attr_name, func(self))
    return getattr(self, attr_name)
  return _lazy_property
