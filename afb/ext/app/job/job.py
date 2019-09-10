# Copyright 2019 Siu-Kei Muk (David). All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from afb.ext.app.task import task as task_lib
from afb.ext.app.values import values as val_lib


class Job(object):
  def __init__(self, task, args=None):
    if not isinstance(task, task_lib.Task):
      raise TypeError("`task` must be an `afb.app.Task`. Given: {}"
                      .format(type(task)))
    if args and not isinstance(args, val_lib.Values):
      raise TypeError("`args` must be an `afb.app.Values`. Given: {}"
                      .format(type(args)))
    self._task = task
    self._args = args

  def run(self):
    args_iter = self._args.make_iterator() if self._args else [{}]

    for kwargs in args_iter:
      self._task.run(**kwargs)


def get_job():
  desc = {
      "short": "",
      "long":
          """
          """,
  }

  sig = {
      "task": {
          "type": task_lib.Task,
          "description": "",
      },
      "args": {
          "type": val_lib.Values,
          "description": "",
      },
  }

  return {"factory": Job, "sig": sig, "descriptions": desc}
