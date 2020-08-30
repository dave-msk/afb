# Copyright 2019 Siu-Kei Muk (David). All Rights Reserved.
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

from afb.core import broker as brk_lib
from afb.ext.app import job
from afb.ext.app import task
from afb.ext.app import values


_REGISTRY = {
    job.Job: {
        "job": job.get_job,
    },
    task.Task: {},
    values.Values: {
        "enum/bool": values.make_enum_values(bool),
        "enum/float": values.make_enum_values(float),
        "enum/int": values.make_enum_values(int),
        "enum/job": values.make_enum_values(job.Job),
        "enum/str": values.make_enum_values(str),
        "alg/concat": values.get_concat,
        "alg/dict/prod": values.get_product_in_dict,
        "alg/dict/zip": values.get_zipped_in_dict,
        "alg/prod": values.get_product,
        "alg/zip": values.get_zipped,
    },
}


def make_broker():
  broker = brk_lib.Broker()
  for cls, cls_reg in _REGISTRY.items():
    [broker.add_factory(cls, k, **get_fct())
     for k, get_fct in cls_reg.items()]
  return broker
