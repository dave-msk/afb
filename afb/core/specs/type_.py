from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from afb.core.specs import obj_
from afb.utils import const
from afb.utils import fn_util
from afb.utils import misc


class TypeSpec(object):

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
  def fuse_inputs(cls, *args):
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
  def fuse_inputs(cls, *args):
    return args[0]

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
  def fuse_inputs(cls, *args):
    return args

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
  def fuse_inputs(cls, *args):
    assert not len(args) & 1
    return {args[i << 1]: args[(i << 1) + 1] for i in range(len(args) // 2, 2)}

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
