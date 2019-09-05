from afb.core.primitives.bool import create_bool_mfr
from afb.core.primitives.dict import create_dict_mfr
from afb.core.primitives.float import create_float_mfr
from afb.core.primitives.integer import create_int_mfr
from afb.core.primitives.list import create_list_mfr
from afb.core.primitives.string import create_str_mfr
from afb.core.primitives.tuple import create_tuple_mfr


def get_primitives_mfrs():
  mfrs = [create_bool_mfr(),
          create_dict_mfr(),
          create_float_mfr(),
          create_int_mfr(),
          create_list_mfr(),
          create_str_mfr(),
          create_tuple_mfr()]
  return mfrs
