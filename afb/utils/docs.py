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
import os
import six


def export_class_markdown(mfr,
                          export_dir,
                          cls_dir_fn,
                          cls_desc_name,
                          factory_doc_path_fn):
  cls = mfr.cls
  cls_name = cls.__qualname__
  cls_doc = inspect.cleandoc(cls.__doc__ or "")
  factories = mfr.factories

  def format_factory_list_entry(key, doc):
    doc_path = os.path.join(".", factory_doc_path_fn(key))
    description = doc["descriptions"]["short"]
    entry = "[`%s`](%s): %s" % (key, doc_path, description)
    return entry

  title = "# %s" % cls_name
  description = "## Description\n\n%s" % cls_doc
  factory_doc_list = ["  - %s" % format_factory_list_entry(k, d)
                      for k, d in sorted(six.iteritems(factories))]
  factory_doc_list_str = "\n".join(factory_doc_list)
  factories_doc = "## Factories\n\n%s\n" % factory_doc_list_str

  cls_desc_path = os.path.join(export_dir,
                               cls_dir_fn(cls),
                               "%s.md" % cls_desc_name)
  make_dir(cls_desc_path)
  with open(cls_desc_path, 'w') as f:
    f.write("\n\n".join((title, description, factories_doc)))


def export_factories_markdown(mfr,
                              export_dir,
                              cls_dir_fn,
                              cls_desc_name,
                              factory_doc_path_fn):
  cls = mfr.cls
  cls_dir = cls_dir_fn(cls)
  cls_name = cls.__qualname__

  for k, entry in six.iteritems(mfr.factories):
    title = "# %s - `%s`" % (cls_name, k)

    short = inspect.cleandoc(entry["descriptions"]["short"])
    long = inspect.cleandoc(entry["descriptions"]["long"])
    description = "## Description\n\n**%s**" % short
    if long:
      description = "%s\n\n%s" % (description, long)

    factory_doc_path_rel = os.path.join(cls_dir, factory_doc_path_fn(k))
    depth = len(factory_doc_path_rel.split('/')) - 1
    doc_root_rel = '/'.join([".."] * depth)

    def format_arg_list_entry(arg, arg_sig, optional):
      arg_line = "- %s`%s`:" % ("(optional) " if optional else "", arg)
      arg_type = arg_sig["type"]
      type_line = make_type_line(
          arg_type, doc_root_rel, cls_dir_fn, cls_desc_name, full_type=False)
      full_type_line = make_type_line(
          arg_type, doc_root_rel, cls_dir_fn, cls_desc_name, full_type=True)

      desc_line = "  - Description: %s" % arg_sig["description"]
      return "\n".join((arg_line, type_line, full_type_line, desc_line))

    fn = entry["fn"]
    sig = entry["sig"]
    rqd_args = entry["rqd_args"]
    parameters = inspect.signature(fn).parameters
    arg_doc_list = []
    for p in parameters:
      if p not in sig:
        continue
      arg_sig = sig[p]
      optional = p not in rqd_args
      arg_doc_list.append(format_arg_list_entry(p, arg_sig, optional))

    signature_doc = "## Arguments\n\n%s" % "\n".join(arg_doc_list)
    factory_doc = "\n\n".join((title, description, signature_doc))

    factory_doc_path = os.path.join(export_dir, factory_doc_path_rel)
    make_dir(factory_doc_path)
    with open(factory_doc_path, 'w') as f:
      f.write(factory_doc)


def make_type_line(arg_type, root, cls_dir_fn, cls_desc_name, full_type=False):
  prefix = "  - %sType: " % ("Full " if full_type else "")

  def get_type_entity(arg_type):
    path = os.path.join(root, cls_dir_fn(arg_type), "%s.md" % cls_desc_name)
    name = arg_type.__qualname__
    if full_type:
      name = "%s.%s" % (arg_type.__module__, name)
    return "[`%s`](%s)" % (name, path)

  if isinstance(arg_type, type):
    body = get_type_entity(arg_type)
  elif isinstance(arg_type, list):
    arg_type = arg_type[0]
    body = "[%s]" % get_type_entity(arg_type)
  elif isinstance(arg_type, tuple):
    body = "(%s)" % ", ".join(get_type_entity(t) for t in arg_type)
  elif isinstance(arg_type, dict):
    kt, vt = iter(six.iteritems(arg_type)).__next__()
    body = "{%s: %s}" % (get_type_entity(kt), get_type_entity(vt))
  else:
    # This line will not be reached as an error will be raised at factory
    # registration time.
    raise TypeError("Unknown type: {}".format(arg_type))

  return "%s%s" % (prefix, body)


def make_dir(path):
  dirname = os.path.dirname(path)
  os.makedirs(dirname, exist_ok=True)
