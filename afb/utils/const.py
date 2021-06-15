from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os


KEY = "key"
INPUTS = "inputs"
VALUE = "value"

KEY_VALUE = {KEY, VALUE}
KEY_INPUTS = {KEY, INPUTS}

AFB_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
