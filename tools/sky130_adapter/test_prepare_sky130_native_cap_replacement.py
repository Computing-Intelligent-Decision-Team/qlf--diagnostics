#!/usr/bin/env python3
from __future__ import annotations

import unittest
from importlib import import_module


try:
    repl = import_module("prepare_sky130_native_cap_replacement")
except ModuleNotFoundError:
    repl = import_module("tools.sky130_adapter.prepare_sky130_native_cap_replacement")


class PrepareSky130NativeCapReplacementTest(unittest.TestCase):
    def test_cap_dimensions_from_bbox_uses_pdk_probe_offsets(self) -> None:
        dims = repl.cap_dimensions_from_bbox([-55, -50, 13055, 10650])

        self.assertAlmostEqual(dims["source_bbox_width_um"], 13.11)
        self.assertAlmostEqual(dims["source_bbox_height_um"], 10.7)
        self.assertAlmostEqual(dims["replacement_cap_width_um"], 10.95)
        self.assertAlmostEqual(dims["replacement_cap_length_um"], 10.3)

    def test_find_identity_instance(self) -> None:
        identity = {
            "instances": [
                {"source_instance": "xr0", "magical_instance": "AMP_xr0"},
                {"source_instance": "xc0", "magical_instance": "AMP_xc0"},
            ]
        }

        self.assertEqual(repl.find_identity_instance(identity, "xc0")["magical_instance"], "AMP_xc0")

    def test_source_cell_bbox_requires_cell_bbox(self) -> None:
        with self.assertRaises(ValueError):
            repl.source_cell_bbox({"top_gds": {"cells": [{"name": "cap"}]}})


if __name__ == "__main__":
    unittest.main()
