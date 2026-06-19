#!/usr/bin/env python3
"""Tests for MAGICAL ioPin layer to Sky130 pin-purpose mapping."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import add_sky130_pin_labels_from_iopin
import add_sky130_pin_shapes_from_iopin
import inspect_gds_pin_shapes


class Sky130PinLayerMapTest(unittest.TestCase):
    def test_iopin_layer_three_maps_to_met2_label_and_pin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            iopin = Path(tmp) / "cell.ioPin"
            iopin.write_text("Y 3 100 200 300 400\n", encoding="utf-8")

            labels = add_sky130_pin_labels_from_iopin.read_iopin(iopin)
            shapes = add_sky130_pin_shapes_from_iopin.read_iopin(iopin)
            inspected = inspect_gds_pin_shapes.read_iopin(iopin)

            self.assertEqual(labels[0].sky130_name, "met2.label")
            self.assertEqual(labels[0].gds_layer, 69)
            self.assertEqual(labels[0].texttype, 5)
            self.assertEqual(shapes[0].pin_name, "met2.pin")
            self.assertEqual(shapes[0].pin_layer, 69)
            self.assertEqual(shapes[0].pin_datatype, 16)
            self.assertEqual(inspected["Y"].sky130_name, "met2")
            self.assertEqual(inspected["Y"].drawing_layer, 69)

    def test_all_magical_routing_iopin_layers_have_mappings(self) -> None:
        for layer in range(1, 7):
            with self.subTest(layer=layer):
                self.assertIn(layer, add_sky130_pin_labels_from_iopin.PIN_LABEL_MAP)
                self.assertIn(layer, add_sky130_pin_shapes_from_iopin.PIN_SHAPE_MAP)
                self.assertIn(layer, inspect_gds_pin_shapes.PIN_PURPOSE_MAP)


if __name__ == "__main__":
    unittest.main()
