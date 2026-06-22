import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.analog_harness.diagnostics.artifact_verifier import (
    verify_artifact_map,
    verify_artifact_path,
    verify_evidence_packets,
    verify_state_artifacts,
)
from tools.analog_harness.diagnostics.lvs_failure_taxonomy import classify_lvs_summary
from tools.analog_harness.diagnostics.pex_structuring import summarize_pex_caps
from tools.analog_harness.diagnostics.sample_trust_gate import (
    decide_sample_trust,
    decide_sample_trust_from_state,
)


class DiagnosticsPackageTest(unittest.TestCase):
    def test_imports_diagnostics_package(self):
        import tools.analog_harness.diagnostics as diagnostics

        self.assertTrue(hasattr(diagnostics, "__all__"))


class LvsFailureTaxonomyTest(unittest.TestCase):
    def test_classifies_clean_lvs_summary(self):
        text = """
        LVS status: **PASS**
        Device mismatch detected: no
        Net mismatch detected: no
        Property mismatch detected: no
        """

        diagnosis = classify_lvs_summary(text)

        self.assertTrue(diagnosis["lvs_match"])
        self.assertEqual(diagnosis["status"], "pass")
        self.assertEqual(diagnosis["failure_categories"], [])

    def test_classifies_net_and_device_mismatch(self):
        text = """
        LVS status: **FAIL**
        Device mismatch detected: yes
        Net mismatch detected: yes
        Property mismatch detected: no
        """

        diagnosis = classify_lvs_summary(text)

        self.assertFalse(diagnosis["lvs_match"])
        self.assertEqual(diagnosis["status"], "fail")
        self.assertIn("device_mismatch", diagnosis["failure_categories"])
        self.assertIn("net_mismatch", diagnosis["failure_categories"])

    def test_classifies_common_netgen_unique_match_phrase(self):
        text = """
        Subcircuit summary:
        Circuits match uniquely.
        Netlists match uniquely.
        """

        diagnosis = classify_lvs_summary(text)

        self.assertEqual(diagnosis["status"], "pass")
        self.assertTrue(diagnosis["lvs_match"])
        self.assertEqual(diagnosis["failure_categories"], [])

    def test_classifies_common_netgen_mismatch_phrases(self):
        text = """
        Netlists do not match.
        Device classes Leung_DFCFC2 and Leung_DFCFC2_flat are not equivalent.
        Property errors were found.
        """

        diagnosis = classify_lvs_summary(text)

        self.assertEqual(diagnosis["status"], "fail")
        self.assertFalse(diagnosis["lvs_match"])
        self.assertIn("device_mismatch", diagnosis["failure_categories"])
        self.assertIn("property_mismatch", diagnosis["failure_categories"])

    def test_classifies_power_domain_short_phrase(self):
        text = """
        LVS status: **FAIL**
        Extracted net vout appears shorted to vdda in the power domain.
        """

        diagnosis = classify_lvs_summary(text)

        self.assertEqual(diagnosis["status"], "fail")
        self.assertIn("power_domain_short", diagnosis["failure_categories"])

    def test_classifies_pin_label_overlap_phrase(self):
        text = """
        LVS status: **FAIL**
        Layout warning: vinn/vinp pin label overlap near top-level port text.
        """

        diagnosis = classify_lvs_summary(text)

        self.assertEqual(diagnosis["status"], "fail")
        self.assertIn("pin_label_overlap", diagnosis["failure_categories"])

    def test_classifies_missing_top_port_label_phrase(self):
        text = """
        LVS status: **FAIL**
        Missing top port label for net vout in extracted layout.
        """

        diagnosis = classify_lvs_summary(text)

        self.assertEqual(diagnosis["status"], "fail")
        self.assertIn("missing_top_port_label", diagnosis["failure_categories"])


class SampleTrustGateTest(unittest.TestCase):
    def test_positive_full_scope_sample_is_training_usable(self):
        decision = decide_sample_trust(
            {
                "candidate_id": "cand_0031",
                "drc_clean": True,
                "lvs_match": True,
                "pex_available": True,
                "post_sim_valid": True,
                "pvt_valid": True,
                "evidence_scope": "full_passive_inclusive_gds_lvs",
            }
        )

        self.assertTrue(decision["usable_for_reward"])
        self.assertTrue(decision["usable_for_post_sim"])
        self.assertTrue(decision["usable_for_training"])
        self.assertTrue(decision["usable_for_parasitic_modeling"])
        self.assertFalse(decision["usable_only_as_failure_case"])
        self.assertEqual(decision["reasons"], [])

    def test_lvs_failure_is_failure_case_not_training_sample(self):
        decision = decide_sample_trust(
            {
                "candidate_id": "dfcfc2_probe",
                "drc_clean": True,
                "lvs_match": False,
                "pex_available": True,
                "post_sim_valid": False,
                "pvt_valid": False,
                "evidence_scope": "mos_only_projection",
            }
        )

        self.assertFalse(decision["usable_for_reward"])
        self.assertFalse(decision["usable_for_post_sim"])
        self.assertFalse(decision["usable_for_training"])
        self.assertTrue(decision["usable_for_parasitic_modeling"])
        self.assertTrue(decision["usable_only_as_failure_case"])
        self.assertIn("lvs_not_matched", decision["reasons"])
        self.assertIn("post_sim_invalid", decision["reasons"])
        self.assertIn("pvt_invalid", decision["reasons"])

    def test_dfcfc2_or_smc_lvs_failure_maps_to_failure_case(self):
        from tools.analog_harness.diagnostics.sample_trust_gate import (
            decide_sample_trust_from_lvs_text,
        )

        lvs_text = """
        Circuit 1 contains 24 devices, Circuit 2 contains 24 devices.
        Circuit 1 contains 18 nets,    Circuit 2 contains 39 nets. *** MISMATCH ***
        Final result:
        Netlists do not match.
        """
        result = decide_sample_trust_from_lvs_text(
            {
                "candidate_id": "fan_smc_no_c0_extract_b1",
                "drc_clean": True,
                "lvs_match": True,
                "pex_available": True,
                "post_sim_valid": False,
                "pvt_valid": False,
                "evidence_scope": "mos_only_projection",
            },
            lvs_text,
        )

        self.assertEqual(set(result), {"lvs_diagnosis", "trust_decision"})
        diagnosis = result["lvs_diagnosis"]
        decision = result["trust_decision"]
        self.assertEqual(diagnosis["status"], "fail")
        self.assertFalse(diagnosis["lvs_match"])
        self.assertIn("net_mismatch", diagnosis["failure_categories"])
        self.assertFalse(decision["usable_for_reward"])
        self.assertFalse(decision["usable_for_post_sim"])
        self.assertFalse(decision["usable_for_training"])
        self.assertTrue(decision["usable_only_as_failure_case"])
        self.assertIn("lvs_not_matched", decision["reasons"])
        self.assertNotIn("net_mismatch", decision["reasons"])

    def test_derives_training_usable_decision_from_candidate_state(self):
        state = {
            "candidate_id": "cand_0031",
            "evidence": [
                {
                    "stage": "layout_verification",
                    "status": "pass",
                    "verification_scope": "mos_only_projection",
                    "metrics": {
                        "drc_count": 0,
                        "lvs_match": "yes",
                        "pex_caps": 37,
                    },
                },
                {
                    "stage": "passive_aware_lvs",
                    "status": "pass",
                    "verification_scope": "full_passive_inclusive_gds_lvs",
                    "metrics": {
                        "full_passive_inclusive_gds_lvs_proven": True,
                    },
                },
                {"stage": "post_sim", "status": "pass", "metrics": {}},
                {
                    "stage": "pvt_sim",
                    "status": "pass",
                    "metrics": {
                        "pvt_passed_corners": 3,
                        "pvt_total_corners": 3,
                    },
                },
            ],
        }

        decision = decide_sample_trust_from_state(state)

        self.assertEqual(decision["candidate_id"], "cand_0031")
        self.assertEqual(decision["evidence_scope"], "full_passive_inclusive_gds_lvs")
        self.assertTrue(decision["usable_for_training"])
        self.assertTrue(decision["usable_for_reward"])

    def test_derives_decision_from_packaged_smcnr_state(self):
        state_path = Path(
            "reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/state.json"
        )
        state = json.loads(state_path.read_text())

        decision = decide_sample_trust_from_state(state)

        self.assertEqual(decision["candidate_id"], "cand_0031")
        self.assertEqual(decision["evidence_scope"], "full_passive_inclusive_gds_lvs")
        self.assertTrue(decision["usable_for_reward"])
        self.assertTrue(decision["usable_for_post_sim"])
        self.assertTrue(decision["usable_for_training"])
        self.assertTrue(decision["usable_for_parasitic_modeling"])
        self.assertFalse(decision["usable_only_as_failure_case"])


class ArtifactVerifierTest(unittest.TestCase):
    def test_existing_local_path_is_present(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "summary.json"
            path.write_text("{}", encoding="utf-8")

            report = verify_artifact_path(str(path), repo_root=Path(tmp))

            self.assertEqual(report["status"], "present")
            self.assertTrue(report["portable"])

    def test_generated_path_missing_is_generated_only(self):
        report = verify_artifact_path(
            "generated/analog_harness/smcnr/cand_0001/magic.log",
            repo_root=Path("."),
        )

        self.assertEqual(report["status"], "generated_only_reference")
        self.assertFalse(report["portable"])

    def test_windows_absolute_path_is_not_portable(self):
        report = verify_artifact_path(
            r"E:\codex-magical-sky130-harness\generated\analog_harness\smcnr\cand_0031\layout\summary.md",
            repo_root=Path("."),
        )

        self.assertEqual(report["status"], "not_portable")
        self.assertFalse(report["portable"])
        self.assertEqual(report["reason"], "windows_absolute_path")

    def test_verifies_artifact_map_with_status_counts(self):
        with TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            present = repo_root / "curated" / "summary.json"
            present.parent.mkdir()
            present.write_text("{}", encoding="utf-8")

            report = verify_artifact_map(
                {
                    "summary": "curated/summary.json",
                    "generated_log": "generated/analog_harness/cand/log.txt",
                    "windows_log": r"E:\run\cand\layout.log",
                    "missing": "not_there/report.md",
                    "non_path_note": "True",
                },
                repo_root=repo_root,
            )

        self.assertEqual(report["artifact_count"], 5)
        self.assertEqual(report["status_counts"]["present"], 1)
        self.assertEqual(report["status_counts"]["generated_only_reference"], 1)
        self.assertEqual(report["status_counts"]["not_portable"], 1)
        self.assertEqual(report["status_counts"]["missing"], 2)
        self.assertEqual(report["artifacts"]["windows_log"]["reason"], "windows_absolute_path")

    def test_verifies_evidence_packets_by_stage(self):
        with TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            present = repo_root / "layout" / "summary.md"
            present.parent.mkdir()
            present.write_text("ok", encoding="utf-8")

            report = verify_evidence_packets(
                [
                    {
                        "stage": "layout_verification",
                        "artifacts": {
                            "summary": "layout/summary.md",
                            "run_log": r"E:\run\layout_adapter_run.log",
                        },
                    },
                    {
                        "stage": "passive_aware_lvs",
                        "artifacts": {
                            "native_report": "generated/analog_harness/cand/passive.md",
                        },
                    },
                ],
                repo_root=repo_root,
            )

        self.assertEqual(report["packet_count"], 2)
        self.assertEqual(report["artifact_count"], 3)
        self.assertEqual(report["status_counts"]["present"], 1)
        self.assertEqual(report["status_counts"]["not_portable"], 1)
        self.assertEqual(report["status_counts"]["generated_only_reference"], 1)
        self.assertEqual(
            report["stage_reports"]["layout_verification"]["status_counts"]["present"],
            1,
        )

    def test_verifies_packaged_smcnr_state_artifact_counts(self):
        state_path = Path(
            "reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/state.json"
        )
        state = json.loads(state_path.read_text())

        report = verify_evidence_packets(state["evidence"], repo_root=Path("."))

        self.assertEqual(report["packet_count"], 5)
        self.assertEqual(report["artifact_count"], 86)
        self.assertEqual(report["status_counts"]["not_portable"], 30)
        self.assertEqual(report["status_counts"]["generated_only_reference"], 28)
        self.assertEqual(report["status_counts"]["missing"], 28)
        self.assertEqual(
            report["stage_reports"]["passive_aware_lvs"]["artifact_count"], 41
        )
        self.assertEqual(
            report["stage_reports"]["passive_aware_lvs"]["status_counts"][
                "generated_only_reference"
            ],
            28,
        )

    def test_verifies_candidate_state_artifacts(self):
        with TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            present = repo_root / "layout" / "summary.md"
            present.parent.mkdir()
            present.write_text("ok", encoding="utf-8")

            report = verify_state_artifacts(
                {
                    "candidate_id": "cand_probe",
                    "evidence": [
                        {
                            "stage": "layout_verification",
                            "artifacts": {
                                "summary": "layout/summary.md",
                                "log": r"E:\run\layout.log",
                            },
                        }
                    ],
                },
                repo_root=repo_root,
            )

        self.assertEqual(report["candidate_id"], "cand_probe")
        self.assertEqual(report["packet_count"], 1)
        self.assertEqual(report["artifact_count"], 2)
        self.assertEqual(report["status_counts"]["present"], 1)
        self.assertEqual(report["status_counts"]["not_portable"], 1)

    def test_verifies_packaged_smcnr_state_at_state_level(self):
        state_path = Path(
            "reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/state.json"
        )
        state = json.loads(state_path.read_text())

        report = verify_state_artifacts(state, repo_root=Path("."))

        self.assertEqual(report["candidate_id"], "cand_0031")
        self.assertEqual(report["packet_count"], 5)
        self.assertEqual(report["artifact_count"], 86)
        self.assertEqual(report["status_counts"]["not_portable"], 30)


class PexStructuringTest(unittest.TestCase):
    def test_summarizes_simple_capacitors_in_ff(self):
        spice = """
        C0 vout gnda 1.5f
        C1 vdda gnda 2.0f
        R0 vout net1 10
        """

        summary = summarize_pex_caps(spice)

        self.assertEqual(summary["pex_caps"], 2)
        self.assertAlmostEqual(summary["pex_total_cap_ff"], 3.5)
        self.assertAlmostEqual(summary["per_node_cap_ff"]["vout"], 1.5)
        self.assertAlmostEqual(summary["per_node_cap_ff"]["gnda"], 3.5)


if __name__ == "__main__":
    unittest.main()
