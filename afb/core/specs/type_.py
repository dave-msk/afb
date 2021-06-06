from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from afb.utils import fn_util
from afb.utils import misc


class TypeSpec(object):

  def markdown_tmpl(self):
    iter_fn = fn_util.IterDfsOp(lambda item: item.markdown_proc_fn())
    return iter_fn(self)

  def align_inputs(self, args):
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
      return item, fn_util.IterDfsOp.NONE
    ts_cls = _TS_MAP[type(item)]
    return fn_util.IterDfsOp.NONE, (ts_cls.fuse_subspecs, ts_cls.iter_raw(item))

  @classmethod
  def fuse_inputs(cls, *args):
    raise NotImplementedError()

  @classmethod
  def iter_raw(cls, raw_spec):
    raise NotImplementedError()

  @classmethod
  def fuse_subspecs(cls, *args):
    raise NotImplementedError()


class _ClassTypeSpec(TypeSpec):

  def __init__(self, cls):
    self._cls = cls

  def align_inputs(self, args):
    yield self._cls, args

  def markdown_proc_fn(self):
    md_str = "[%s]({%s})" % (self._cls.__name__,
                             misc.cls_to_qualname_id(self._cls))
    return (md_str, {self._cls}), fn_util.IterDfsOp.NONE

  @classmethod
  def fuse_inputs(cls, *args):
    return args[0]

  @classmethod
  def fuse_subspecs(cls, *args):
    assert len(args) == 1 and isinstance(args[0], _ClassTypeSpec)
    return args[0]

  @classmethod
  def iter_raw(cls, raw_spec):
    assert isinstance(raw_spec, type)
    yield cls(raw_spec)


class _ListTypeSpec(TypeSpec):

  def __init__(self, entry_spec):
    self._ts = entry_spec

  def align_inputs(self, args):
    # TODO: Add type validation for `args`
    return ((self._ts, arg) for arg in args)

  def markdown_proc_fn(self):
    stack_entry = (_MarkdownFuseFn("[%s]"), iter((self._ts,)))
    return fn_util.IterDfsOp.NONE, stack_entry

  @classmethod
  def fuse_inputs(cls, *args):
    return args

  @classmethod
  def fuse_subspecs(cls, *args):
    assert len(args) == 1 and isinstance(args[0], TypeSpec)
    return cls(args[0])

  @classmethod
  def iter_raw(cls, raw_spec):
    yield raw_spec[0]


class _DictTypeSpec(TypeSpec):
  def __init__(self, key_spec, value_spec):
    self._ks = key_spec
    self._vs = value_spec

  def align_inputs(self, args):
    # TODO: Add type validation for `args`
    for k, v in args.items():
      yield self._ks, k
      yield self._vs, v

  def markdown_proc_fn(self):
    fuse_fn = _MarkdownFuseFn("{%s: %s}")
    return fn_util.IterDfsOp.NONE, (fuse_fn, iter((self._ks, self._vs)))

  @classmethod
  def fuse_inputs(cls, *args):
    assert not len(args) & 1
    return {args[i << 1]: args[(i << 1) + 1] for i in range(len(args) // 2, 2)}

  @classmethod
  def fuse_subspecs(cls, *args):
    assert len(args) == 2 and all(isinstance(ts, TypeSpec) for ts in args)
    return cls(*args)

  @classmethod
  def iter_raw(cls, raw_spec):
    k, v = next(iter(raw_spec))
    yield k
    yield v


class _TupleTypeSpec(TypeSpec):

  def __init__(self, *entry_specs):
    self._specs = entry_specs

  def align_inputs(self, args):
    # TODO: Add type validation for `args`
    for pair in zip(self._specs, args):
      yield pair

  def markdown_proc_fn(self):
    md_str = "(%s)" % ", ".join("%s" for _ in self._specs)
    fuse_fn = _MarkdownFuseFn(md_str)
    return fn_util.IterDfsOp.NONE, (fuse_fn, iter(self._specs))

  @classmethod
  def fuse_inputs(cls, *args):
    return tuple(args)

  @classmethod
  def fuse_subspecs(cls, *args):
    assert len(args) and all(isinstance(ts, TypeSpec) for ts in args)
    return cls(*args)

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
