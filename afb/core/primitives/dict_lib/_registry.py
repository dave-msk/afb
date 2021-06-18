from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from afb.core.primitives.dict_lib import config
from afb.core.primitives.dict_lib import direct

FACTORIES = {
    "from-config": config.get_load_config,
    "direct": direct.get_direct,
}
