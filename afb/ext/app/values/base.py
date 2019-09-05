from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections


class Values(object):
  def make_iterator(self):
    iterator = self._make_iterator()
    if not isinstance(iterator, collections.Iterator):
      raise TypeError("\"_make_iterator\" must return an Iterator. "
                      "Given: {}".format(type(iterator)))

    return iterator

  def _make_iterator(self):
    raise NotImplementedError("Must be implemented in descendants.")
