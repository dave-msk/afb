from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import importlib

from afb.utils import decorators


class ModuleProxy(object):
  def __init__(self, path):
    self._path = path

  @decorators.LazyProperty
  def _mod(self):
    return importlib.import_module(self._path)

  def __getattr__(self, item):
    return getattr(self._mod, item)
