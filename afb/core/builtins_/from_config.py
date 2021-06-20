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

from afb.core.specs import param
from afb.utils import misc


def make_from_config(mfr):
  sig = {
      "config": param.ParameterSpec(
          str,
          description="Config file in YAML/JSON, containing a single "
                      'object specification for class "%s"' % mfr.cls.__name__,
          required=True),
  }

  def from_config(config):
    """Constructs object from object specification in config file.

    This function constructs the object from object specification contained
    in a config file.

    Current, only YAML and JSON is supported. The format is determined by the
    file extension, where

    - `.yaml`, `yml` -> YAML
    - `.json` -> JSON

    The config file must contain exactly one object specification. That is, it
    must contain a singleton dictionary that maps a factory name to its
    parameters.
    """
    params = misc.load_config(config)
    key, args = next(iter(params.items()))
    return mfr.make(method=key, params=args)

  return {"factory": from_config, "signature": sig}
