#!/usr/bin/env python3
"""Tests for generic Sky130 case pipeline helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sky130_case_pipeline_helpers import check_power_nets, subckt_ports


class Sky130CasePipelineHelpersTest(unittest.TestCase):
    def test_check_power_nets_accepts_explicit_vdd_vss_arrays(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Path(tmpdir) / "case.json"
            config.write_text(
                '{"vddNetNames": ["VDD"], "vssNetNames": ["GND"]}\n',
                encoding="utf-8",
            )

            result = check_power_nets(config, "VDD", "GND")

        self.assertEqual(result.vdd_present, True)
        self.assertEqual(result.vss_present, True)
        self.assertEqual(result.missing, [])

    def test_check_power_nets_reports_missing_net(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Path(tmpdir) / "case.json"
            config.write_text(
                '{"vddNetNames": ["VDD"], "vssNetNames": []}\n',
                encoding="utf-8",
            )

            result = check_power_nets(config, "VDD", "GND")

        self.assertEqual(result.vdd_present, True)
        self.assertEqual(result.vss_present, False)
        self.assertEqual(result.missing, ["GND"])

    def test_subckt_ports_extracts_raw_magic_ports(self) -> None:
        ports = subckt_ports(".subckt ota_core_flat VINP VINM IB VDD VOUT GND")

        self.assertEqual(ports, "VINP VINM IB VDD VOUT GND")


if __name__ == "__main__":
    unittest.main()
