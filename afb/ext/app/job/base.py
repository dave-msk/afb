from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from afb.ext.app.task import base as task_base
from afb.ext.app.values import base as val_base


class Job(object):
  def __init__(self, task, args=None):
    if not isinstance(task, task_base.Task):
      raise TypeError("`task` must be an `afb.app.Task`. Given: {}"
                      .format(type(task)))
    if args and not isinstance(args, val_base.Values):
      raise TypeError("`args` must be an `afb.app.Values`. Given: {}"
                      .format(type(args)))
    self._task = task
    self._args = args

  def run(self):
    args_iter = self._args.make_iterator() if self._args else [{}]

    for kwargs in args_iter:
      self._task.run(**kwargs)
