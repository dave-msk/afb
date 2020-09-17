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

import copy
import itertools

from afb.ext.app.values import values as val_base


def get_zipped_in_dict():
  desc = {
      "short": "",
      "long":
          """
          """,
  }

  def factory(values_map, base=None):
    return _ComposedDictValues(zip, values_map, base=base)

  return {"factory": factory,
          "sig": _ComposedDictValues._SIG,  # pylint: disable=protected-access
          "descriptions": desc}


def get_product_in_dict():
  desc = {
      "short": "",
      "long":
          """
          """,
  }

  def factory(values_map, base=None):
    return _ComposedDictValues(itertools.product, values_map, base=base)

  return {"factory": factory,
          "sig": _ComposedDictValues._SIG,  # pylint: disable=protected-access
          "descriptions": desc}


def get_concat():
  desc = {
      "short": "",
      "long":
          """
          """,
  }

  def factory(values_list):
    return _ComposedValues(itertools.chain, values_list)

  return {"factory": factory,
          "sig": _ComposedValues._SIG,  # pylint: disable=protected-access
          "descriptions": desc}


def get_zipped():
  desc = {
      "short": "",
      "long":
          """
          """,
  }

  def factory(values_list):
    return _ComposedValues(zip, values_list)

  return {"factory": factory,
          "sig": _ComposedValues._SIG,  # pylint: disable=protected-access
          "descriptions": desc}


def get_product():
  desc = {
      "short": "",
      "long":
          """
          """,
  }

  def factory(values_list):
    return _ComposedValues(itertools.product, values_list)

  return {"factory": factory,
          "sig": _ComposedValues._SIG,  # pylint: disable=protected-access
          "descriptions": desc}


class _ComposedDictValues(val_base.Values):
  _SIG = {
      "values_map": {
        "type": {str: val_base.Values},
        "description": "",
      },
      "base": {
        "type": dict,
        "description": "",
      },
  }

  def __init__(self, combine_fn, values_map, base=None):
    self._combine_fn = combine_fn
    self._values_map = values_map
    self._base = base or {}

  def _make_iterator(self):
    keys, vals = list(zip(*list(self._values_map.items.items())))
    its = [v.make_iterator() for v in vals]

    for comb in self._combine_fn(*its):
      out = copy.deepcopy(self._base)
      out.update(dict(zip(keys, comb)))
      yield out

    del its[:]


class _ComposedValues(val_base.Values):
  _SIG = {
      "values_list": {
          "type": [val_base.Values],
          "description": "",
      },
  }

  def __init__(self, combine_fn, values_list):
    self._val_list = values_list
    self._combine_fn = combine_fn

  def _make_iterator(self):
    iterator = self._combine_fn(*[v.make_iterator() for v in self._val_list])
    return iterator
