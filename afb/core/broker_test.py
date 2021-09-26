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


class BrokerTest(absltest.TestCase):
  def _create_broker(self, *classes):
    bkr = bkr_lib.Broker()
    [bkr.register(mfr_lib.Manufacturer(cls)) for cls in classes]
    return bkr

  def test_get_not_registered(self):
    sut = bkr_lib.Broker()
    result = sut.get(_TrivialClass)
    self.assertIsNone(result)

  def test_register_simple(self):
    sut = bkr_lib.Broker()

    sut.register(mfr_lib.Manufacturer(_TrivialClass))

    result = sut.get(_TrivialClass)
    self.assertIsInstance(result, mfr_lib.Manufacturer)
    self.assertIs(result.cls, _TrivialClass)

  def test_register_conflict(self):
    sut = self._create_broker(_TrivialClass)
    mfr = mfr_lib.Manufacturer(_TrivialClass)

    with self.assertRaises(errors.KeyConflictError):
      sut.register(mfr)

  def test_register_override(self):
    sut = self._create_broker(_TrivialClass)
    mfr = mfr_lib.Manufacturer(_TrivialClass)

    sut.register(mfr, override=True)

    result = sut.get(_TrivialClass)
    self.assertIsInstance(result, mfr_lib.Manufacturer)
    self.assertIs(result, mfr)

  def test_register_all(self):
    sut = bkr_lib.Broker()
    m1 = mfr_lib.Manufacturer(_ValueHolder)
    m2 = mfr_lib.Manufacturer(_Adder)
    m3 = mfr_lib.Manufacturer(_TrivialClass)

    sut.register_all([m1, lambda: m2, m3])

    self.assertIs(sut.get(_ValueHolder), m1)
    self.assertIs(sut.get(_Adder), m2)

  def test_get_or_create(self):
    sut = bkr_lib.Broker()

    self.assertIsNone(sut.get(_TrivialClass))
    result = sut.get_or_create(_TrivialClass)

    self.assertIsInstance(result, mfr_lib.Manufacturer)
    self.assertIs(result.cls, _TrivialClass)
    self.assertIs(sut.get(_TrivialClass), result)

  def test_make(self):
    # Arrange
    sut = self._create_broker(_ValueHolder, _Adder)
    mfr_vh = sut.get(_ValueHolder)
    mfr_vh.register_dict(_FCTS[_ValueHolder])
    mfr_adr = sut.get(_Adder)
    mfr_adr.register_dict(_FCTS[_Adder])

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
    result = sut.make(_Adder, key="create/vhs", inputs=inputs)

    # Assert
    self.assertIsInstance(result, _Adder)
    self.assertAlmostEqual(result.value, 45.0)

  def test_add_factory(self):
    sut = bkr_lib.Broker()
    key = "create/int"

    sut.add_factory(_ValueHolder, key, *_FCTS[_ValueHolder][key])

    self.assertIsInstance(sut.get(_ValueHolder), mfr_lib.Manufacturer)
    result = sut.make(_ValueHolder, key=key, inputs={"value": 1})
    self.assertIsInstance(result, _ValueHolder)
    self.assertEqual(result.value, 1)

  def test_merge_mfr(self):
    sut = bkr_lib.Broker()
    m1 = mfr_lib.Manufacturer(_ValueHolder)
    m1.register("create/int", *_FCTS[_ValueHolder]["create/int"])

    sut.merge_mfr(m1)

    self.assertIn("create/int", sut.get(_ValueHolder))

  def test_merge_mfrs(self):
    sut = self._create_broker(_ValueHolder)
    m0 = sut.get(_ValueHolder)
    m0.register("create/int", *_FCTS[_ValueHolder]["create/int"])
    m1 = mfr_lib.Manufacturer(_ValueHolder)
    m1.register("create/float", *_FCTS[_ValueHolder]["create/float"])
    m2 = mfr_lib.Manufacturer(_Adder)
    m2.register("create/floats", *_FCTS[_Adder]["create/floats"])

    sut.merge_mfrs({"k1": lambda: [m1], "k2": [lambda: m2]}, sep=".")

    self.assertIn("create/int", sut.get(_ValueHolder))
    self.assertIn("k1.create/float", sut.get(_ValueHolder))
    self.assertIn("k2.create/floats", sut.get(_Adder))

  def test_merge(self):
    sut = bkr_lib.Broker()
    sut.add_factory(
        _ValueHolder, "create/int", *_FCTS[_ValueHolder]["create/int"])
    bkr = bkr_lib.Broker()
    bkr.add_factory(
        _ValueHolder, "create/float", *_FCTS[_ValueHolder]["create/int"])
    bkr.add_factory(
        _Adder, "create/floats", *_FCTS[_Adder]["create/floats"])

    sut.merge(bkr, root="extra")

    self.assertIsInstance(sut.get(_ValueHolder), mfr_lib.Manufacturer)
    self.assertIn("create/int", sut.get(_ValueHolder))
    self.assertIn("extra/create/float", sut.get(_ValueHolder))
    self.assertIsInstance(sut.get(_Adder), mfr_lib.Manufacturer)
    self.assertIn("extra/create/floats", sut.get(_Adder))

  def test_classes(self):
    sut = self._create_broker(_TrivialClass, _ValueHolder, _Adder)

    classes = sut.classes

    self.assertListEqual(classes, [_Adder, _TrivialClass, _ValueHolder])


if __name__ == "__main__":
  absltest.main()
