from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from afb.core.specs import obj_
from afb.utils import const
from afb.utils import fn_util
from afb.utils import misc


class TypeSpec(object):
  """Type specification of parameter.

  This class is an abstraction of parameter types for a factory. The expected
  type of each parameter of a factory has to be specified for `afb` to look for
  the right `Manufacturer` in the inputs preparation stage.

  The type specification (type spec) has the following grammar:

  CTS := class
  LTS := [TS]
  DTS := {TS: TS}
  TTS := (TS, ..., TS)
  TS  := CTS | LTS | DTS | TTS

  In detail, a type spec can be one of the following:

    * CTS: Any class or type (e.g.: `str`, `MyClass`, ...)
    * LTS: A singleton list of a type spec (e.g.: `[MyClass]`, `[{str: int}]`,
           ...). This means the parameter is a homogeneous list of objects of
           type specified by the containing spec.
    * DTS: A singleton dictionary with both the key and value being a type spec
           (e.g.: `{MyClass1: [int]}`, `{str: MyClass2}`, ...). This means the
           parameter is a homogeneous dictionary with keys and values conforming
           to the key and value type specs respectively.
    * TTS: A tuple of type specs (e.g.: ([int], {str: MyClass}), ...).
           This means the parameter is a tuple of objects with each element
           conforms to the type spec at its corresponding position.

  Each kind of type spec corresponds to a particular form of input, called
  Input Specification, which the argument must conform to. It has the following
  grammar:

  OIS := instance | {key: inputs} | {"key": key, "inputs": inputs}
  LIS := [IS, ...]
  DIS := {IS_k: IS_v, ...} | [{"key": IS_k, "value": IS_v}, ...]
  TIS := (IS, ..., IS)
  IS  := OIS | LIS | DIS | TIS

  The following describes the input spec that corresponds to each kind of
  type spec above:

    * OIS: (CTS) Either of the following:
      * An instance of the target class
      * A singleton dictionary with the factory key as key, and a dictionary
        mapping each parameter to its input spec for the factory as value.
      * A dictionary with two items:
        * `"key"`: Factory key.
        * `"inputs"`: Dictionary mapping each parameter to its input spec.
    * LIS: (LTS) A list / tuple of arbitrary length of object specs of the
           element type spec.
    * DIS: (DTS) Either of the following:
      * A dictionary of arbitrary length with keys and values being input specs
        for the key and value type spec respectively.
      * A list / tuple of dictionaries each with the following items:
        * `"key"`: Input spec for the key.
        * `"value"`: Input spec for the value.
    * TIS: (TTS) A list / tuple of input specs each conforms to its
           corresponding type spec. Each TS in the original TTS MUST have
           an input spec.

  This is the base class of the certain kind of type specs described above.
  DO NOT instantiate the classes directly, use `TypeSpec.create` instead.
  """
  def markdown_tmpl(self):
    iter_fn = fn_util.IterDfsOp(lambda item: item.markdown_proc_fn())
    return iter_fn(self)

  def parse_input_spec(self, input_spec):
    raise NotImplementedError()

  def markdown_proc_fn(self):
    raise NotImplementedError()

  @classmethod
  def create(cls, raw_or_spec):
    if isinstance(raw_or_spec, TypeSpec):
      return raw_or_spec

    if type(raw_or_spec) not in _TS_MAP:
      raise TypeError()

    iter_fn = fn_util.IterDfsOp(cls._create_proc_fn)
    return iter_fn(raw_or_spec)

  @classmethod
  def _create_proc_fn(cls, item):
    if isinstance(item, cls):
      return item, misc.NONE
    ts_cls = _TS_MAP[type(item)]
    return misc.NONE, (ts_cls.fuse_subspecs, ts_cls.iter_raw(item))

  @classmethod
  def fuse_inputs(cls, *inputs):
    raise NotImplementedError()

  @classmethod
  def iter_raw(cls, raw_spec):
    raise NotImplementedError()

  @classmethod
  def fuse_subspecs(cls, *specs):
    raise NotImplementedError()


class _ClassTypeSpec(TypeSpec):
  def __init__(self, cls):
    self._cls = cls
    self._is_dict = cls is dict

  def parse_input_spec(self, input_spec):
    if obj_.is_direct_object(input_spec, self._cls):
      yield self._cls, input_spec
      return

    obj_spec = obj_.ObjectSpec.parse(input_spec)
    yield self._cls, obj_spec

  def markdown_proc_fn(self):
    md_str = "[%s]({%s})" % (self._cls.__name__,
                             misc.cls_to_qualname_id(self._cls))
    return (md_str, {self._cls}), misc.NONE

  @classmethod
  def fuse_inputs(cls, *inputs):
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

  def parse_input_spec(self, input_spec):
    # TODO: Add type validation for `args`
    if not isinstance(input_spec, (tuple, list)):
      raise TypeError()
    for spec in input_spec:
      yield self._ts, spec

  def markdown_proc_fn(self):
    stack_entry = (_MarkdownFuseFn("\\[%s\\]"), iter((self._ts,)))
    return misc.NONE, stack_entry

  @classmethod
  def fuse_inputs(cls, *inputs):
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

  def parse_input_spec(self, input_spec):
    # TODO: Add type validation for `input_spec`
    if isinstance(input_spec, dict):
      iterable = input_spec.items()
    elif isinstance(input_spec, (tuple, list)):
      iterable = input_spec
    else:
      raise TypeError()

    for pair in iterable:
      if isinstance(pair, (tuple, list)) and len(pair) == 2:
        k, v = pair
      elif isinstance(pair, dict) and set(pair) == const.KEY_VALUE:
        k, v = pair[const.KEY], pair[const.VALUE]
      else:
        raise TypeError()
      yield self._ks, k
      yield self._vs, v

  def markdown_proc_fn(self):
    fuse_fn = _MarkdownFuseFn("{%s: %s}")
    return misc.NONE, (fuse_fn, iter((self._ks, self._vs)))

  @classmethod
  def fuse_inputs(cls, *inputs):
    assert not len(inputs) & 1
    return {inputs[i << 1]: inputs[(i << 1) + 1]
            for i in range(len(inputs) // 2, 2)}

  @classmethod
  def fuse_subspecs(cls, *specs):
    assert len(specs) == 2 and all(isinstance(ts, TypeSpec) for ts in specs)
    return cls(*specs)

  @classmethod
  def iter_raw(cls, raw_spec):
    k, v = next(iter(raw_spec))
    yield k
    yield v


class _TupleTypeSpec(TypeSpec):
  def __init__(self, *entry_specs):
    self._specs = entry_specs
    self._num_elements = len(entry_specs)

  def parse_input_spec(self, input_spec):
    # TODO: Add type validation for `args`
    if (not isinstance(input_spec, (tuple, list)) or
        len(input_spec) != self._num_elements):
      raise TypeError()
    for pair in zip(self._specs, input_spec):
      yield pair

  def markdown_proc_fn(self):
    md_str = "(%s)" % ", ".join("%s" for _ in self._specs)
    fuse_fn = _MarkdownFuseFn(md_str)
    return misc.NONE, (fuse_fn, iter(self._specs))

  @classmethod
  def fuse_inputs(cls, *args):
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
