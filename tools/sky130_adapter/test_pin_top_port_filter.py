#!/usr/bin/env python3
"""Tests for Sky130 ioPin top-port filtering helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pin_top_port_filter import filter_named_pins, parse_top_ports


class PinTopPortFilterTest(unittest.TestCase):
    def test_parse_top_ports_accepts_dot_subckt(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            netlist = Path(tmpdir) / "test.sp"
            netlist.write_text(
                ".subckt ota_core VINP VINM IB VDD VOUT GND\n"
                "M1 (net2 IB GND GND) sky130_fd_pr__nfet_01v8\n"
                ".ends ota_core\n",
                encoding="utf-8",
            )

            ports = parse_top_ports(netlist, "ota_core")

        self.assertEqual(ports, ["VINP", "VINM", "IB", "VDD", "VOUT", "GND"])

    def test_parse_top_ports_accepts_magical_subckt_without_dot(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            netlist = Path(tmpdir) / "test.sp"
            netlist.write_text(
                "subckt inverter_core A Y VPWR VGND\n"
                "M0 (Y A VGND VGND) sky130_fd_pr__nfet_01v8\n"
                "ends inverter_core\n",
                encoding="utf-8",
            )

            ports = parse_top_ports(netlist, "inverter_core")

        self.assertEqual(ports, ["A", "Y", "VPWR", "VGND"])

    def test_filter_named_pins_skips_internal_nets(self) -> None:
        pins = ["VINP", "VINM", "IB", "VDD", "VOUT", "GND", "net1", "net2"]

        result = filter_named_pins(pins, ["VINP", "VINM", "IB", "VDD", "VOUT", "GND"])

        self.assertEqual(result.processed, ["VINP", "VINM", "IB", "VDD", "VOUT", "GND"])
        self.assertEqual(result.skipped, ["net1", "net2"])
        self.assertEqual(result.skipped_reasons, {"net1": "not in top subckt port list", "net2": "not in top subckt port list"})


if __name__ == "__main__":
    unittest.main()
