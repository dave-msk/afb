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

from afb.core.specs import obj_
from afb.utils import algorithms as algs
from afb.utils import const
from afb.utils import errors
from afb.utils import misc


class TypeSpec(object):
  """Type specification of parameter.

  This class is an abstraction of parameter types for a factory. The expected
  type of each parameter of a factory has to be specified for `afb` to look for
  the right `Manufacturer` in the inputs preparation stage.

  The type specification (type spec) has the following grammar:

  CTS (class type spec) := class
  LTS (list type spec)  := [TS]
  DTS (dict type spec)  := {TS: TS}
  TTS (tuple type spec) := (TS, ..., TS)
  TS  (type spec)       := CTS | LTS | DTS | TTS

  In detail, a type spec can be one of the following:

    * CTS: Any class or type (e.g.: `str`, `MyClass`, ...)
    * LTS: A singleton list of a type spec (e.g.: `[MyClass]`, `[{str: int}]`,
           ...). This means the parameter is a homogeneous list of objects of
           type specified by the containing spec.
    * DTS: A singleton dict with both the key and value being a type spec
           (e.g.: `{MyClass1: [int]}`, `{str: MyClass2}`, ...). This means the
           parameter is a homogeneous dict with keys and values conforming
           to the key and value type specs respectively.
    * TTS: A tuple of type specs (e.g.: ([int], {str: MyClass}), ...).
           This means the parameter is a tuple of objects with each element
           conforms to the type spec at its corresponding position.

  Each kind of type spec corresponds to a particular form of input, called
  Manifest, which the argument must conform to. It has the following
  grammar:

  CM (class manifest) := object | {key: inputs} | {"key": key, "inputs": inputs}
  LM (list manifest)  := [M, ...]
  DM (dict manifest)  := {M_k: M_v, ...} | [{"key": M_k, "value": M_v}, ...]
  TM (tuple manifest) := (M, ..., M)
  M  (manifest)       := CM | LM | DM | TM

  The following describes the manifest that corresponds to each kind of
  type spec above:

    * CM: (CTS) Either of the following:
      * An instance of the target class
      * A singleton dict with the factory key as key, and a dict
        mapping each parameter to its manifest for the factory as value.
      * A dict with two items:
        * `"key"`: Factory key.
        * `"inputs"`: dict mapping each parameter to its manifest.
    * LM: (LTS) A list / tuple of arbitrary length of object specs of the
        element type spec.
    * DM: (DTS) Either of the following:
      * A dict of arbitrary length with keys and values being manifests
        for the key and value type spec respectively.
      * A list / tuple of dicts each with the following items:
        * `"key"`: manifest for the key.
        * `"value"`: manifest for the value.
    * TM: (TTS) A list / tuple of manifests each conforms to its
        corresponding type spec. Each TS in the original TTS MUST have
        an manifest.

  This is the base class of the certain kind of type specs described above.
  DO NOT instantiate the classes directly, use `TypeSpec.create` instead.
  """
  def markdown_tmpl(self):
    iter_fn = algs.PostorderDFS(lambda item: item.markdown_proc())
    return iter_fn(self)

  def parse_manifest(self, manifest):
    raise NotImplementedError("Must be implemented in descendants.")

  def markdown_proc(self):
    raise NotImplementedError("Must be implemented in descendants.")

  @classmethod
  def parse(cls, spec):
    if isinstance(spec, TypeSpec):
      return spec

    if type(spec) not in _TS_MAP:
      raise TypeError("`spec` has to be a `type`, `list`, `dict` or `tuple`. "
                      "Given: {}".format(misc.qualname(type(spec))))

    iter_fn = algs.PostorderDFS(cls._parse_proc)
    return iter_fn(spec)

  @classmethod
  def _parse_proc(cls, item):
    if isinstance(item, cls):
      return algs.ItemResult(item)
    ts_cls = _TS_MAP[type(item)]
    return algs.NodeResult(ts_cls.fuse_subspecs, ts_cls.iter_raw(item))

  @classmethod
  def pack(cls, *inputs):
    raise NotImplementedError("Must be implemented in descendants.")

  @classmethod
  def iter_raw(cls, raw_spec):
    raise NotImplementedError("Must be implemented in descendants.")

  @classmethod
  def fuse_subspecs(cls, *specs):
    raise NotImplementedError("Must be implemented in descendants.")


class _ClassTypeSpec(TypeSpec):
  def __init__(self, cls):
    self._cls = cls

  def parse_manifest(self, manifest):
    if obj_.is_direct_object(manifest, self._cls):
      yield self._cls, manifest
      return

    obj_spec = obj_.ObjectSpec.parse(manifest)
    yield self._cls, obj_spec

  def markdown_proc(self):
    md_str = "[%s]({%s})" % (self._cls.__name__,
                             misc.qualname_id(self._cls))
    return algs.ItemResult((md_str, {self._cls}))

  @classmethod
  def pack(cls, *inputs):
    return inputs[0]

  @classmethod
  def fuse_subspecs(cls, *specs):
    assert len(specs) == 1 and isinstance(specs[0], _ClassTypeSpec)
    return specs[0]

  @classmethod
  def iter_raw(cls, raw_spec):
    assert isinstance(raw_spec, type)
    yield cls(raw_spec)


class _ListTypeSpec(TypeSpec):

  def __init__(self, entry_spec):
    self._ts = entry_spec

  def parse_manifest(self, manifest):
    if not isinstance(manifest, (tuple, list)):
      raise errors.InvalidFormatError(
          "Manifest expected to be a `list` or `tuple` for ListTypeSpec. "
          "Given: {}".format(manifest))
    for spec in manifest:
      yield self._ts, spec

  def markdown_proc(self):
    return algs.NodeResult(_MarkdownFuseFn("\\[%s\\]"),
                              iter((self._ts,)))

  @classmethod
  def pack(cls, *inputs):
    return inputs

  @classmethod
  def fuse_subspecs(cls, *specs):
    assert len(specs) == 1 and isinstance(specs[0], TypeSpec)
    return cls(specs[0])

  @classmethod
  def iter_raw(cls, raw_spec):
    yield raw_spec[0]


class _DictTypeSpec(TypeSpec):
  def __init__(self, key_spec, value_spec):
    self._ks = key_spec
    self._vs = value_spec

  def parse_manifest(self, manifest):
    if isinstance(manifest, dict):
      iterable = manifest.items()
    elif isinstance(manifest, (tuple, list)):
      iterable = manifest
    else:
      raise errors.InvalidFormatError(
          "Expected manifest formats for DictTypeSpec:\n"
          "1. {{M_k: M_v, ...}}\n"
          "2. [{{\"key\": M_k, \"value\": M_v}}, ...]\n"
          "Given: {}".format(manifest))

    for pair in iterable:
      if isinstance(pair, (tuple, list)) and len(pair) == 2:
        k, v = pair
      elif isinstance(pair, dict) and set(pair) == const.KEY_VALUE:
        k, v = pair[const.KEY], pair[const.VALUE]
      else:
        raise errors.InvalidFormatError(
          "Expected manifest formats for DictTypeSpec:\n"
          "1. {{M_k: M_v, ...}}\n"
          "2. [{{\"key\": M_k, \"value\": M_v}}, ...]\n"
          "Given: {}".format(manifest))
      yield self._ks, k
      yield self._vs, v

  def markdown_proc(self):
    fuse_fn = _MarkdownFuseFn("{%s: %s}")
    return algs.NodeResult(fuse_fn, iter((self._ks, self._vs)))

  @classmethod
  def pack(cls, *inputs):
    assert not len(inputs) & 1
    return {inputs[i << 1]: inputs[(i << 1) + 1]
            for i in range(len(inputs) // 2)}

  @classmethod
  def fuse_subspecs(cls, *specs):
    assert len(specs) == 2 and all(isinstance(ts, TypeSpec) for ts in specs)
    return cls(*specs)

  @classmethod
  def iter_raw(cls, raw_spec):
    assert isinstance(raw_spec, dict) and len(raw_spec) == 1
    k, v = next(iter(raw_spec.items()))
    yield k
    yield v


class _TupleTypeSpec(TypeSpec):
  def __init__(self, *entry_specs):
    self._specs = entry_specs
    self._num_elements = len(entry_specs)

  def parse_manifest(self, manifest):
    if (not isinstance(manifest, (tuple, list)) or
        len(manifest) != self._num_elements):
      raise errors.InvalidFormatError(
          "Manifest expected to be `list` or `tuple` with the same length as "
          "the TupleTypeSpec. Given: {}".format(manifest))

    for pair in zip(self._specs, manifest):
      yield pair

  def markdown_proc(self):
    md_str = "(%s)" % ", ".join("%s" for _ in self._specs)
    fuse_fn = _MarkdownFuseFn(md_str)
    return algs.NodeResult(fuse_fn, iter(self._specs))

  @classmethod
  def pack(cls, *args):
    return tuple(args)

  @classmethod
  def fuse_subspecs(cls, *specs):
    assert len(specs) and all(isinstance(ts, TypeSpec) for ts in specs)
    return cls(*specs)

  @classmethod
  def iter_raw(cls, raw_spec):
    for s in raw_spec:
      yield s


class _MarkdownFuseFn(object):
  def __init__(self, fmt):
    self._fmt = fmt

  def __call__(self, *args):
    z = zip(*args)
    s = self._fmt % next(z)
    c = set().union(*next(z))
    if None in c: c.remove(None)
    return s, c


_TS_MAP = {
    type: _ClassTypeSpec,
    list: _ListTypeSpec,
    dict: _DictTypeSpec,
    tuple: _TupleTypeSpec,
}
