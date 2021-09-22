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
import copy
import inspect
import io

from afb.core.specs import param
from afb.utils import errors
from afb.utils import fn_util
from afb.utils import misc
from afb.utils import validate


class Factory(object):
  def __init__(self,
               cls,
               fn,
               signature,
               descriptions=None,
               defaults=None):
    validate.is_type(cls, type, "cls")
    validate.is_callable(fn, "fn")
    self._cls = cls
    self._fn = fn
    if not isinstance(signature, Signature):
      signature = Signature.create(fn, signature)
    self._sig = signature
    short, long = _normalize_descriptions(descriptions or fn.__doc__)
    self._short_desc = short
    self._long_desc = long
    self._defaults = defaults or {}

  def parse_inputs(self, inputs):
    assert inputs is None or isinstance(inputs, dict)
    inputs = self.merge_inputs(**(inputs or {}))
    for k, v in inputs.items():
      yield None, k
      yield self._sig[k].type, v

  def merge_inputs(self, **kwargs):
    # 1. Merge inputs
    merged = dict(self._defaults)
    merged.update(kwargs)

    # 2. Validate merged arguments
    # 2.1 Arguments validity check
    merged_names = set(merged)
    inv_args = merged_names - self._sig.names
    if inv_args:
      raise errors.ArgumentError("Invalid arguments:\n"
                                 "Expected: {}\nGiven: {}\nInvalid: {}"
                                 .format(sorted(self._sig.names),
                                         sorted(merged_names),
                                         sorted(inv_args)))

    # 2.2 Required arguments check
    missing = self._sig.required - merged_names
    if missing:
      raise errors.ArgumentError("Missing required arguments.\n"
                                 "Required: {}\nGiven: {}\nMissing: {}"
                                 .format(sorted(self._sig.required),
                                         sorted(merged_names),
                                         sorted(missing)))

    return merged

  def markdown_item_tmpl(self):
    return "[`{key}`]({path}): %s" % self._short_desc

  def markdown_doc_tmpl(self):
    with io.StringIO() as tmpl:
      tmpl.write("# {class_name} - `{factory_key}`\n\n")
      tmpl.write("## Description\n\n**%s**\n\n" % self._short_desc)
      if self._long_desc:
        tmpl.write("%s\n\n" % self._long_desc)
      tmpl.write("## Parameters\n\n")

      arg_line = "- %s`%s`:\n"
      type_line = "  - Type: %s\n"
      desc_line = "  - Description: %s\n"

      all_classes = set()

      for k, p in self._sig:
        tmpl.write(arg_line % ("" if p.required else "(optional) ", k))
        md_str, classes = p.type.markdown_tmpl()
        tmpl.write(type_line % md_str)
        tmpl.write(desc_line % p.description)
        all_classes.update(classes)

      return tmpl.getvalue(), all_classes

  def call_as_fuse_fn(self, *args):
    kwargs = fn_util.varargs_to_kwargs(*args)
    return self(**kwargs)

  @property
  def defaults(self):
    return copy.deepcopy(self._defaults)

  @property
  def signature(self):
    return copy.deepcopy(self._sig)

  @property
  def short_description(self):
    return self._short_desc

  @property
  def long_description(self):
    return self._long_desc

  def __call__(self, **kwargs):
    instance = self._fn(**kwargs)
    if not isinstance(instance, self._cls):
      raise TypeError("Expected output of class `{}`. Returned: {}, Class: `{}`"
                      .format(misc.qualname(self._cls),
                              instance,
                              misc.qualname(type(instance))))
    return instance


class Signature(object):
  def __init__(self, ordered_param_specs, required):
    self._ordered_param_specs = ordered_param_specs
    self._required = required

  @property
  def required(self):
    return set(self._required)

  @property
  def names(self):
    return set(self._ordered_param_specs)

  def __getitem__(self, item):
    return self._ordered_param_specs[item]

  def __contains__(self, item):
    return item in self._ordered_param_specs

  def __iter__(self):
    return iter(self._ordered_param_specs.items())

  @classmethod
  def create(cls, fn, param_specs):
    param_specs = collections.OrderedDict(param_specs)

    required = collections.OrderedDict()
    optional = collections.OrderedDict()
    missing = []

    fn_arg_spec = fn_util.FnArgSpec.parse(fn)
    for k in fn_arg_spec.required:
      if k in param_specs:
        required[k] = param.ParameterSpec.parse(param_specs.pop(k))
      else:
        missing.append(k)

    if missing:
      raise errors.SignatureError("Missing required parameters: {}"
                                  .format(missing))

    for k in fn_arg_spec.optional:
      if k in param_specs:
        ps = param.ParameterSpec.parse(param_specs.pop(k))
        [optional, required][ps.required][k] = ps

    if param_specs:
      if not fn_arg_spec.kwargs:
        raise errors.SignatureError("No such parameters: {}"
                                    .format(list(param_specs)))

      for k, p in param_specs.items():
        ps = param.ParameterSpec.parse(p)
        [optional, required][ps.required][k] = ps

    required_names = set(required)
    ordered_param_specs = collections.OrderedDict(required)
    ordered_param_specs.update(optional)
    return cls(ordered_param_specs, required_names)


def _normalize_descriptions(desc):
  if isinstance(desc, str):
    lines = inspect.cleandoc(desc).split("\n")
    return lines[0], "\n".join(lines[1:]).strip()

  valid_keys = {"short", "long"}
  desc = desc or {"short": ""}
  if (not isinstance(desc, dict) or
      "short" not in desc or
      (set(desc) - valid_keys)):
    raise errors.InvalidFormatError(
        "The factory description must either be `None`, a `str`, or a `dict` "
        "including short description as \"short\" (required) and long "
        "description as \"long\" (optional). Given: {}".format(desc))
  short = desc["short"]
  long = desc.get("long", "")
  if not isinstance(short, str) or not isinstance(long, str):
    raise TypeError("The descriptions must be strings. Given: {}".format(desc))
  return short, long
