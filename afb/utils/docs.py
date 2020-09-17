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

import inspect
import os


def export_class_markdown(mfr,
                          export_dir,
                          cls_dir_fn,
                          cls_desc_name,
                          factory_doc_path_fn,
                          static_doc_path_fn):
  cls = mfr.cls
  cls_name = cls.__qualname__
  cls_doc = inspect.cleandoc(cls.__doc__ or "")
  dynamic_fcts = mfr.dynamic_factories
  static_fcts = mfr.static_factories

  def create_format_list_entry_fn(path_fn):
    def format_factory_list_entry(key, doc):
      doc_path = os.path.join(".", path_fn(key))
      description = doc["descriptions"]["short"]
      entry = "[`%s`](%s): %s" % (key, doc_path, description)
      return entry
    return format_factory_list_entry

  title = "# %s" % cls_name
  description = "## Description\n\n%s" % cls_doc
  format_factory_list_entry = create_format_list_entry_fn(factory_doc_path_fn)
  factory_doc_list = ["  - %s" % format_factory_list_entry(k, d)
                      for k, d in sorted(dynamic_fcts.items())]
  factory_doc_list_str = "\n".join(factory_doc_list)
  factories_doc = "## Factories\n\n%s\n" % factory_doc_list_str

  format_static_list_entry = create_format_list_entry_fn(static_doc_path_fn)
  statics_doc_list = ["  - %s" % format_static_list_entry(k, d)
                      for k, d in sorted(static_fcts.items())]
  statics_doc_list_str = "\n".join(statics_doc_list)
  statics_doc = "## Static\n\n%s\n" % statics_doc_list_str

  cls_desc_path = os.path.join(export_dir,
                               cls_dir_fn(cls),
                               "%s.md" % cls_desc_name)
  make_dir(cls_desc_path)
  with open(cls_desc_path, 'w') as f:
    f.write("\n\n".join((title, description, factories_doc, statics_doc)))


def export_factories_markdown(mfr,
                              export_dir,
                              cls_dir_fn,
                              cls_desc_name,
                              factory_doc_path_fn,
                              static=False):
  cls = mfr.cls
  cls_dir = cls_dir_fn(cls)
  cls_name = cls.__qualname__
  factories = mfr.static_factories if static else mfr.dynamic_factories

  for k, entry in factories.items():
    title = "# %s - `%s`" % (cls_name, k)

    short = inspect.cleandoc(entry["descriptions"]["short"])
    long = inspect.cleandoc(entry["descriptions"]["long"])
    description = "## Description\n\n**%s**" % short
    if long:
      description = "%s\n\n%s" % (description, long)

    factory_doc_path_rel = os.path.join(cls_dir, factory_doc_path_fn(k))
    depth = len(factory_doc_path_rel.split('/')) - 1
    doc_root_rel = '/'.join([".."] * depth)

    def format_arg_list_entry(name, arg, optional):
      arg_line = "- %s`%s`:" % ("(optional) " if optional else "", name)
      type_spec = arg["type"]
      type_line = make_type_line(
          type_spec, doc_root_rel, cls_dir_fn, cls_desc_name, full_type=False)
      full_type_line = make_type_line(
          type_spec, doc_root_rel, cls_dir_fn, cls_desc_name, full_type=True)

      desc_line = "  - Description: %s" % arg["description"]
      return "\n".join((arg_line, type_line, full_type_line, desc_line))

    sig = entry["sig"]
    rqd_args = entry["rqd_args"]
    arg_doc_list = []
    for k, p in sig.items():
      optional = k not in rqd_args
      arg_doc_list.append(format_arg_list_entry(k, p, optional))

    signature_doc = "## Arguments\n\n%s" % "\n".join(arg_doc_list)
    factory_doc = "\n\n".join((title, description, signature_doc))

    factory_doc_path = os.path.join(export_dir, factory_doc_path_rel)
    make_dir(factory_doc_path)
    with open(factory_doc_path, 'w') as f:
      f.write(factory_doc)


def make_type_line(type_spec, root, cls_dir_fn, cls_desc_name, full_type=False):
  prefix = "  - %sType: " % ("Full " if full_type else "")

  def get_type_entity(type_spec):
    path = os.path.join(root, cls_dir_fn(type_spec), "%s.md" % cls_desc_name)
    name = type_spec.__qualname__
    if full_type:
      name = "%s.%s" % (type_spec.__module__, name)
    return "[`%s`](%s)" % (name, path)

  body = get_type_spec_repr(type_spec, get_type_entity)
  return "%s%s" % (prefix, body)


def get_type_spec_repr(type_spec, link_fn):
  if isinstance(type_spec, list):
    return "[%s]" % get_type_spec_repr(type_spec[0], link_fn)
  if isinstance(type_spec, dict):
    kt, vt = next(iter(type_spec.items()))
    return "{%s: %s}" % (get_type_spec_repr(kt, link_fn),
                         get_type_spec_repr(vt, link_fn))
  if isinstance(type_spec, tuple):
    return "(%s)" % ", ".join(get_type_spec_repr(t, link_fn) for t in type_spec)
  if isinstance(type_spec, type):
    return link_fn(type_spec)

  # This line should be unreachable
  raise TypeError("Unknown type: {}".format(type_spec))


def make_dir(path):
  dirname = os.path.dirname(path)
  os.makedirs(dirname, exist_ok=True)
