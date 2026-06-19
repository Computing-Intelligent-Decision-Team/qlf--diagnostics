#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
from importlib import import_module
from pathlib import Path


try:
    probe = import_module("probe_sky130_native_cap_gencell")
except ModuleNotFoundError:
    probe = import_module("tools.sky130_adapter.probe_sky130_native_cap_gencell")


class ProbeSky130NativeCapGencellTest(unittest.TestCase):
    def test_parse_extracted_native_cap_device(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            spice = Path(tmpdir) / "cap.spice"
            spice.write_text(
                ".subckt cap C2 C1\n"
                "X0 C1 C2 sky130_fd_pr__cap_mim_m3_1 l=10 w=10\n"
                "C0 C1 C2 9.4f\n"
                ".ends\n",
                encoding="utf-8",
            )

            devices = probe.parse_extracted_native_caps(spice)

        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0]["instance"], "X0")
        self.assertEqual(devices[0]["terminals"], ["C1", "C2"])
        self.assertEqual(devices[0]["model"], "sky130_fd_pr__cap_mim_m3_1")
        self.assertEqual(devices[0]["params"], "l=10 w=10")

    def test_write_magic_tcl_uses_direct_draw_proc(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tcl = Path(tmpdir) / "probe.tcl"
            probe._write_magic_tcl(
                tcl,
                model="sky130_fd_pr__cap_mim_m3_1",
                cell_name="cap_probe",
                width_um=10.0,
                length_um=12.0,
            )

            text = tcl.read_text(encoding="ascii")

        self.assertIn("sky130::sky130_fd_pr__cap_mim_m3_1_draw $params", text)
        self.assertIn("dict set params w 10", text)
        self.assertIn("dict set params l 12", text)
        self.assertIn("gds write ${gname}.gds", text)
        self.assertIn("ext2spice ${gname}.ext", text)

    def test_write_magic_tcl_rejects_non_cap_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(ValueError):
                probe._write_magic_tcl(
                    Path(tmpdir) / "probe.tcl",
                    model="sky130_fd_pr__res_xhigh_po",
                    cell_name="bad_probe",
                    width_um=10.0,
                    length_um=10.0,
                )


if __name__ == "__main__":
    unittest.main()
