#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from importlib import import_module
from pathlib import Path


try:
    native = import_module("prepare_native_passive_retarget_lvs")
except ModuleNotFoundError:
    native = import_module("tools.sky130_adapter.prepare_native_passive_retarget_lvs")


class PrepareNativePassiveRetargetLvsTest(unittest.TestCase):
    def test_build_trial_generates_native_resistor_chain_and_fails_missing_cap(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            packet = root / "packet.json"
            extracted = root / "extracted.spice"
            packet.write_text(
                json.dumps(
                    {
                        "source_instance_coverage": {
                            "source_instances": ["xr0", "xc0"],
                        },
                        "candidates": [
                            {
                                "candidate_type": "segmented_resistor_chain_source_equivalent",
                                "source_instance": "xr0",
                                "source_model": "rppolywo_m",
                                "source_terminals": ["net027", "vout", "gnda"],
                                "chain": {
                                    "device_models": ["sky130_fd_pr__res_xhigh_po"],
                                    "devices": [
                                        {
                                            "instance": "X0",
                                            "model": "sky130_fd_pr__res_xhigh_po",
                                            "terminals": ["net027", "n1", "gnda"],
                                        },
                                        {
                                            "instance": "X1",
                                            "model": "sky130_fd_pr__res_xhigh_po",
                                            "terminals": ["n1", "vout", "gnda"],
                                        },
                                    ],
                                },
                            },
                            {
                                "candidate_type": "plate_coupling_capacitor_source_equivalent",
                                "source_instance": "xc0",
                                "source_model": "cfmom_2t",
                                "electrical_terminals": ["outn", "net027"],
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            extracted.write_text(
                ".subckt amp net027 vout gnda outn\n"
                "X0 net027 n1 gnda sky130_fd_pr__res_xhigh_po w=0.4 l=4\n"
                "X1 n1 vout gnda sky130_fd_pr__res_xhigh_po w=0.4 l=4\n"
                ".ends amp\n",
                encoding="utf-8",
            )

            summary = native.build_trial(
                packet_json=packet,
                candidate_extracted=extracted,
                out_dir=root / "trial",
                prefix="amp",
            )

        self.assertEqual(summary["native_resistor_chain_status"], "pass")
        self.assertEqual(summary["native_resistor_chain_device_count"], 2)
        self.assertEqual(summary["native_capacitor_device_recognition_status"], "fail")
        self.assertEqual(summary["missing_native_source_passive_instances"], ["xc0"])
        self.assertFalse(summary["full_native_passive_lvs_ready"])

    def test_build_trial_recognizes_native_cap_device_for_matching_terminals(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            packet = root / "packet.json"
            extracted = root / "extracted.spice"
            packet.write_text(
                json.dumps(
                    {
                        "source_instance_coverage": {"source_instances": ["xc0"]},
                        "candidates": [
                            {
                                "candidate_type": "plate_coupling_capacitor_source_equivalent",
                                "source_instance": "xc0",
                                "source_model": "cfmom_2t",
                                "electrical_terminals": ["outn", "net027"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            extracted.write_text(
                "XCAP outn net027 sky130_fd_pr__cap_mim_m3_1 w=10 l=10\n",
                encoding="utf-8",
            )

            summary = native.build_trial(
                packet_json=packet,
                candidate_extracted=extracted,
                out_dir=root / "trial",
                prefix="amp",
            )
            source_text = Path(summary["source_native_passive_netlist"]).read_text(encoding="utf-8")
            candidate_text = Path(summary["candidate_native_passive_netlist"]).read_text(encoding="utf-8")

        self.assertEqual(summary["native_capacitor_device_recognition_status"], "pass")
        self.assertEqual(summary["missing_native_source_passive_instances"], [])
        self.assertIn("XNC0 outn net027 sky130_fd_pr__cap_mim_m3_1 w=10 l=10", source_text)
        self.assertIn("XNC0 outn net027 sky130_fd_pr__cap_mim_m3_1 w=10 l=10", candidate_text)
        self.assertEqual(summary["native_capacitor_device_count"], 1)


if __name__ == "__main__":
    unittest.main()
