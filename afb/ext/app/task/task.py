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

import inspect
import logging
import threading


class Task(object):
  def __init__(self, name):
    self._name = name

  @property
  def name(self):
    return self._name

  def run(self, *args, **kwargs):
    sig = inspect.signature(self._run)
    if "exit_ctx" in sig.parameters:
      with ExitContext() as exit_ctx:
        kwargs["exit_ctx"] = exit_ctx
        self._run(*args, **kwargs)
    else:
      self._run(*args, **kwargs)

  def _run(self, *args, **kwargs):
    raise NotImplementedError("Undefined task logic.")

  def _get_logger(self):
    return logging.getLogger(self.name)


class ExitContext(object):
  def __init__(self):
    self._cleanup_fns = []
    self._lock = threading.Lock()

  def add_cleanup_fn(self, fn):
    if not callable(fn) or inspect.signature(fn).parameters:
      raise ValueError("`fn` must be a zero-argument function.")
    with self._lock:
      self._cleanup_fns.append(fn)

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    with self._lock:
      [f() for f in self._cleanup_fns]
      self._cleanup_fns.clear()
