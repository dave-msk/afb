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

from afb.core import broker as bkr_lib
from afb.core import manufacturer as mfr_lib
from afb.utils import errors
from afb.utils import test_helpers


_FCTS = test_helpers.FCTS
_TrivialClass = test_helpers.TrivialClass
_ValueHolder = test_helpers.ValueHolder
_Adder = test_helpers.Adder


class ManufacturerTest(absltest.TestCase):
  def _create_broker(self, *classes):
    bkr = bkr_lib.Broker()
    [bkr.register(mfr_lib.Manufacturer(cls)) for cls in classes]
    return bkr

  def test_initial_default_is_none(self):
    sut = mfr_lib.Manufacturer(_TrivialClass)
    self.assertIsNone(sut.default)

  def test_default_key_must_be_registered(self):
    sut = mfr_lib.Manufacturer(_TrivialClass)
    with self.assertRaises(KeyError):
      sut.default = "not exist"

  def test_get_non_exist_factory(self):
    sut = mfr_lib.Manufacturer(_TrivialClass)
    self.assertIsNone(sut.get("not exist"))

  def test_register_simple(self):
    sut = mfr_lib.Manufacturer(_ValueHolder)

    key = "create/int"
    sut.register(key, *_FCTS[_ValueHolder][key])

    self.assertIn(key, sut)

  def test_registered_entry_is_callable(self):
    sut = mfr_lib.Manufacturer(_ValueHolder)

    key = "create/int"
    sut.register(key, *_FCTS[_ValueHolder][key])

    self.assertTrue(callable(sut.get(key)))

  def test_register_key_conflict(self):
    sut = mfr_lib.Manufacturer(_ValueHolder)

    key = "create/int"
    sut.register(key, *_FCTS[_ValueHolder][key])

    with self.assertRaisesRegex(errors.KeyConflictError, key):
      sut.register(key, *_FCTS[_ValueHolder][key])

  def test_register_key_override(self):
    sut = mfr_lib.Manufacturer(_ValueHolder)

    key = "create/int"
    sut.register(key,
                 lambda value: _ValueHolder(value),
                 {"value": {"type": int}})
    factory_1 = sut.get(key)
    sut.register(key, *_FCTS[_ValueHolder][key], override=True)
    factory_2 = sut.get(key)

    self.assertIsNot(factory_2, factory_1)

  def test_register_dict(self):
    # Arrange
    sut = mfr_lib.Manufacturer(_ValueHolder)

    # Act
    regs = {
        "create/int": _FCTS[_ValueHolder]["create/int"],
        "create/float": {
            "factory": _FCTS[_ValueHolder]["create/float"][0],
            "signature": _FCTS[_ValueHolder]["create/float"][1],
        },
        "sum/list/int": lambda: _FCTS[_ValueHolder]["sum/list/int"],
        "sum/tuple": lambda: {"factory": _FCTS[_ValueHolder]["sum/tuple"][0],
                              "signature": _FCTS[_ValueHolder]["sum/tuple"][1]},
    }
    sut.register_dict(regs)

    # Assert
    self.assertIn("create/int", sut)
    self.assertIn("create/float", sut)
    self.assertIn("sum/list/int", sut)
    self.assertIn("sum/tuple", sut)

  def test_make_simple(self):
    bkr = self._create_broker(_ValueHolder)
    sut = bkr.get(_ValueHolder)
    key = "create/int"
    sut.register(key, *_FCTS[_ValueHolder][key])

    result = sut.make(key=key, inputs={"value": 1})

    self.assertIsInstance(result, _ValueHolder)
    self.assertEqual(result.value, 1)

  def test_make_with_list_type_spec(self):
    bkr = self._create_broker(_ValueHolder)
    sut = bkr.get(_ValueHolder)
    key = "sum/list/int"
    sut.register(key, *_FCTS[_ValueHolder][key])

    result = sut.make(key=key, inputs={"values": [1, 2, 3, 4, 5]})

    self.assertIsInstance(result, _ValueHolder)
    self.assertEqual(result.value, 15)

  def test_make_with_tuple_type_spec(self):
    bkr = self._create_broker(_ValueHolder)
    sut = bkr.get(_ValueHolder)
    key = "sum/tuple"
    sut.register(key, *_FCTS[_ValueHolder][key])

    result = sut.make(key=key, inputs={"values": (1, 2.0, 3, 4.0)})

    self.assertIsInstance(result, _ValueHolder)
    self.assertAlmostEqual(result.value, 10.0)

  def test_make_with_dict_type_spec_dict_form(self):
    # Arrange
    bkr = self._create_broker(_ValueHolder)
    sut = bkr.get(_ValueHolder)
    sut.register("create/float", *_FCTS[_ValueHolder]["create/float"])
    sut.register("create/int", *_FCTS[_ValueHolder]["create/int"])
    key = "sum/key-values/vh"
    sut.register(key, *_FCTS[_ValueHolder][key])

    # Act
    inputs = {
      "vhd": [{
        "key": {
          "key": "create/float",
          "inputs": {"value": 1.0},
        },
        "value": {
          "key": "create/int",
          "inputs": {"value": 2},
        },
      }, {
        "key": {
          "key": "create/int",
          "inputs": {"value": 3},
        },
        "value": {
          "key": "create/float",
          "inputs": {"value": 4.0},
        },
      }],
    }
    result = sut.make(key=key, inputs=inputs)

    # Assert
    self.assertIsInstance(result, _ValueHolder)
    self.assertAlmostEqual(result.value, 10.0)

  def test_make_with_dict_type_spec_pair_form(self):
    # Arrange
    bkr = self._create_broker(_ValueHolder)
    sut = bkr.get(_ValueHolder)
    sut.register("create/float", *_FCTS[_ValueHolder]["create/float"])
    sut.register("create/int", *_FCTS[_ValueHolder]["create/int"])
    key = "sum/key-values/vh"
    sut.register(key, *_FCTS[_ValueHolder][key])
    inputs = {
        "vhd": [(
            {"key": "create/float", "inputs": {"value": 1.0}},
            {"key": "create/int", "inputs": {"value": 2}},
        ), (
            {"key": "create/int", "inputs": {"value": 3}},
            {"key": "create/float", "inputs": {"value": 4.0}},
        )],
    }

    # Act
    result = sut.make(key=key, inputs=inputs)

    # Assert
    self.assertIsInstance(result, _ValueHolder)
    self.assertAlmostEqual(result.value, 10.0)

  def test_make_composite(self):
    # Arrange
    bkr = self._create_broker(_ValueHolder, _Adder)
    vh_mfr = bkr.get(_ValueHolder)
    vh_mfr.register("create/float", *_FCTS[_ValueHolder]["create/float"])
    vh_mfr.register("create/int", *_FCTS[_ValueHolder]["create/int"])
    vh_mfr.register("sum/list/vh", *_FCTS[_ValueHolder]["sum/list/vh"])
    vh_mfr.register("sum/key-values/vh",
                    *_FCTS[_ValueHolder]["sum/key-values/vh"])
    vh_mfr.register("sum/tuple", *_FCTS[_ValueHolder]["sum/tuple"])
    sut = bkr.get(_Adder)
    sut.register("create/vhs", *_FCTS[_Adder]["create/vhs"])

    vh1_spec = {
        "key": "sum/list/vh",
        "inputs": {
            "vhs": [
                {
                    "key": "create/int",
                    "inputs": {"value": 1},
                },
                {
                    "key": "sum/tuple",
                    "inputs": {"values": [2, 3.0, 4, 5.0]},
                },
            ],
        },
    }
    vh2_spec = {
        "key": "sum/key-values/vh",
        "inputs": {
            "vhd": [{
                "key": {
                    "key": "create/float",
                    "inputs": {"value": 6.0},
                },
                "value": {
                    "key": "create/int",
                    "inputs": {"value": 7},
                },
            }, {
                "key": {
                    "key": "create/int",
                    "inputs": {"value": 8},
                },
                "value": {
                    "key": "create/float",
                    "inputs": {"value": 9.0},
                },
            }],
        },
    }
    inputs = {"vh1": vh1_spec, "vh2": vh2_spec}

    # Act
    result = sut.make(key="create/vhs", inputs=inputs)

    # Assert
    self.assertIsInstance(result, _Adder)
    self.assertAlmostEqual(result.value, 45.0)

  def test_make_via_default_factory(self):
    bkr = self._create_broker(_ValueHolder)
    sut = bkr.get(_ValueHolder)
    sut.register("create/float", *_FCTS[_ValueHolder]["create/float"])
    sut.default = "create/float"

    result = sut.make(inputs={"value": 1.0})

    self.assertEqual(sut.default, "create/float")
    self.assertIsInstance(result, _ValueHolder)
    self.assertAlmostEqual(result.value, 1.0)

  def test_make_with_default_parameters(self):
    bkr = self._create_broker(_ValueHolder)
    sut = bkr.get(_ValueHolder)
    key = "create/float"
    sut.register(key, *_FCTS[_ValueHolder][key], defaults={"value": 1.0})

    result = sut.make(key=key)

    self.assertIsInstance(result, _ValueHolder)
    self.assertAlmostEqual(result.value, 1.0)

  def test_make_overriding_default_parameters(self):
    bkr = self._create_broker(_ValueHolder)
    sut = bkr.get(_ValueHolder)
    key = "create/float"
    sut.register(key, *_FCTS[_ValueHolder][key], defaults={"value": 1.0})

    result = sut.make(key=key, inputs={"value": 2.0})

    self.assertIsInstance(result, _ValueHolder)
    self.assertAlmostEqual(result.value, 2.0)

  def test_make_with_invalid_input_type(self):
    bkr = self._create_broker(_ValueHolder)
    sut = bkr.get(_ValueHolder)
    key = "create/int"
    sut.register(key, *_FCTS[_ValueHolder][key])

    with self.assertRaisesRegex(
        errors.InputError,
        "Manifest is expected to be either an instance of "
        "or an ObjectSpec for class `int`. Given: 1.0"):
      sut.make(key=key, inputs={"value": 1.0})

  def test_make_with_factory_returning_incompatible_type(self):
    bkr = self._create_broker(_TrivialClass)
    sut = bkr.get(_TrivialClass)
    key = "create/int"

    sut.register(key, *_FCTS[_ValueHolder][key])

    with self.assertRaises(TypeError):
      sut.make(key=key, inputs={"value": 1})

  def test_merge_simple(self):
    sut = mfr_lib.Manufacturer(_ValueHolder)
    sut.register("create/int", *_FCTS[_ValueHolder]["create/int"])
    mfr = mfr_lib.Manufacturer(_ValueHolder)
    mfr.register("create/float", *_FCTS[_ValueHolder]["create/float"])
    mfr2 = mfr_lib.Manufacturer(_ValueHolder)
    mfr2.register("sum/list/int", *_FCTS[_ValueHolder]["sum/list/int"])

    sut.merge(mfr)
    sut.merge(lambda: mfr2)

    self.assertIn("create/float", sut)
    self.assertIn("create/int", sut)
    self.assertIn("sum/list/int", sut)

  def test_merge_incompatible(self):
    sut = mfr_lib.Manufacturer(_ValueHolder)
    mfr = mfr_lib.Manufacturer(_Adder)

    with self.assertRaises(TypeError):
      sut.merge(mfr)

  def test_merge_simple_with_conflict_not_ignored(self):
    key = "create/int"
    sut = mfr_lib.Manufacturer(_ValueHolder)
    sut.register(key, *_FCTS[_ValueHolder][key])
    mfr = mfr_lib.Manufacturer(_ValueHolder)
    mfr.register(key, *_FCTS[_ValueHolder][key])

    with self.assertRaisesRegex(errors.KeyConflictError, key):
      sut.merge(mfr, ignore_collision=False)

  def test_merge_with_non_empty_root(self):
    key = "create/int"
    sut = mfr_lib.Manufacturer(_ValueHolder)
    sut.register(key, *_FCTS[_ValueHolder][key])
    mfr = mfr_lib.Manufacturer(_ValueHolder)
    mfr.register(key, *_FCTS[_ValueHolder][key])

    sut.merge(mfr, root="other")
    sut.merge(mfr, root="more", sep=".")

    self.assertIn("other/create/int", sut)
    self.assertIn("more.create/int", sut)

  def test_merge_all(self):
    k1 = "create/int"
    k2 = "create/float"
    sut = mfr_lib.Manufacturer(_ValueHolder)
    m1 = mfr_lib.Manufacturer(_ValueHolder)
    m1.register(k1, *_FCTS[_ValueHolder][k1])
    m2 = mfr_lib.Manufacturer(_ValueHolder)
    m2.register(k2, *_FCTS[_ValueHolder][k2])

    sut.merge_all({None: [m1, lambda: m2],
                   "f1": [m1],
                   "f2": lambda: [m2],
                   "f3": lambda: [lambda: m1, m2]})

    self.assertIn(k1, sut)
    self.assertIn(k2, sut)
    self.assertIn("f1/%s" % k1, sut)
    self.assertIn("f2/%s" % k2, sut)
    self.assertIn("f3/%s" % k1, sut)
    self.assertIn("f3/%s" % k2, sut)


if __name__ == "__main__":
  absltest.main()
