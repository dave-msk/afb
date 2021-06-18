from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from afb.core.specs import param


def get_direct():
  sig = {
      "value": param.ParameterSpec(
          object,
          description="Dictionary to be used directly.",
      )
  }

  return {"factory": direct_dict,
          "signature": sig}


def direct_dict(value):
  """Returns input dictionary directly.

  This function returns the input directly to disambiguate from `ObjectSpec`
  raw formats.

  Args:
    value: Dictionary to be used directly.

  Returns:
    The input `value`.
  """
  if not isinstance(value, dict):
    raise TypeError("`dict` expected for `value`. Given: {}".format(value))
  return value
