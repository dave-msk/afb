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
from afb.utils import test_helpers as helpers


class BrokerTest(absltest.TestCase):
  def test_get_not_registered(self):
    sut = bkr_lib.Broker()
    result = sut.get(helpers.TrivialClass)
    self.assertIsNone(result)

  def test_register_simple(self):
    sut = bkr_lib.Broker()

    sut.register(mfr_lib.Manufacturer(helpers.TrivialClass))

    result = sut.get(helpers.TrivialClass)
    self.assertIsInstance(result, mfr_lib.Manufacturer)
    self.assertIs(result.cls, helpers.TrivialClass)

  def test_register_conflict(self):
    sut = helpers.create_broker(helpers.TrivialClass)
    mfr = mfr_lib.Manufacturer(helpers.TrivialClass)

    with self.assertRaises(errors.KeyConflictError):
      sut.register(mfr)

  def test_register_override(self):
    sut = helpers.create_broker(helpers.TrivialClass)
    mfr = mfr_lib.Manufacturer(helpers.TrivialClass)

    sut.register(mfr, override=True)

    result = sut.get(helpers.TrivialClass)
    self.assertIsInstance(result, mfr_lib.Manufacturer)
    self.assertIs(result, mfr)

  def test_register_all(self):
    sut = bkr_lib.Broker()
    m1 = mfr_lib.Manufacturer(helpers.ValueHolder)
    m2 = mfr_lib.Manufacturer(helpers.Adder)
    m3 = mfr_lib.Manufacturer(helpers.TrivialClass)

    sut.register_all([m1, lambda: m2, m3])

    self.assertIs(sut.get(helpers.ValueHolder), m1)
    self.assertIs(sut.get(helpers.Adder), m2)

  def test_get_or_create(self):
    sut = bkr_lib.Broker()

    self.assertIsNone(sut.get(helpers.TrivialClass))
    result = sut.get_or_create(helpers.TrivialClass)

    self.assertIsInstance(result, mfr_lib.Manufacturer)
    self.assertIs(result.cls, helpers.TrivialClass)
    self.assertIs(sut.get(helpers.TrivialClass), result)

  def test_make(self):
    # Arrange
    sut = helpers.create_broker(helpers.ValueHolder, helpers.Adder)
    mfr_vh = sut.get(helpers.ValueHolder)
    mfr_vh.register_dict(helpers.FCTS[helpers.ValueHolder])
    mfr_adr = sut.get(helpers.Adder)
    mfr_adr.register_dict(helpers.FCTS[helpers.Adder])

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
    result = sut.make(helpers.Adder, key="create/vhs", inputs=inputs)

    # Assert
    self.assertIsInstance(result, helpers.Adder)
    self.assertAlmostEqual(result.value, 45.0)

  def test_add_factory(self):
    sut = bkr_lib.Broker()
    key = "create/int"

    sut.add_factory(helpers.ValueHolder,
                    key,
                    **helpers.factory_spec(helpers.ValueHolder, key))

    self.assertIsInstance(sut.get(helpers.ValueHolder), mfr_lib.Manufacturer)
    result = sut.make(helpers.ValueHolder, key=key, inputs={"value": 1})
    self.assertIsInstance(result, helpers.ValueHolder)
    self.assertEqual(result.value, 1)

  def test_merge_mfr(self):
    sut = bkr_lib.Broker()
    m1 = mfr_lib.Manufacturer(helpers.ValueHolder)
    m1.register("create/int",
                **helpers.factory_spec(helpers.ValueHolder, "create/int"))

    sut.merge_mfr(m1)

    self.assertIn("create/int", sut.get(helpers.ValueHolder))

  def test_merge_mfrs(self):
    sut = helpers.create_broker(helpers.ValueHolder)
    m0 = sut.get(helpers.ValueHolder)
    m0.register("create/int",
                **helpers.factory_spec(helpers.ValueHolder, "create/int"))
    m1 = mfr_lib.Manufacturer(helpers.ValueHolder)
    m1.register("create/float",
                **helpers.factory_spec(helpers.ValueHolder, "create/float"))
    m2 = mfr_lib.Manufacturer(helpers.Adder)
    m2.register("create/floats",
                **helpers.factory_spec(helpers.Adder, "create/floats"))

    sut.merge_mfrs({"k1": lambda: [m1], "k2": [lambda: m2]}, sep=".")

    self.assertIn("create/int", sut.get(helpers.ValueHolder))
    self.assertIn("k1.create/float", sut.get(helpers.ValueHolder))
    self.assertIn("k2.create/floats", sut.get(helpers.Adder))

  def test_merge(self):
    sut = bkr_lib.Broker()
    sut.add_factory(helpers.ValueHolder,
                    "create/int",
                    **helpers.factory_spec(helpers.ValueHolder, "create/int"))
    bkr = bkr_lib.Broker()
    bkr.add_factory(helpers.ValueHolder,
                    "create/float",
                    **helpers.factory_spec(helpers.ValueHolder, "create/int"))
    bkr.add_factory(helpers.Adder,
                    "create/floats",
                    **helpers.factory_spec(helpers.Adder, "create/floats"))

    sut.merge(bkr, root="extra")

    self.assertIsInstance(sut.get(helpers.ValueHolder), mfr_lib.Manufacturer)
    self.assertIn("create/int", sut.get(helpers.ValueHolder))
    self.assertIn("extra/create/float", sut.get(helpers.ValueHolder))
    self.assertIsInstance(sut.get(helpers.Adder), mfr_lib.Manufacturer)
    self.assertIn("extra/create/floats", sut.get(helpers.Adder))

  def test_classes(self):
    sut = helpers.create_broker(helpers.TrivialClass,
                                helpers.ValueHolder,
                                helpers.Adder)

    classes = sut.classes

    self.assertListEqual(
        classes,
        [helpers.Adder, helpers.TrivialClass, helpers.ValueHolder])


if __name__ == "__main__":
  absltest.main()
