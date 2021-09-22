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

import collections

from afb.utils import misc


class PostorderDFS(object):
  def __init__(self, proc_fn):
    self._proc_fn = proc_fn

  def __call__(self, seed):
    stack = collections.deque()
    stack.append(PostorderDFSNode(lambda *x: x[0], (seed,)))
    result = None

    while stack:
      node = stack[-1]

      try:
        item = node.next()
      except StopIteration:
        stack.pop()
        result = node.fuse()
        if stack:
          stack[-1].add(result)
        continue

      proc_result = self._proc_fn(item)
      if proc_result.has_item():
        node.add(proc_result.item)
      if proc_result.node:
        stack.append(proc_result.node)

    return result


class PostorderDFSNode(object):
  def __init__(self, fuse_fn, items):
    self._fuse = fuse_fn
    self._items = items if hasattr(items, "__next__") else iter(items)
    self._fuse_items = []

  def next(self):
    return next(self._items)

  def add(self, item):
    self._fuse_items.append(item)

  def fuse(self):
    return self._fuse(*self._fuse_items)


class ProcResult(object):
  def __init__(self, item=misc.NONE, node=None):
    self._item = item
    self._node = node

  def has_item(self):
    return self._item is not misc.NONE

  @property
  def item(self):
    return self._item

  @property
  def node(self):
    return self._node


class ItemResult(ProcResult):
  def __init__(self, item):
    super(ItemResult, self).__init__(item=item)


class NodeResult(ProcResult):
  def __init__(self, fuse_fn, items):
    super(NodeResult, self).__init__(node=PostorderDFSNode(fuse_fn, items))
