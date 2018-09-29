from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import yaml
import json
import os

CONFIG_LOADER = {
    'yaml': yaml.load,
    'yml': yaml.load,
    'json': json.load
}


def get_load_config():
  return load_config, {'config': str}


def load_config(config):
  format = os.path.splitext(config)[1][1:]
  with open(config, 'rb') as f:
    data = CONFIG_LOADER[format](f)
  return data
