# Copyright 2020 (David) Siu-Kei Muk. All Rights Reserved.
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

import json
import os

import yaml

from afb.utils import proxy

NONE = object()

CONFIG_LOADER = {
    'yaml': yaml.safe_load,
    'yml': yaml.safe_load,
    'json': json.load,
}

_mfr_lib = proxy.ModuleProxy("afb.core.manufacturer")


def create_mfr(cls, fct_fn_dict, keyword_mode=None):
  if keyword_mode is not None:
    # TODO: Add deprecation warning
    pass
  return _mfr_lib.Manufacturer.from_dict(cls, fct_fn_dict)


def cls_to_qualname_id(cls, sep="_"):
  if not isinstance(cls, type):
    # TODO: Add error message
    raise TypeError("`cls` must be a class. Given: {}".format(cls))
  fmt = "%s" + sep + "%s"
  return fmt % (cls.__module__.replace(".", sep), cls.__name__)


def cls_fullname(cls):
  if not isinstance(cls, type):
    raise TypeError("`cls` must be a class. Given: {}".format(cls))

  return "%s.%s" % (cls.__module__, cls.__name__)


def load_config(config):
  """Loads dictionary from config file.

  The currently supported file format is YAML and JSON.

  The file format is determined by the file extension:

  - YAML: `.yaml`, `.yml`
  - JSON: `.json`

  The config file must contain a representation that will be deserialized into
  a single `dict`. Additional dictionaries (e.g. from YAML) are ignored.
  """
  fmt = os.path.splitext(config)[1][1:].lower()
  with open(config, 'rb') as f:
    data = CONFIG_LOADER[fmt](f) or {None: None}
  if not isinstance(data, dict) or len(data) != 1:
    # TODO: Add error message
    raise TypeError()

  return data
