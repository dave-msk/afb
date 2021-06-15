from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
import copy
import inspect
import io

from afb.core import specs
from afb.utils import errors
from afb.utils import fn_util


class Factory(object):
  def __init__(self, cls, fn, signature, descriptions=None, defaults=None):
    # TODO: Check if `factory` is callable
    assert isinstance(cls, type)

    self._cls = cls
    self._fn = fn
    self._rqd, self._sig = _format_signature(fn, signature)
    self._all_args = set(self._sig)
    desc = _normalized_factory_descriptions(descriptions or fn.__doc__)
    self._short_desc = inspect.cleandoc(desc["short"])
    self._long_desc = inspect.cleandoc(desc["long"])
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
    inv_args = merged_names - self._all_args
    if inv_args:
      raise ValueError("Invalid arguments:\n"
                       "Expected: {}\nGiven: {}\nInvalid: {}"
                       .format(sorted(self._all_args),
                               sorted(merged_names),
                               sorted(inv_args)))

    # 2.2 Required arguments check
    missing = self._rqd - merged_names
    if missing:
      raise TypeError("Missing required arguments.\n"
                      "Required: {}\nGiven: {}\nMissing: {}"
                      .format(sorted(self._rqd),
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

      for k, p in self._sig.items():
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
      raise TypeError()
    return instance


def _format_signature(fn, signature):
  signature = collections.OrderedDict(signature)

  rqd_sig = collections.OrderedDict()
  opt_sig = collections.OrderedDict()
  missing = []

  fn_arg_spec = fn_util.FnArgSpec.from_fn(fn)
  for k in fn_arg_spec.required:
    if k in signature:
      rqd_sig[k] = specs.ParameterSpec.from_raw(signature.pop(k))
    else:
      missing.append(k)

  if missing:
    raise errors.SignatureError("Missing required parameters: {}"
                                .format(missing))

  for k in fn_arg_spec.optional:
    if k in signature:
      opt_sig[k] = specs.ParameterSpec.from_raw(signature.pop(k))

  if signature:
    if not fn_arg_spec.kwargs:
      raise errors.SignatureError("No such parameters: {}"
                                  .format(list(signature)))
    for k, p in signature.items():
      pspec = specs.ParameterSpec.from_raw(p)
      [opt_sig, rqd_sig][pspec.required][k] = pspec

  rqds = set(rqd_sig)
  ordered_sig = collections.OrderedDict(rqd_sig)
  ordered_sig.update(opt_sig)
  return rqds, ordered_sig


def _normalized_factory_descriptions(desc):
  if isinstance(desc, str):
    lines = inspect.cleandoc(desc).split("\n")
    return {"short": lines[0], "long": "\n".join(lines[1:]).strip()}

  valid_keys = {"short", "long"}
  desc = desc or {"short": ""}
  if (not isinstance(desc, dict) or
      "short" not in desc or
      (set(desc) - valid_keys)):
    raise ValueError("The factory description must either be `None`, a `str`,"
                     "or a `dict` including short description as \"short\" "
                     "(required) and long description as \"long\" (optional)."
                     "Given: {}".format(desc))
  short = desc["short"]
  long = desc.get("long", "")
  if not isinstance(short, str) or not isinstance(long, str):
    raise TypeError("The descriptions must be strings. Given: {}".format(desc))
  return {"short": short, "long": long}
