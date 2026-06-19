#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
from importlib import import_module
from pathlib import Path

try:
    probe = import_module("probe_sky130_native_passive_capability")
except ModuleNotFoundError:
    probe = import_module("tools.sky130_adapter.probe_sky130_native_passive_capability")

build_summary = probe.build_summary
parse_magic_supported_models = probe.parse_magic_supported_models
parse_netgen_supported_models = probe.parse_netgen_supported_models


class ProbeSky130NativePassiveCapabilityTest(unittest.TestCase):
    def test_parses_magic_and_netgen_supported_models(self) -> None:
        magic = "\n".join(
            [
                " device rsubcircuit sky130_fd_pr__res_xhigh_po uhrpoly l=l w=w",
                " device csubcircuit sky130_fd_pr__cap_mim_m3_1 *mimcap *m3 w=w l=l",
                " device resistor sky130_fd_pr__res_generic_m1 rmetal1 *metal1",
            ]
        )
        netgen = "\n".join(
            [
                "lappend devices sky130_fd_pr__res_xhigh_po",
                "lappend devices sky130_fd_pr__cap_mim_m3_1",
                "lappend devices sky130_fd_pr__nfet_01v8",
            ]
        )

        self.assertEqual(
            parse_magic_supported_models(magic),
            {
                "sky130_fd_pr__res_xhigh_po",
                "sky130_fd_pr__cap_mim_m3_1",
                "sky130_fd_pr__res_generic_m1",
            },
        )
        self.assertEqual(
            parse_netgen_supported_models(netgen),
            {
                "sky130_fd_pr__res_xhigh_po",
                "sky130_fd_pr__cap_mim_m3_1",
                "sky130_fd_pr__nfet_01v8",
            },
        )

    def test_reports_magical_passives_require_native_retarget(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "amp.sp"
            source.write_text(
                ".subckt amp outn vout gnda\n"
                "xr0 net027 vout gnda rppolywo_m lr=4e-6\n"
                "xc0 outn net027 cfmom_2t nr=94\n"
                ".ends amp\n",
                encoding="utf-8",
            )
            sky130a = root / "sky130A"
            magic = sky130a / "libs.tech" / "magic" / "sky130A.tech"
            netgen = sky130a / "libs.tech" / "netgen" / "sky130A_setup.tcl"
            magic.parent.mkdir(parents=True)
            netgen.parent.mkdir(parents=True)
            magic.write_text(
                " device rsubcircuit sky130_fd_pr__res_xhigh_po uhrpoly l=l w=w\n"
                " device csubcircuit sky130_fd_pr__cap_mim_m3_1 *mimcap *m3 w=w l=l\n",
                encoding="utf-8",
            )
            netgen.write_text(
                "lappend devices sky130_fd_pr__res_xhigh_po\n"
                "lappend devices sky130_fd_pr__cap_mim_m3_1\n",
                encoding="utf-8",
            )

            summary = build_summary(
                source_netlist=source,
                sky130a=str(sky130a),
                repo_root=root,
            )

        self.assertEqual(summary["source_model_native_status"], "fail")
        self.assertFalse(summary["direct_source_model_support"])
        self.assertEqual(summary["unsupported_source_models"], ["cfmom_2t", "rppolywo_m"])
        self.assertTrue(summary["native_retarget_available"])
        self.assertEqual(summary["native_retarget_map"]["rppolywo_m"], ["sky130_fd_pr__res_xhigh_po"])
        self.assertEqual(summary["native_retarget_map"]["cfmom_2t"], ["sky130_fd_pr__cap_mim_m3_1"])
        self.assertTrue(summary["native_retarget_requires_geometry_replacement"])
        self.assertFalse(summary["can_fix_current_gds_by_layer_remap_only"])
        self.assertFalse(
            summary["device_generation_source_status"]["can_patch_current_generator_source"]
        )

    def test_reports_no_retarget_when_pdk_lacks_native_capacitor(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "amp.sp"
            source.write_text("xc0 outn net027 cfmom_2t nr=94\n", encoding="utf-8")
            sky130a = root / "sky130A"
            magic = sky130a / "libs.tech" / "magic" / "sky130A.tech"
            netgen = sky130a / "libs.tech" / "netgen" / "sky130A_setup.tcl"
            magic.parent.mkdir(parents=True)
            netgen.parent.mkdir(parents=True)
            magic.write_text(" device resistor sky130_fd_pr__res_xhigh_po uhrpoly\n", encoding="utf-8")
            netgen.write_text("lappend devices sky130_fd_pr__res_xhigh_po\n", encoding="utf-8")

            summary = build_summary(source_netlist=source, sky130a=str(sky130a))

        self.assertEqual(summary["source_model_native_status"], "fail")
        self.assertFalse(summary["native_retarget_available"])
        self.assertEqual(summary["native_retarget_map"]["cfmom_2t"], [])


if __name__ == "__main__":
    unittest.main()
