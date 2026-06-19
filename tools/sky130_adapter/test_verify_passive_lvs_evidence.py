#!/usr/bin/env python3
"""Tests for passive LVS evidence verification."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_passive_lvs_evidence import verify_evidence


class VerifyPassiveLvsEvidenceTest(unittest.TestCase):
    def test_accepts_formal_resistor_and_capacitor_lvs_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet_json = root / "packet_verification.json"
            source_abs = root / "source_abs.spice"
            candidate_abs = root / "candidate_abs.spice"
            packet_json.write_text(
                json.dumps(
                    {
                        "formal_lvs_abstraction_ready": True,
                        "all_source_passives_have_candidate": True,
                        "candidate_checks": [
                            {
                                "source_instance": "xr0",
                                "candidate_type": "segmented_resistor_chain_source_equivalent",
                                "abstraction_rule": "collapse_segmented_resistor_chain_to_lvs_resistor",
                                "lvs_primitive_device_class": "r",
                                "lvs_primitive_kind": "resistor",
                            },
                            {
                                "source_instance": "xc0",
                                "candidate_type": "plate_coupling_capacitor_source_equivalent",
                                "abstraction_rule": "collapse_plate_coupling_evidence_to_lvs_capacitor",
                                "lvs_primitive_device_class": "c",
                                "lvs_primitive_kind": "capacitor",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            source_abs.write_text(
                ".subckt src net027 outn vout\n"
                "R_xr0 net027 vout 1\n"
                "C_xc0 outn net027 1f\n"
                ".ends src\n",
                encoding="utf-8",
            )
            candidate_abs.write_text(
                ".subckt cand net027 outn vout\n"
                "R_xr0 net027 vout 1\n"
                "C_xc0 outn net027 1f\n"
                ".ends cand\n",
                encoding="utf-8",
            )
            summary = {
                "best_abstraction_packet_verification_json": str(packet_json),
                "best_abstraction_source_passive_abs_netlist": str(source_abs),
                "best_abstraction_candidate_passive_abs_netlist": str(candidate_abs),
                "best_passive_abs_netgen_status": "pass",
                "best_hybrid_mos_passive_lvs_trial_netgen_status": "pass",
                "best_passive_aware_lvs_trial_netgen_status": "fail",
            }

            result = verify_evidence(summary, require_resistor=True, require_capacitor=True)

            self.assertEqual(result["status"], "formal_passive_lvs_evidence_pass")
            self.assertEqual(
                result["verification_scope"],
                "formal_passive_abstraction_with_mos_only_projection",
            )
            self.assertTrue(result["formal_passive_lvs_evidence_pass"])
            self.assertFalse(result["full_passive_inclusive_gds_lvs_proven"])
            self.assertEqual(result["failed_requirements"], [])
            self.assertEqual(result["source_passive_primitive_counts"], {"resistor": 1, "capacitor": 1, "total": 2})
            records = {item["source_instance"]: item for item in result["lvs_primitive_abstractions"]}
            self.assertEqual(records["xr0"]["lvs_primitive_device_class"], "r")
            self.assertEqual(records["xc0"]["lvs_primitive_device_class"], "c")
            self.assertEqual(
                records["xc0"]["abstraction_rule"],
                "collapse_plate_coupling_evidence_to_lvs_capacitor",
            )

    def test_reports_incomplete_when_hybrid_netgen_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet_json = root / "packet_verification.json"
            source_abs = root / "source_abs.spice"
            candidate_abs = root / "candidate_abs.spice"
            packet_json.write_text(
                json.dumps(
                    {
                        "formal_lvs_abstraction_ready": True,
                        "all_source_passives_have_candidate": True,
                        "candidate_checks": [
                            {
                                "source_instance": "xr0",
                                "candidate_type": "segmented_resistor_chain_source_equivalent",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            source_abs.write_text(".subckt src a b\nR_xr0 a b 1\n.ends src\n", encoding="utf-8")
            candidate_abs.write_text(".subckt cand a b\nR_xr0 a b 1\n.ends cand\n", encoding="utf-8")
            summary = {
                "best_abstraction_packet_verification_json": str(packet_json),
                "best_abstraction_source_passive_abs_netlist": str(source_abs),
                "best_abstraction_candidate_passive_abs_netlist": str(candidate_abs),
                "best_passive_abs_netgen_status": "pass",
                "best_hybrid_mos_passive_lvs_trial_netgen_status": "skipped",
            }

            result = verify_evidence(summary, require_resistor=True)

            self.assertEqual(result["status"], "formal_passive_lvs_evidence_incomplete")
            self.assertFalse(result["formal_passive_lvs_evidence_pass"])
            self.assertEqual(
                result["failed_requirements"],
                ["hybrid_mos_reference_passive_netgen_lvs_pass"],
            )

    def test_full_gds_formal_trial_pass_does_not_claim_native_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet_json = root / "packet_verification.json"
            source_abs = root / "source_abs.spice"
            candidate_abs = root / "candidate_abs.spice"
            packet_json.write_text(
                json.dumps(
                    {
                        "formal_lvs_abstraction_ready": True,
                        "all_source_passives_have_candidate": True,
                        "candidate_checks": [
                            {
                                "source_instance": "xc0",
                                "candidate_type": "plate_coupling_capacitor_source_equivalent",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            source_abs.write_text(".subckt src a b\nC_xc0 a b 1f\n.ends src\n", encoding="utf-8")
            candidate_abs.write_text(".subckt cand a b\nC_xc0 a b 1f\n.ends cand\n", encoding="utf-8")
            summary = {
                "best_abstraction_packet_verification_json": str(packet_json),
                "best_abstraction_source_passive_abs_netlist": str(source_abs),
                "best_abstraction_candidate_passive_abs_netlist": str(candidate_abs),
                "best_passive_abs_netgen_status": "pass",
                "best_hybrid_mos_passive_lvs_trial_netgen_status": "pass",
                "best_passive_aware_lvs_trial_netgen_status": "pass",
            }

            result = verify_evidence(summary, require_capacitor=True)

            self.assertEqual(result["status"], "formal_passive_lvs_evidence_pass")
            self.assertEqual(
                result["verification_scope"],
                "formal_passive_abstraction_with_full_gds_mos",
            )
            self.assertTrue(result["formal_passive_lvs_evidence_pass"])
            self.assertTrue(result["full_gds_formal_passive_lvs_evidence_pass"])
            self.assertFalse(result["full_passive_inclusive_gds_lvs_proven"])
            self.assertFalse(result["native_passive_device_recognition_claimed"])

    def test_marks_full_gds_scope_only_with_explicit_native_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet_json = root / "packet_verification.json"
            source_abs = root / "source_abs.spice"
            candidate_abs = root / "candidate_abs.spice"
            packet_json.write_text(
                json.dumps(
                    {
                        "formal_lvs_abstraction_ready": True,
                        "all_source_passives_have_candidate": True,
                        "candidate_checks": [
                            {
                                "source_instance": "xc0",
                                "candidate_type": "plate_coupling_capacitor_source_equivalent",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            source_abs.write_text(".subckt src a b\nC_xc0 a b 1f\n.ends src\n", encoding="utf-8")
            candidate_abs.write_text(".subckt cand a b\nC_xc0 a b 1f\n.ends cand\n", encoding="utf-8")
            summary = {
                "best_abstraction_packet_verification_json": str(packet_json),
                "best_abstraction_source_passive_abs_netlist": str(source_abs),
                "best_abstraction_candidate_passive_abs_netlist": str(candidate_abs),
                "best_passive_abs_netgen_status": "pass",
                "best_hybrid_mos_passive_lvs_trial_netgen_status": "pass",
                "best_passive_aware_lvs_trial_netgen_status": "pass",
                "best_native_passive_device_recognition_status": "pass",
                "best_native_passive_device_recognition_claimed": True,
            }

            result = verify_evidence(summary, require_capacitor=True)

            self.assertEqual(result["status"], "full_passive_inclusive_gds_lvs_pass")
            self.assertEqual(result["verification_scope"], "full_passive_inclusive_gds_lvs")
            self.assertTrue(result["formal_passive_lvs_evidence_pass"])
            self.assertTrue(result["full_passive_inclusive_gds_lvs_proven"])
            self.assertTrue(result["native_passive_device_recognition_claimed"])

    def test_native_recognition_without_full_gds_lvs_does_not_claim_full_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet_json = root / "packet_verification.json"
            source_abs = root / "source_abs.spice"
            candidate_abs = root / "candidate_abs.spice"
            packet_json.write_text(
                json.dumps(
                    {
                        "formal_lvs_abstraction_ready": True,
                        "all_source_passives_have_candidate": True,
                        "candidate_checks": [
                            {
                                "source_instance": "xc0",
                                "candidate_type": "plate_coupling_capacitor_source_equivalent",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            source_abs.write_text(".subckt src a b\nC_xc0 a b 1f\n.ends src\n", encoding="utf-8")
            candidate_abs.write_text(".subckt cand a b\nC_xc0 a b 1f\n.ends cand\n", encoding="utf-8")
            summary = {
                "best_abstraction_packet_verification_json": str(packet_json),
                "best_abstraction_source_passive_abs_netlist": str(source_abs),
                "best_abstraction_candidate_passive_abs_netlist": str(candidate_abs),
                "best_passive_abs_netgen_status": "pass",
                "best_hybrid_mos_passive_lvs_trial_netgen_status": "pass",
                "best_passive_aware_lvs_trial_netgen_status": "fail",
                "best_native_passive_device_recognition_status": "pass",
                "best_native_passive_device_recognition_claimed": True,
            }

            result = verify_evidence(summary, require_capacitor=True)

            self.assertEqual(result["status"], "formal_passive_lvs_evidence_pass")
            self.assertEqual(
                result["verification_scope"],
                "formal_passive_abstraction_with_mos_only_projection",
            )
            self.assertTrue(result["native_passive_device_recognition_claimed"])
            self.assertFalse(result["full_passive_inclusive_gds_lvs_proven"])

    def test_promotes_scope_when_route_bridge_gds_trial_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet_json = root / "packet_verification.json"
            source_abs = root / "source_abs.spice"
            candidate_abs = root / "candidate_abs.spice"
            packet_json.write_text(
                json.dumps(
                    {
                        "formal_lvs_abstraction_ready": True,
                        "all_source_passives_have_candidate": True,
                        "candidate_checks": [
                            {
                                "source_instance": "xr0",
                                "candidate_type": "segmented_resistor_chain_source_equivalent",
                            },
                            {
                                "source_instance": "xc0",
                                "candidate_type": "plate_coupling_capacitor_source_equivalent",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            source_abs.write_text(
                ".subckt src a b c\nR_xr0 a b 1\nC_xc0 b c 1f\n.ends src\n",
                encoding="utf-8",
            )
            candidate_abs.write_text(
                ".subckt cand a b c\nR_xr0 a b 1\nC_xc0 b c 1f\n.ends cand\n",
                encoding="utf-8",
            )
            summary = {
                "best_abstraction_packet_verification_json": str(packet_json),
                "best_abstraction_source_passive_abs_netlist": str(source_abs),
                "best_abstraction_candidate_passive_abs_netlist": str(candidate_abs),
                "best_passive_abs_netgen_status": "pass",
                "best_hybrid_mos_passive_lvs_trial_netgen_status": "pass",
                "best_passive_aware_lvs_trial_netgen_status": "fail",
                "best_route_bridge_injection_status": "bridges_inserted",
                "best_route_bridge_drc_count": 0,
                "best_route_bridge_mos_connectivity_status": "pass",
                "best_route_bridge_formal_passive_lvs_netgen_status": "pass",
            }

            result = verify_evidence(summary, require_resistor=True, require_capacitor=True)

            self.assertEqual(result["status"], "formal_passive_lvs_evidence_pass")
            self.assertEqual(
                result["verification_scope"],
                "formal_passive_abstraction_with_gds_mos_bridge",
            )
            self.assertTrue(result["route_bridge_formal_passive_lvs_evidence_pass"])
            self.assertFalse(result["full_passive_inclusive_gds_lvs_proven"])


if __name__ == "__main__":
    unittest.main()
