#!/usr/bin/env python3
"""Tests for passive-aware LVS trial netlist preparation."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from prepare_passive_aware_lvs_netlists import (
    extracted_to_passive_aware_connectivity,
    prepare,
    source_to_passive_aware_connectivity,
)


class PreparePassiveAwareLvsNetlistsTest(unittest.TestCase):
    def test_source_to_passive_aware_keeps_passives_as_primitives(self) -> None:
        lines = [
            ".subckt amp vdda gnda outn vout\n",
            "xm0 outn vin gnda gnda nch_mac l=1u w=2u\n",
            "xr0 net027 vout gnda rppolywo_m lr=4e-6\n",
            "xc0 outn net027 cfmom_2t nr=94\n",
            ".ends amp\n",
        ]

        output, stats = source_to_passive_aware_connectivity(lines)

        text = "".join(output)
        self.assertIn("xm0 outn vin gnda gnda sky130_fd_pr__nfet_01v8 w=2 l=1", text)
        self.assertIn("R_xr0 net027 vout 1", text)
        self.assertIn("C_xc0 outn net027 1f", text)
        self.assertEqual(stats["abstracted_source_passives"], {"rppolywo_m": 1, "cfmom_2t": 1})
        self.assertEqual(stats["ignored_reference_terminals"], {"xr0": ["gnda"]})
        records = {item["source_instance"]: item for item in stats["lvs_primitive_abstractions"]}
        self.assertEqual(records["xr0"]["lvs_primitive_device_class"], "r")
        self.assertEqual(records["xr0"]["ignored_reference_terminals"], ["gnda"])
        self.assertEqual(records["xc0"]["lvs_primitive_device_class"], "c")
        self.assertEqual(records["xc0"]["lvs_primitive_spice"], "C_xc0 outn net027 1f")

    def test_extracted_to_passive_aware_removes_fragments_and_inserts_candidates(self) -> None:
        packet = {
            "candidates": [
                {
                    "source_instance": "xr0",
                    "source_model": "rppolywo_m",
                    "source_terminals": ["net027", "vout", "gnda"],
                },
                {
                    "source_instance": "xc0",
                    "source_model": "cfmom_2t",
                    "source_terminals": ["outn", "net027"],
                },
            ]
        }
        extracted = [
            ".subckt amp_flat vdda vin vip ibias vout\n",
            "+ net027 outn\n",
            "X0 vout ibias vdda vdda sky130_fd_pr__pfet_01v8 ad=1 as=2 w=0.22 l=10\n",
            "X3 net027 n1 vdda sky130_fd_pr__res_xhigh_po w=0.4 l=4\n",
            "R1 outn net027 sky130_fd_pr__res_generic_m1 w=0.1 l=0.2\n",
            "C1 outn net027 1f\n",
            ".ends\n",
        ]

        output, stats = extracted_to_passive_aware_connectivity(
            extracted,
            packet=packet,
            renames={},
            source_ports=["vdda", "gnda", "vin", "vip", "ibias", "vout"],
        )

        text = "".join(output)
        self.assertIn(".subckt amp_flat vdda gnda vin vip ibias vout", text)
        self.assertNotIn("net027 outn", text.splitlines()[0])
        self.assertIn("X0 vout ibias vdda vdda sky130_fd_pr__pfet_01v8 w=0.22 l=10", text)
        self.assertNotIn("res_xhigh_po", text)
        self.assertNotIn("sky130_fd_pr__res_generic_m1", text)
        self.assertNotIn("C1 outn net027", text)
        self.assertIn("R_xr0 net027 vout 1", text)
        self.assertIn("C_xc0 outn net027 1f", text)
        self.assertEqual(stats["skipped_physical_passives"], 2)
        self.assertEqual(stats["skipped_parasitic_capacitors"], 1)
        self.assertEqual(stats["skipped_subckt_port_continuations"], 1)
        self.assertEqual(stats["inserted_candidate_count"], 2)
        records = {item["source_instance"]: item for item in stats["lvs_primitive_abstractions"]}
        self.assertEqual(records["xr0"]["abstraction_source"], "passive_abstraction_packet")
        self.assertEqual(records["xr0"]["lvs_primitive_device_class"], "r")
        self.assertEqual(records["xc0"]["lvs_primitive_device_class"], "c")

    def test_prepare_can_restore_extracted_mos_connectivity_from_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.spice"
            extracted = root / "corrupt_extracted.spice"
            mos_reference = root / "mos_reference.spice"
            packet = root / "packet.json"
            out_dir = root / "out"
            source.write_text(
                ".subckt amp vdda gnda outn vout\n"
                "xm0 outn vin gnda gnda nch_mac l=1u w=2u\n"
                "xr0 net027 vout gnda rppolywo_m lr=4e-6\n"
                "xc0 outn net027 cfmom_2t nr=94\n"
                ".ends amp\n",
                encoding="utf-8",
            )
            extracted.write_text(
                ".subckt amp_flat vdda gnda outn vout\n"
                "X0 outn vin vdda vdda sky130_fd_pr__nfet_01v8 w=2 l=1\n"
                ".ends\n",
                encoding="utf-8",
            )
            mos_reference.write_text(
                ".subckt amp_flat vdda gnda outn vout\n"
                "X0 outn vin gnda gnda sky130_fd_pr__nfet_01v8 w=2 l=1\n"
                ".ends\n",
                encoding="utf-8",
            )
            packet.write_text(
                '{"schema_version": "passive_abstraction_packet.v1", "candidates": ['
                '{"source_instance": "xr0", "source_model": "rppolywo_m", "source_terminals": ["net027", "vout", "gnda"]},'
                '{"source_instance": "xc0", "source_model": "cfmom_2t", "source_terminals": ["outn", "net027"]}'
                "]}\n",
                encoding="utf-8",
            )

            summary = prepare(
                source_path=source,
                extracted_path=extracted,
                packet_path=packet,
                out_dir=out_dir,
                prefix="restored",
                renames={},
                mos_reference_path=mos_reference,
            )

            extracted_text = Path(summary["extracted_output"]).read_text(encoding="utf-8")
            self.assertEqual(summary["mos_connectivity_source"], "mos_reference")
            self.assertEqual(summary["mos_reference"], str(mos_reference))
            self.assertIn("X0 outn vin gnda gnda sky130_fd_pr__nfet_01v8 w=2 l=1", extracted_text)
            self.assertNotIn("X0 outn vin vdda vdda", extracted_text)
            self.assertIn("R_xr0 net027 vout 1", extracted_text)
            self.assertIn("C_xc0 outn net027 1f", extracted_text)
            source_records = {
                item["source_instance"]: item
                for item in summary["source_stats"]["lvs_primitive_abstractions"]
            }
            extracted_records = {
                item["source_instance"]: item
                for item in summary["extracted_stats"]["lvs_primitive_abstractions"]
            }
            self.assertEqual(source_records["xr0"]["lvs_primitive_kind"], "resistor")
            self.assertEqual(source_records["xc0"]["lvs_primitive_kind"], "capacitor")
            self.assertEqual(extracted_records["xr0"]["lvs_primitive_device_class"], "r")
            self.assertEqual(extracted_records["xc0"]["lvs_primitive_device_class"], "c")


if __name__ == "__main__":
    unittest.main()
