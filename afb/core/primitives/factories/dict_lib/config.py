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

import yaml
import json
import os

from afb.core import specs


CONFIG_LOADER = {
    'yaml': yaml.safe_load,
    'yml': yaml.safe_load,
    'json': json.load,
}


def get_load_config():
  sig = {
      "config": specs.ArgumentSpec(
          str,
          description="Path to configuration file containing a "
                      "representation corresponding to a single `dict`."),
  }

  return {"factory": load_config, "signature": sig}


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
    data = CONFIG_LOADER[fmt](f)
  return data
