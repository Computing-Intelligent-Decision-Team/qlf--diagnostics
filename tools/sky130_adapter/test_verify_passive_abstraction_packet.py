#!/usr/bin/env python3
"""Tests for passive abstraction packet verification."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_passive_abstraction_packet import abstraction_netlists, verify_packet


class VerifyPassiveAbstractionPacketTest(unittest.TestCase):
    def test_verifies_formal_lvs_abstraction_for_supported_resistor_and_capacitor(self) -> None:
        source = [
            ".subckt amp gnda net027 outn vout\n",
            "xr0 net027 vout gnda rppolywo_m lr=4e-6\n",
            "xc0 outn net027 cfmom_2t nr=94\n",
            ".ends amp\n",
        ]
        packet = {
            "proof_status": "candidate_requires_review",
            "candidates": [
                {
                    "source_instance": "xr0",
                    "candidate_type": "segmented_resistor_chain_source_equivalent",
                    "candidate_status": "candidate_requires_review",
                    "source_equivalent_spice": "xr0 net027 vout gnda rppolywo_m",
                    "chain": {"present": True, "device_count": 31, "start_net": "net027", "end_net": "vout"},
                    "unresolved": ["body_or_substrate_pin_has_no_magical_geometry:gnda"],
                },
                {
                    "source_instance": "xc0",
                    "candidate_type": "plate_coupling_capacitor_source_equivalent",
                    "candidate_status": "candidate_requires_review",
                    "source_equivalent_spice": "xc0 outn net027 cfmom_2t",
                    "coupling_capacitor_count": 4,
                    "coupling_capacitance_ff": 539.84,
                    "unresolved": ["source_capacitor_requires_plate_coupling_abstraction"],
                },
            ],
        }

        summary = verify_packet(source_lines=source, packet=packet)

        self.assertEqual(summary["status"], "formal_lvs_abstraction_verified")
        self.assertTrue(summary["formal_lvs_abstraction_ready"])
        self.assertTrue(summary["all_candidates_formal_lvs_abstraction_ready"])
        self.assertFalse(summary["full_passive_aware_lvs_proven"])
        self.assertTrue(summary["all_source_passives_have_candidate"])
        self.assertTrue(summary["all_source_equivalents_match"])
        self.assertTrue(summary["all_candidate_support_verified"])
        self.assertEqual(summary["remaining_unresolved_blockers"], [])
        self.assertEqual(summary["missing_source_passive_instances"], [])
        self.assertEqual(len(summary["candidate_checks"]), 2)
        checks = {item["source_instance"]: item for item in summary["candidate_checks"]}
        self.assertEqual(
            checks["xr0"]["abstraction_rule"],
            "collapse_segmented_resistor_chain_to_lvs_resistor",
        )
        self.assertEqual(checks["xr0"]["lvs_primitive_device_class"], "r")
        self.assertEqual(checks["xr0"]["lvs_primitive_kind"], "resistor")
        self.assertEqual(checks["xr0"]["lvs_primitive_spice"], "R_xr0 net027 vout 1")
        self.assertEqual(
            checks["xc0"]["abstraction_rule"],
            "collapse_plate_coupling_evidence_to_lvs_capacitor",
        )
        self.assertEqual(checks["xc0"]["lvs_primitive_device_class"], "c")
        self.assertEqual(checks["xc0"]["lvs_primitive_kind"], "capacitor")
        self.assertEqual(checks["xc0"]["lvs_primitive_spice"], "C_xc0 outn net027 1f")

        source_abs, candidate_abs = abstraction_netlists(
            source_lines=source,
            packet=packet,
            top_cell="AMP",
        )
        self.assertIn(".subckt AMP_source_passive_abs net027 outn vout", source_abs)
        self.assertIn("R_xr0 net027 vout 1", source_abs)
        self.assertIn("C_xc0 outn net027 1f", source_abs)
        self.assertIn(".subckt AMP_candidate_passive_abs net027 outn vout", candidate_abs)
        self.assertIn("R_xr0 net027 vout 1", candidate_abs)
        self.assertIn("C_xc0 outn net027 1f", candidate_abs)

    def test_keeps_review_status_for_unknown_unresolved_blocker(self) -> None:
        source = [
            ".subckt amp net027 vout\n",
            "xr0 net027 vout gnda rppolywo_m lr=4e-6\n",
            ".ends amp\n",
        ]
        packet = {
            "proof_status": "candidate_requires_review",
            "candidates": [
                {
                    "source_instance": "xr0",
                    "candidate_type": "segmented_resistor_chain_source_equivalent",
                    "candidate_status": "candidate_requires_review",
                    "source_equivalent_spice": "xr0 net027 vout gnda rppolywo_m",
                    "chain": {"present": True, "device_count": 31, "start_net": "net027", "end_net": "vout"},
                    "unresolved": ["unexpected_open_terminal"],
                }
            ],
        }

        summary = verify_packet(source_lines=source, packet=packet)

        self.assertEqual(summary["status"], "candidate_requires_review")
        self.assertFalse(summary["formal_lvs_abstraction_ready"])
        self.assertEqual(summary["remaining_unresolved_blockers"], ["unexpected_open_terminal"])

    def test_fails_when_source_passive_has_no_candidate(self) -> None:
        source = [
            ".subckt amp gnda net027 outn vout\n",
            "xr0 net027 vout gnda rppolywo_m lr=4e-6\n",
            "xc0 outn net027 cfmom_2t nr=94\n",
            ".ends amp\n",
        ]
        packet = {
            "proof_status": "candidate_requires_review",
            "candidates": [
                {
                    "source_instance": "xc0",
                    "candidate_type": "plate_coupling_capacitor_source_equivalent",
                    "source_equivalent_spice": "xc0 outn net027 cfmom_2t",
                    "coupling_capacitor_count": 4,
                    "coupling_capacitance_ff": 539.84,
                    "unresolved": ["source_capacitor_requires_plate_coupling_abstraction"],
                }
            ],
        }

        summary = verify_packet(source_lines=source, packet=packet)

        self.assertEqual(summary["status"], "fail")
        self.assertFalse(summary["all_source_passives_have_candidate"])
        self.assertEqual(summary["missing_source_passive_instances"], ["xr0"])
        self.assertIn("missing_candidate:xr0", summary["structural_failures"])


if __name__ == "__main__":
    unittest.main()
