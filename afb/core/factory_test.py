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

from absl.testing import absltest

from afb.core import factory as fct_lib
from afb.core.specs import param
from afb.core.specs import type_
from afb.utils import errors
from afb.utils import test_helpers as helpers


def _create_factory(cls, key, **kwargs):
  args = helpers.factory_spec(cls, key, **kwargs)
  args["fn"] = args.pop("factory")
  return fct_lib.Factory(cls, **args)


class SignatureTest(absltest.TestCase):
  def test_create(self):
    fct_spec = helpers.factory_spec(helpers.Adder, "create/ints/with-defaults")

    sut = fct_lib.Signature.create(fct_spec["factory"], fct_spec["signature"])

    self.assertSetEqual(sut.required, {"v1", "v2", "v4"})
    self.assertSetEqual(sut.names, {"v1", "v2", "v3", "v4"})
    self.assertIsInstance(sut["v1"], param.ParameterSpec)
    self.assertIsInstance(sut["v2"], param.ParameterSpec)
    self.assertIsInstance(sut["v3"], param.ParameterSpec)
    self.assertIsInstance(sut["v4"], param.ParameterSpec)
    self.assertIn("v1", sut)
    self.assertIn("v2", sut)
    self.assertIn("v3", sut)
    self.assertIn("v4", sut)


class FactoryTest(absltest.TestCase):
  def test_call_as_fuse_fn(self):
    fct = _create_factory(helpers.Adder, "create/floats")

    result = fct.call_as_fuse_fn("v1", 1.0, "v2", 2.0)

    self.assertIsInstance(result, helpers.Adder)
    self.assertAlmostEqual(result.value, 3.0)

  def test_call(self):
    fct = _create_factory(helpers.Adder, "create/floats")

    result = fct(v1=1.0, v2=2.0)

    self.assertIsInstance(result, helpers.Adder)
    self.assertAlmostEqual(result.value, 3.0)

  def test_parse_inputs_simple(self):
    fct = _create_factory(helpers.Adder, "create/ints")

    result = fct.parse_inputs({"v1": 1, "v2": 2})

    self.assertTupleEqual(next(result), (None, "v1"))
    t, v = next(result)
    self.assertIsInstance(t, type_.TypeSpec)
    self.assertEqual(v, 1)
    self.assertTupleEqual(next(result), (None, "v2"))
    t, v = next(result)
    self.assertIsInstance(t, type_.TypeSpec)
    self.assertEqual(v, 2)

  def test_merge_inputs(self):
    fct = _create_factory(helpers.Adder, "create/ints", defaults={"v1": 1})

    r1 = fct.merge_inputs(v2=2)
    r2 = fct.merge_inputs(v1=3, v2=4)

    self.assertDictEqual(r1, {"v1": 1, "v2": 2})
    self.assertDictEqual(r2, {"v1": 3, "v2": 4})

  def test_merge_inputs_missing_args(self):
    fct = _create_factory(helpers.Adder,
                          "create/ints/with-defaults",
                          defaults={"v1": 1})

    with self.assertRaisesRegex(errors.ArgumentError,
                                "Missing required arguments"):
      fct.merge_inputs()

    with self.assertRaisesRegex(errors.ArgumentError,
                                "Missing required arguments"):
      fct.merge_inputs(v2=1)

    with self.assertRaisesRegex(errors.ArgumentError,
                                "Missing required arguments"):
      fct.merge_inputs(v1=1, v2=2, v3=3)

  def test_merge_inputs_invalid_args(self):
    fct = _create_factory(helpers.Adder, "create/ints", defaults={"v1": 1})

    with self.assertRaisesRegex(errors.ArgumentError, "Invalid arguments"):
      fct.merge_inputs(v3=1)

    with self.assertRaisesRegex(errors.ArgumentError, "Invalid arguments"):
      fct.merge_inputs(v1=1, v2=2, v3=3)


if __name__ == "__main__":
  absltest.main()
