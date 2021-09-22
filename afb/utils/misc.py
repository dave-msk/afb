# Copyright 2021 (David) Siu-Kei Muk. All Rights Reserved.
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

SEP = "/"
_RESERVED = "afb"
NONE = object()

CONFIG_LOADER = {
    '.yaml': yaml.safe_load,
    '.yml': yaml.safe_load,
    '.json': json.load,
}

_mfr_lib = proxy.ModuleProxy("afb.core.manufacturer")
_dep_lib = proxy.ModuleProxy("afb.utils.deprecation")


def create_mfr(cls, fct_fn_dict, keyword_mode=None):
  _dep_lib.warn("`{}` is deprecated and will be removed in a future version. "
                "Use `Manufacturer.from_dict` instead."
                .format(qualname(create_mfr)))
  if keyword_mode is not None:
    _dep_lib.warn("`keyword_mode` is not used anymore.")
  return _mfr_lib.Manufacturer.from_dict(cls, fct_fn_dict)


def qualname_id(obj, sep="_"):
  fmt = "%s" + sep + "%s"
  return fmt % (obj.__module__.replace(".", sep), obj.__name__)


def qualname(obj):
  if obj.__module__ == "builtins": return obj.__name__
  return "%s.%s" % (obj.__module__, obj.__name__)


def load_config(config):
  """Loads dictionary from config file.

  The currently supported file format is YAML and JSON.

  The file format is determined by the file extension:

  - YAML: `.yaml`, `.yml`
  - JSON: `.json`

  The config file must contain a representation that will be deserialized into
  a single `dict`. Additional dictionaries (e.g. from YAML) are ignored.
  """
  fmt = os.path.splitext(config)[-1].lower()
  with open(config, 'rb') as f:
    data = CONFIG_LOADER[fmt](f) or {None: None}
  if not isinstance(data, dict):
    raise TypeError("File content is not a `dict`. Path: {}, Content: {}"
                    .format(config, data))
  return data


def is_reserved(name):
  return name.split(SEP)[0] == _RESERVED


def join(*args):
  return SEP.join(args)


def join_reserved(*args):
  return join(_RESERVED, *args)
