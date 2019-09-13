from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import yaml
import json
import os

CONFIG_LOADER = {
    'yaml': yaml.load,
    'yml': yaml.load,
    'json': json.load,
}


def get_load_config():
  descriptions = {
      "short": "Loads dictionary from config file.",
      "long":
          """The currently supported file format is YAML and JSON.
          
          The file format is determined by the file extension:
          
          - YAML: `.yaml`, `.yml`
          - JSON: `.json`
          
          The config file must contain a representation that will be
          deserialized into a single `dict`.
          """,
  }

  sig = {
      "config": {
          "type": str,
          "description": "Path to configuration file containing a "
                         "representation corresponding to a single `dict`.",
      },
  }

  return {"factory": load_config, "sig": sig, "descriptions": descriptions}


def load_config(config):
  format = os.path.splitext(config)[1][1:].lower()
  with open(config, 'rb') as f:
    data = CONFIG_LOADER[format](f)
  return data
