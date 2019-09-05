from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from afb.ext.app.job import base
from afb.ext.app.job import factories as fcts
from afb.utils import misc


FCTS = {
    "job": fcts.basic.get_job,
}


def get_factories():
  return dict(FCTS)
