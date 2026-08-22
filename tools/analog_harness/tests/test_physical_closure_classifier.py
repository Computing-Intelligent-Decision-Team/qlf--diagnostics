#!/usr/bin/env python3
"""Tests for the GRPO→PCS physical closure classifier helpers."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from tools.analog_harness.ml.physical_closure_classifier import (  # noqa: E402
    CandidateRow,
    compute_metrics,
    derived_features,
    load_rows_and_features,
    matrix_rows,
)


class TestDerivedFeatures(unittest.TestCase):
    def test_uses_sizing_and_action_features(self) -> None:
        values = {
            "mosfet_12_1_w_gmf2_pmos": 0.5,
            "mosfet_12_1_l_gmf2_pmos": 2.8,
            "mosfet_12_1_m_gmf2_pmos": 339,
            "mosfet_23_2_w_load2_nmos": 5.6,
            "mosfet_23_2_l_load2_nmos": 1.5,
            "mosfet_23_2_m_load2_nmos": 34,
            "capacitor_0": 26,
            "capacitor_1": 12,
            "current_0_bias": 10.5,
        }
        feats = derived_features(values, [0.1, -0.2])
        self.assertEqual(feats["sizing__mosfet_12_1_m_gmf2_pmos"], 339)
        self.assertEqual(feats["action_norm_00"], 0.1)
        self.assertEqual(feats["requested_cap_sum"], 38.0)
        self.assertEqual(feats["bias_current_sum"], 10.5)
        self.assertEqual(feats["mos_device_count"], 2.0)
        self.assertGreater(feats["mos_gate_area_proxy_sum"], 0.0)


class TestLabelsAndLeakage(unittest.TestCase):
    def test_matrix_keeps_outcome_fields_out_of_features(self) -> None:
        rows = [
            CandidateRow(
                sample_uid="b/c0",
                batch_id="b",
                candidate_id="c0",
                design_id="d",
                admission_status="admitted_raw_pex_graph",
                failure_stage="",
                best_closure_level="L6_post_layout_pvt",
                graph_training_admitted=1,
                raw_pex_available=1,
                physical_closure_failed_no_raw_pex=0,
                simulation_timeout_or_hang=0,
                source_state_path="state.json",
                source_state_resolved="/tmp/state.json",
                m12_m=339,
                pex_cap_count=118,
                pex_total_cap_ff=2001.0,
                raw_spice_sha256="abc",
            )
        ]
        matrix, feature_names = matrix_rows(rows, [{"sizing__x": 1.0, "record__m12_m": 339.0}])
        self.assertIn("sizing__x", feature_names)
        self.assertNotIn("pex_cap_count", feature_names)
        self.assertNotIn("pex_total_cap_ff", feature_names)
        self.assertEqual(matrix[0]["label_graph_training_admitted"], 1)
        self.assertEqual(matrix[0]["label_simulation_timeout_or_hang"], 0)

    def test_load_rows_resolves_source_state_from_pcs_root(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = root / "repo"
            pcs = root / "pcs"
            state_rel = Path("generated/analog_harness/run/source_states/c0.source_state.json")
            (pcs / state_rel).parent.mkdir(parents=True)
            (pcs / state_rel).write_text(
                json.dumps(
                    {
                        "values": {
                            "mosfet_12_1_w_gmf2_pmos": 0.5,
                            "mosfet_12_1_l_gmf2_pmos": 2.8,
                            "mosfet_12_1_m_gmf2_pmos": 339,
                        },
                        "action_normalized": [0.0],
                    }
                ),
                encoding="utf-8",
            )
            summary = repo / "summary.json"
            summary.parent.mkdir(parents=True)
            summary.write_text(
                json.dumps(
                    {
                        "batch_id": "batch",
                        "records": [
                            {
                                "candidate_id": "c0",
                                "design_id": "d",
                                "admission_status": "physical_closure_failed",
                                "best_closure_level": "L2_pre_layout_pvt",
                                "failure_stage": "magical_place_route",
                                "m12_m": 339,
                                "source_state_path": str(state_rel),
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            rows, features = load_rows_and_features([summary], repo, pcs)
            self.assertEqual(rows[0].graph_training_admitted, 0)
            self.assertEqual(rows[0].physical_closure_failed_no_raw_pex, 1)
            self.assertEqual(rows[0].simulation_timeout_or_hang, 0)
            self.assertEqual(features[0]["sizing__mosfet_12_1_m_gmf2_pmos"], 339)


class TestMetrics(unittest.TestCase):
    def test_compute_metrics(self) -> None:
        metrics = compute_metrics([1, 1, 0, 0], [1, 0, 1, 0])
        self.assertEqual(metrics["confusion_matrix"], {"tp": 1, "tn": 1, "fp": 1, "fn": 1})
        self.assertEqual(metrics["accuracy"], 0.5)
        self.assertEqual(metrics["balanced_accuracy"], 0.5)


if __name__ == "__main__":
    unittest.main()
