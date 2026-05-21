#!/usr/bin/env python3
"""Tests for Sky130 case regression registry and summary collection."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from collect_sky130_case_summaries import (
    load_registry,
    parse_case_summary,
    render_regression_summary,
)


class CollectSky130CaseSummariesTest(unittest.TestCase):
    def test_load_registry_reads_case_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = Path(tmpdir) / "registry.yaml"
            registry.write_text(
                "cases:\n"
                "  inverter_core:\n"
                "    case_dir: examples/inverter_sky130_try\n"
                "    top_cell: inverter_core\n"
                "    vdd: VPWR\n"
                "    vss: VGND\n"
                "    convert_xschem: no\n"
                "    magical_netlist: inverter_sky130_name_test.sp\n"
                "    config: inverter_trial.json\n"
                "    out_dir: generated/sky130_cases/inverter_core\n",
                encoding="utf-8",
            )

            cases = load_registry(registry)

        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0]["name"], "inverter_core")
        self.assertEqual(cases[0]["vdd"], "VPWR")
        self.assertEqual(cases[0]["out_dir"], "generated/sky130_cases/inverter_core")

    def test_parse_case_summary_extracts_standard_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = Path(tmpdir) / "summary.md"
            summary.write_text(
                "| Field | Value |\n"
                "| --- | --- |\n"
                "| CASE_NAME | ota_core |\n"
                "| TOP_CELL | ota_core |\n"
                "| DRC_COUNT | 0 |\n"
                "| CONNECTIVITY_LVS_MATCH | yes |\n"
                "| PEX_CAPS | 25 |\n",
                encoding="utf-8",
            )

            fields = parse_case_summary(summary)

        self.assertEqual(fields["CASE_NAME"], "ota_core")
        self.assertEqual(fields["DRC_COUNT"], "0")
        self.assertEqual(fields["CONNECTIVITY_LVS_MATCH"], "yes")

    def test_render_regression_summary_marks_pass(self) -> None:
        rows = [
            {
                "CASE_NAME": "inverter_core",
                "TOP_CELL": "inverter_core",
                "VDD_NET": "VPWR",
                "VSS_NET": "VGND",
                "DRC_COUNT": "0",
                "RAW_SUBCKT_PORTS": "A Y VPWR VGND",
                "ANONYMOUS_NODES": "none",
                "CONNECTIVITY_LVS_MATCH": "yes",
                "NET_RENAMES_USED": "no",
                "PEX_CAPS": "6",
                "PEX_TOTAL_CAP_FF": "4.20175 fF",
            }
        ]

        markdown = render_regression_summary(rows)

        self.assertIn("| inverter_core | PASS | inverter_core | VPWR | VGND | 0 | yes | none | no | 6 | 4.20175 fF |", markdown)


if __name__ == "__main__":
    unittest.main()
