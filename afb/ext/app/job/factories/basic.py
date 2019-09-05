from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from afb.ext.app.job import base as job_base
from afb.ext.app.task import base as task_base
from afb.ext.app.values import base as val_base


def get_job():
  desc = {
      "short": "",
      "long":
          """
          """,
  }

  sig = {
      "task": {
          "type": task_base.Task,
          "description": "",
      },
      "args": {
          "type": val_base.Values,
          "description": "",
      },
  }

  return {"factory": job_base.Job, "sig": sig, "descriptions": desc}
