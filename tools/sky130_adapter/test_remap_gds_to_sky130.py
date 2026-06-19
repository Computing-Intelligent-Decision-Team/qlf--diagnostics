#!/usr/bin/env python3
"""Tests for MAGICAL-to-Sky130 GDS remapping."""

from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from remap_gds_to_sky130 import RemapTarget, TargetSpec, remap_gds, write_int2


def record(record_type: int, payload: bytes = b"", data_type: int = 0x02) -> bytes:
    return struct.pack(">HBB", len(payload) + 4, record_type, data_type) + payload


def minimal_boundary(layer: int, datatype: int) -> bytes:
    return (
        record(0x08, b"", 0x00)
        + record(0x0D, write_int2(layer))
        + record(0x0E, write_int2(datatype))
        + record(0x11, b"", 0x00)
    )


class RemapGdsToSky130Test(unittest.TestCase):
    def test_confirmed_layer_mapping_still_remaps_without_datatype_override(self) -> None:
        mapping = {
            31: RemapTarget(
                magical_layer="M1",
                internal_layer=31,
                sky130_layer_name="li1",
                sky130_gds_layer=67,
                sky130_datatype=20,
                status="confirmed",
                risk="test",
                datatype_overrides={},
            )
        }

        _data, actions = remap_gds(minimal_boundary(31, 0), mapping)

        self.assertEqual(actions[0].output_layer, 67)
        self.assertEqual(actions[0].output_datatype, 20)
        self.assertEqual(actions[0].action, "remapped")

    def test_experimental_datatype_override_is_disabled_by_default(self) -> None:
        mapping = {
            150: RemapTarget(
                magical_layer="MRDMY",
                internal_layer=150,
                sky130_layer_name="TBD",
                sky130_gds_layer=None,
                sky130_datatype=None,
                status="tbd",
                risk="test",
                datatype_overrides={
                    2: TargetSpec(
                        sky130_layer_name="met1.res",
                        sky130_gds_layer=68,
                        sky130_datatype=13,
                        status="experimental",
                        risk="test",
                    )
                },
            )
        }

        _data, actions = remap_gds(minimal_boundary(150, 2), mapping)

        self.assertEqual(actions[0].output_layer, 150)
        self.assertEqual(actions[0].output_datatype, 2)
        self.assertEqual(actions[0].action, "preserved_tbd")

    def test_experimental_datatype_override_remaps_when_enabled(self) -> None:
        mapping = {
            150: RemapTarget(
                magical_layer="MRDMY",
                internal_layer=150,
                sky130_layer_name="TBD",
                sky130_gds_layer=None,
                sky130_datatype=None,
                status="tbd",
                risk="test",
                datatype_overrides={
                    2: TargetSpec(
                        sky130_layer_name="met1.res",
                        sky130_gds_layer=68,
                        sky130_datatype=13,
                        status="experimental",
                        risk="test",
                    ),
                    3: TargetSpec(
                        sky130_layer_name="met2.res",
                        sky130_gds_layer=69,
                        sky130_datatype=13,
                        status="experimental",
                        risk="test",
                    ),
                },
            )
        }

        _data_a, actions_a = remap_gds(
            minimal_boundary(150, 2),
            mapping,
            allow_experimental=True,
        )
        _data_b, actions_b = remap_gds(
            minimal_boundary(150, 3),
            mapping,
            allow_experimental=True,
        )

        self.assertEqual(actions_a[0].output_layer, 68)
        self.assertEqual(actions_a[0].output_datatype, 13)
        self.assertEqual(actions_b[0].output_layer, 69)
        self.assertEqual(actions_b[0].output_datatype, 13)
        self.assertIn("MRDMY[2]", actions_a[0].mapping)

    def test_excluded_input_pair_preserves_original_layer_and_datatype(self) -> None:
        mapping = {
            150: RemapTarget(
                magical_layer="MRDMY",
                internal_layer=150,
                sky130_layer_name="TBD",
                sky130_gds_layer=None,
                sky130_datatype=None,
                status="tbd",
                risk="test",
                datatype_overrides={
                    2: TargetSpec(
                        sky130_layer_name="met1.res",
                        sky130_gds_layer=68,
                        sky130_datatype=13,
                        status="experimental",
                        risk="test",
                    ),
                    3: TargetSpec(
                        sky130_layer_name="met2.res",
                        sky130_gds_layer=69,
                        sky130_datatype=13,
                        status="experimental",
                        risk="test",
                    ),
                },
            )
        }

        _data_a, actions_a = remap_gds(
            minimal_boundary(150, 2),
            mapping,
            allow_experimental=True,
            exclude_input_pairs={(150, 2)},
        )
        _data_b, actions_b = remap_gds(
            minimal_boundary(150, 3),
            mapping,
            allow_experimental=True,
            exclude_input_pairs={(150, 2)},
        )

        self.assertEqual(actions_a[0].output_layer, 150)
        self.assertEqual(actions_a[0].output_datatype, 2)
        self.assertEqual(actions_a[0].action, "preserved_excluded")
        self.assertEqual(actions_b[0].output_layer, 69)
        self.assertEqual(actions_b[0].output_datatype, 13)
        self.assertEqual(actions_b[0].action, "remapped")


if __name__ == "__main__":
    unittest.main()
