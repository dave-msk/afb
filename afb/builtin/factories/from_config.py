from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


def create_from_config(mfr):
  descriptions = {
      "short": "Constructs object from object specification in config file.",
      "long":
          """This function constructs the object from object specification
          contained in a config file.
    
          Current, only YAML and JSON is supported. The format is determined
          by the file extension, where
    
          - `.yaml`, `yml` -> YAML
          - `.json` -> JSON
    
          The config file must contain exactly one object specification. That
          is, it must contain a singleton dictionary that maps a factory name
          to its parameters.
          """
  }

  sig = {
      "config": {
          "type": str,
          "description": 'Config file in YAML/JSON, containing a single '
                         'object specification for class "{}"'
                         .format(mfr.cls.__name__),
      },
  }

  def from_config(config):
    params = mfr._broker.make(dict, {"load_config": {"config": config}})  # pylint: disable=protected-access
    return mfr._broker.make(mfr.cls, params)  # pylint: disable=protected-access

  return {"factory": from_config, "sig": sig, "descriptions": descriptions}
