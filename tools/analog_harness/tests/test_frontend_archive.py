#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.analog_harness.archive import KnowledgeTransferArchive
from tools.analog_harness.config import load_harness_config
from tools.analog_harness.frontend import FrontEndResultLoader
from tools.analog_harness.legalizer import SizingLegalizer
from tools.analog_harness.optimizer import AnalogGymGRPOAdapter


class FrontendArchiveTest(unittest.TestCase):
    def test_frontend_loader_prefers_existing_candidate_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "source.sp"
            config_json = root / "source.json"
            source.write_text(".subckt amp vdd vss out\n.ends amp\n", encoding="utf-8")
            config_json.write_text("{}", encoding="utf-8")
            frontend_dir = root / "frontend" / "cand_0001"
            frontend_dir.mkdir(parents=True)
            (frontend_dir / "state.json").write_text(
                json.dumps(
                    {
                        "candidate_id": "cand_0001",
                        "values": {"m0_w": 3.0},
                        "reward": 0.2,
                        "closure_level": "L1_pre_layout_nominal",
                    }
                ),
                encoding="utf-8",
            )
            harness = self._write_config(root, source, config_json, frontend_dir.parent)
            config = load_harness_config(harness)
            legalizer = SizingLegalizer(config.variables)

            proposals = FrontEndResultLoader(config, legalizer).proposals([])

            self.assertEqual(len(proposals), 1)
            self.assertEqual(proposals[0].source, "frontend_result")
            self.assertEqual(proposals[0].values["m0_w"], 3.0)
            self.assertIn("frontend_origin_id", proposals[0].metadata)

    def test_archive_writes_warm_start_bank_and_feedback_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "source.sp"
            config_json = root / "source.json"
            source.write_text(".subckt amp vdd vss out\n.ends amp\n", encoding="utf-8")
            config_json.write_text("{}", encoding="utf-8")
            harness = self._write_config(root, source, config_json, root / "missing_frontend")
            config = load_harness_config(harness)
            archive = KnowledgeTransferArchive(config)

            archived = archive.consider(
                {
                    "candidate_id": "cand_0001",
                    "design_id": "test_amp",
                    "top_cell": "amp",
                    "values": {"m0_w": 3.0},
                    "reward": 0.1,
                    "closure_level": "L1_pre_layout_nominal",
                    "verification_scope": "mos_only_projection",
                    "evidence": [{"fidelity": "E0", "status": "pass", "metrics": {"dcgain": 80}}],
                }
            )

            self.assertTrue(archived)
            self.assertTrue((root / "archive" / "warm_start_bank.json").is_file())
            self.assertTrue((root / "archive" / "proxy_feedback_dataset.jsonl").is_file())
            records = archive.warm_start_records()
            self.assertEqual(records[0]["values"]["m0_w"], 3.0)

    def test_frontend_loader_skips_repair_requested_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "source.sp"
            config_json = root / "source.json"
            source.write_text(".subckt amp vdd vss out\n.ends amp\n", encoding="utf-8")
            config_json.write_text("{}", encoding="utf-8")
            frontend_dir = root / "frontend" / "cand_0001"
            frontend_dir.mkdir(parents=True)
            (frontend_dir / "state.json").write_text(
                json.dumps(
                    {
                        "candidate_id": "cand_0001",
                        "values": {"m0_w": 3.0},
                        "reward": 0.2,
                        "redesign_request": {"owner": "sizing_optimizer"},
                    }
                ),
                encoding="utf-8",
            )
            harness = self._write_config(root, source, config_json, frontend_dir.parent)
            config = load_harness_config(harness)
            legalizer = SizingLegalizer(config.variables)

            proposals = FrontEndResultLoader(config, legalizer).proposals([])

            self.assertEqual(proposals, [])

    def test_optimizer_uses_layout_safe_seed_after_layout_repair(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "source.sp"
            config_json = root / "source.json"
            source.write_text(".subckt amp vdd vss out\n.ends amp\n", encoding="utf-8")
            config_json.write_text("{}", encoding="utf-8")
            harness = self._write_config(root, source, config_json, root / "missing_frontend")
            config = load_harness_config(harness)
            legalizer = SizingLegalizer(config.variables)
            optimizer = AnalogGymGRPOAdapter(config, legalizer)
            optimizer.initialize(
                {},
                [
                    {
                        "values": {"m0_w": 4.0},
                        "reward": 0.5,
                        "redesign_request": {
                            "reasons": ["layout_verification:fail"],
                        },
                    }
                ],
            )

            proposal = optimizer.propose({}, 1)[0]

            self.assertEqual(proposal.metadata["proposal_mode"], "layout_safe_sizing_repair")
            self.assertEqual(proposal.values["m0_w"], 2.0)

    def test_optimizer_uses_model_safe_seed_after_model_bin_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "source.sp"
            config_json = root / "source.json"
            source.write_text(".subckt amp vdd vss out\n.ends amp\n", encoding="utf-8")
            config_json.write_text("{}", encoding="utf-8")
            harness = self._write_config(root, source, config_json, root / "missing_frontend")
            config = load_harness_config(harness)
            legalizer = SizingLegalizer(config.variables)
            optimizer = AnalogGymGRPOAdapter(config, legalizer)
            optimizer.initialize(
                {},
                [
                    {
                        "values": {"m0_w": 4.0},
                        "reward": 0.5,
                        "redesign_request": {
                            "action": "propose_model_safe_sizing",
                            "reasons": ["post_sim:sky130_model_bin_mismatch"],
                        },
                    }
                ],
            )

            proposal = optimizer.propose({}, 1)[0]

            self.assertEqual(proposal.metadata["proposal_mode"], "model_safe_sizing_repair")
            self.assertEqual(proposal.values["m0_w"], 1.5)

    def test_optimizer_prepares_grpo_long_training_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "source.sp"
            config_json = root / "source.json"
            source.write_text(".subckt amp vdd vss out\n.ends amp\n", encoding="utf-8")
            config_json.write_text("{}", encoding="utf-8")
            harness = self._write_config(root, source, config_json, root / "missing_frontend")
            config = load_harness_config(harness)
            legalizer = SizingLegalizer(config.variables)
            optimizer = AnalogGymGRPOAdapter(config, legalizer)
            optimizer.initialize({}, [])

            manifest = optimizer.prepare_long_training_interface(root / "archive", steps=123)

            self.assertEqual(manifest["requested_steps"], 123)
            self.assertEqual(manifest["status"], "prepared_not_executed")
            self.assertTrue((root / "archive" / "grpo_warm_start_training_manifest.json").is_file())
            self.assertTrue((root / "archive" / "run_grpo_warm_start_training.ps1").is_file())

    @staticmethod
    def _write_config(root: Path, source: Path, config_json: Path, frontend_source: Path) -> Path:
        harness = root / "harness.yaml"
        harness.write_text(
            f"""
design_id: test_amp
top_cell: amp
paths:
  source_netlist: {source}
  source_config: {config_json}
  runs_dir: {root / "runs"}
ports: {{vdd: vdd, vss: vss, output: out}}
frontend_results:
  enabled: true
  sources: [{frontend_source}]
knowledge_transfer:
  enabled: true
  archive_dir: {root / "archive"}
  min_reward: -0.5
  preserve_model_artifacts: false
optimizer:
  model_safe_repair_values:
    m0_w: 1.5
sizing_variables:
  - {{name: m0_w, kind: device, instances: [xm0], param: w, min: 1, max: 4, init: 2, step: 0.5, unit: u}}
""",
            encoding="utf-8",
        )
        return harness


if __name__ == "__main__":
    unittest.main()
