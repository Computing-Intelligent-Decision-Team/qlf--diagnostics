from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import yaml

from tools.analog_harness.grpo_to_pcs_admission_runner import (
    build_admission_summary,
    prepare_candidate_configs,
    run_admission_batch,
)


class GrpoToPcsAdmissionRunnerTest(unittest.TestCase):
    def test_prepare_candidate_configs_isolates_runs_dir_per_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base_config = root / "base.yaml"
            base_config.write_text(
                yaml.safe_dump(
                    {
                        "design_id": "leung_dfcfc2_pin_3",
                        "top_cell": "leung_dfcfc2_pin_3",
                        "paths": {"runs_dir": "generated/old"},
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            manifest = {
                "config": str(base_config),
                "design_id": "leung_dfcfc2_pin_3",
                "family_id": "family_v1",
                "jobs": [
                    {"candidate_id": "c0", "source_state": "states/c0.json", "expected_flow": {"run_post_sim": True}},
                    {"candidate_id": "c1", "source_state": "states/c1.json", "expected_flow": {"run_post_sim": True}},
                ],
            }

            plans = prepare_candidate_configs(manifest, output_dir=root / "batch")

            self.assertEqual([plan.candidate_id for plan in plans], ["c0", "c1"])
            self.assertEqual(
                yaml.safe_load((root / "batch/configs/c0.yaml").read_text(encoding="utf-8"))["paths"]["runs_dir"],
                str((root / "batch/runs/c0").resolve()),
            )
            self.assertEqual(
                yaml.safe_load((root / "batch/configs/c1.yaml").read_text(encoding="utf-8"))["paths"]["runs_dir"],
                str((root / "batch/runs/c1").resolve()),
            )
            self.assertEqual(
                yaml.safe_load(base_config.read_text(encoding="utf-8"))["paths"]["runs_dir"],
                "generated/old",
            )

    def test_dry_run_writes_reproducible_plan_without_running_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base_config = root / "base.yaml"
            base_config.write_text(
                yaml.safe_dump({"design_id": "d", "top_cell": "d", "paths": {"runs_dir": "old"}}),
                encoding="utf-8",
            )
            batch_manifest = root / "batch_replay_manifest.json"
            batch_manifest.write_text(
                json.dumps(
                    {
                        "config": str(base_config),
                        "design_id": "d",
                        "family_id": "family",
                        "jobs": [
                            {
                                "candidate_id": "c0",
                                "source_state": "source_states/c0.source_state.json",
                                "expected_flow": {"run_post_sim": False},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = run_admission_batch(
                batch_replay_manifest=batch_manifest,
                output_dir=root / "out",
                timeout_s=1800,
                kill_after_s=60,
                dry_run=True,
            )

            self.assertEqual(result["status"], "dry_run")
            self.assertEqual(result["total"], 1)
            plan = json.loads((root / "out/run_plan.json").read_text(encoding="utf-8"))
            self.assertEqual(plan["jobs"][0]["candidate_id"], "c0")
            self.assertIn("--skip-sim", plan["jobs"][0]["command"])
            self.assertEqual(json.loads((root / "out/promotion_progress.json").read_text())["status"], "dry_run")

    def test_build_admission_summary_classifies_l6_lvs_fail_and_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_dir = root / "batch"
            source_dir = output_dir / "l0/source_states"
            source_dir.mkdir(parents=True)
            for cid in ("c_l6", "c_lvs", "c_timeout"):
                (source_dir / f"{cid}.source_state.json").write_text(
                    json.dumps({"values": {"mosfet_12_1_m_gmf2_pmos": 100}, "optimizer_metadata": {}}),
                    encoding="utf-8",
                )

            def write_layout(cid: str, closure: str | None, status: str | None, raw: bool) -> None:
                run = output_dir / "runs" / cid
                if closure is not None:
                    run.mkdir(parents=True)
                    (run / "summary.json").write_text(json.dumps({"best_closure_level": closure}), encoding="utf-8")
                layout = run / "cand_0001/layout"
                layout.mkdir(parents=True)
                if status:
                    (layout / "summary.md").write_text(status, encoding="utf-8")
                if raw:
                    (layout / "d_extracted.raw.spice").write_text("C0 vout gnda 2f\n", encoding="utf-8")

            write_layout("c_l6", "L6_post_layout_pvt", None, True)
            write_layout(
                "c_lvs",
                "L2_pre_layout_pvt",
                "| FAILED_STAGE | connectivity_lvs |\n",
                True,
            )
            write_layout(
                "c_timeout",
                None,
                "| MAGICAL_RESULT | pass |\n| DRC_COUNT | 0 |\n| PEX_CAPS | 1 |\n",
                True,
            )
            (output_dir / "promotion_results.jsonl").write_text(
                "\n".join(
                    [
                        json.dumps({"candidate_id": "c_l6", "returncode": 0, "summary": {"best_closure_level": "L6_post_layout_pvt"}}),
                        json.dumps({"candidate_id": "c_lvs", "returncode": 0, "summary": {"best_closure_level": "L2_pre_layout_pvt"}}),
                        json.dumps({"candidate_id": "c_timeout", "returncode": 124, "summary": None}),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            manifest = {
                "design_id": "d",
                "family_id": "family",
                "config": "config.yaml",
                "jobs": [
                    {"candidate_id": "c_l6", "source_state": str(source_dir / "c_l6.source_state.json")},
                    {"candidate_id": "c_lvs", "source_state": str(source_dir / "c_lvs.source_state.json")},
                    {"candidate_id": "c_timeout", "source_state": str(source_dir / "c_timeout.source_state.json")},
                ],
            }

            summary = build_admission_summary(
                output_dir=output_dir,
                batch_manifest=manifest,
                source_state_dir=source_dir,
                timeout_s=1800,
                kill_after_s=60,
            )

            self.assertEqual(summary["counts"]["l6_admitted_raw_pex_graph"], 1)
            self.assertEqual(summary["counts"]["raw_pex_available_not_l6"], 1)
            self.assertEqual(summary["counts"]["simulation_timeout_or_hang"], 1)
            statuses = {row["candidate_id"]: row["admission_status"] for row in summary["records"]}
            self.assertEqual(statuses["c_l6"], "admitted_raw_pex_graph")
            self.assertEqual(statuses["c_lvs"], "raw_pex_available_not_l6")
            self.assertEqual(statuses["c_timeout"], "simulation_timeout_or_hang")


if __name__ == "__main__":
    unittest.main()
