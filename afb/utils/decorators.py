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


class LazyPropery(object):
  """
  TODO: Add descriptions
  """
  def __init__(self, function):
    self.function = function
    self.name = function.__name__

  def __get__(self, obj, type=None):
    obj.__dict__[self.name] = self.function(obj)
    return obj.__dict__[self.name]


class SetterProperty(object):
  """
  # TODO: Add descriptions. From https://stackoverflow.com/questions/17576009/python-class-property-use-setter-but-evade-getter
  """
  def __init__(self, function):
    self.function = function
    self.__doc__ = function.__doc__

  def __set__(self, obj, value):
    return self.function(obj, value)
