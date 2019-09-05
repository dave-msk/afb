from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


class Task(object):
  def run(self, *args, **kwargs):
    self._run(*args, **kwargs)

  def _run(self, *args, **kwargs):
    raise NotImplementedError("Undefined task logic.")
