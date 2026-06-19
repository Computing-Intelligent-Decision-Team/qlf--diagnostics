#!/usr/bin/env python3
"""Tests for MAGICAL trial Sky130 PDK generation."""

from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

import yaml

from generate_magical_sky130_pdk import export_records, make_record, rewrite_lef, rewrite_techfile, write_lf


class GenerateMagicalSky130PdkTest(unittest.TestCase):
    def test_export_records_preserves_datatype_overrides(self) -> None:
        record = make_record(
            "MRDMY",
            150,
            {
                "MRDMY": {
                    "selected_sky130_layer": "TBD",
                    "gds_layer": "TBD",
                    "datatype": "TBD",
                    "risk": "test",
                    "datatype_overrides": {
                        2: {
                            "sky130_layer_name": "MET1RES",
                            "sky130_gds_layer": 68,
                            "sky130_datatype": 13,
                            "status": "experimental",
                            "risk": "test override",
                        }
                    },
                }
            },
        )

        exported = yaml.safe_load(export_records([record]))
        layer = exported["layers"][0]

        self.assertEqual(layer["magical_layer"], "MRDMY")
        self.assertEqual(layer["status"], "tbd")
        self.assertEqual(layer["datatype_overrides"][2]["sky130_layer_name"], "MET1RES")
        self.assertEqual(layer["datatype_overrides"][2]["status"], "experimental")

    def test_rewrite_techfile_keeps_router_layers_only(self) -> None:
        source = (
            "techLayers(\n"
            "  ( NW               3      NW               )\n"
            "  ( CO               30     CO               )\n"
            "  ( VIA1             51     VIA1             )\n"
            ")\n"
        )

        rewritten, records = rewrite_techfile(
            source,
            {},
            {
                "NW": 3,
                "RPO": 29,
                "CO": 30,
                "VIA1": 51,
                "RPDMY": 115,
            },
        )

        self.assertNotIn("( RPO", rewritten)
        self.assertNotIn("( RPDMY", rewritten)
        self.assertEqual([record.magical_layer for record in records], ["NW", "CO", "VIA1"])

    def test_rewrite_lef_keeps_existing_layers_only(self) -> None:
        source = (
            "VERSION 5.8 ;\n"
            "LAYER NW\n"
            "  TYPE MASTERSLICE ;\n"
            "END NW\n"
            "VIA VIA12 DEFAULT\n"
            "END VIA12\n"
            "END LIBRARY\n"
        )

        rewritten, records = rewrite_lef(
            source,
            {},
            {
                "NW": 3,
                "RPO": 29,
                "RPDMY": 115,
            },
        )

        self.assertNotIn("LAYER RPO", rewritten)
        self.assertNotIn("LAYER RPDMY", rewritten)
        self.assertEqual([record.magical_layer for record in records], ["NW"])

    def test_write_lf_normalizes_output_newlines(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sky130.techfile"

            write_lf(path, "a\r\nb\rc\n")

            data = path.read_bytes()
        self.assertEqual(data, b"a\nb\nc\n")
        self.assertNotIn(b"\r\n", data)


if __name__ == "__main__":
    unittest.main()
