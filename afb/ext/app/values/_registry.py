from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from afb.ext.app.values import base as val_base
from afb.ext.app.values import factories as fcts
from afb.utils import misc


FCTS = {
    "zip": fcts.algebra.get_zipped,
    "prod": fcts.algebra.get_product,
}


def get_factories():
  return dict(FCTS)
