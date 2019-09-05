from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from afb.core import broker as brk_lib
from afb.ext.app import job as job_lib
from afb.ext.app import task as task_lib
from afb.ext.app import values as val_lib


REGISTRY = {
    job_lib.Job: job_lib.get_factories,
    task_lib.Task: task_lib.get_factories,
    val_lib.Values: val_lib.get_factories,
}


def create_broker():
  broker = brk_lib.Broker()
  for cls, get_fcts_fn in REGISTRY.items():
    fcts = get_fcts_fn()
    for key, get_fct_fn in fcts.items():
      broker.add_factory(cls, key, **get_fct_fn())
  return broker
