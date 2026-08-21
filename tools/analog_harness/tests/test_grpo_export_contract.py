import json
import tempfile
import unittest
from pathlib import Path

import yaml


class TestGrpoExportContract(unittest.TestCase):
    def test_builds_contract_export_from_analoggym_recommended_candidates(self):
        from tools.analog_harness.ml.grpo_export_contract import convert_analoggym_run_to_export

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = root / "amp_dfcfc2.yaml"
            cfg.write_text(
                yaml.safe_dump(
                    {
                        "device": {
                            "M0": {
                                "range": {"W": [0.5, 10], "L": [0.5, 5], "M": [1, 50]},
                                "step": {"W": 0.1, "L": 0.1, "M": 1},
                                "num": 8,
                            },
                            "M12": {
                                "range": {"W": [0.5, 10], "L": [0.5, 5], "M": [100, 500]},
                                "step": {"W": 0.1, "L": 0.1, "M": 1},
                                "num": 1,
                            },
                        }
                    },
                    sort_keys=False,
                )
            )
            run_dir = root / "training_saves" / "grpo_amp_dfcfc2_20260821-010203"
            cand_dir = run_dir / "recommended_candidates_tt"
            cand_dir.mkdir(parents=True)
            (cand_dir / "recommended_candidates.json").write_text(
                json.dumps(
                    [
                        {
                            "rank": 1,
                            "candidate_source": "final_test",
                            "design_idx": 7,
                            "training_reward": -0.25,
                            "utility": -0.25,
                            "pm_feasible": True,
                            "pm_violation": 0.0,
                            "evaluation_source": "tt",
                            "objective_rewards": {"constraint_reward": -0.1},
                            "action_normalized": [0.0, 0.0, 0.0, 0.2, -0.2, 0.5],
                            "action_real": [1.0, 1.0, 4, 2.0, 2.5, 227],
                            "performance": {"dcgain": 101.0, "phase_margin (deg)": 70.0},
                        }
                    ]
                )
            )

            export = convert_analoggym_run_to_export(
                run_dir=run_dir,
                circuit_config_path=cfg,
                source_repo=root,
                circuit_id="amp_dfcfc2",
                pcs_design_id="leung_dfcfc2_pin_3",
                action_space_contract_id="amp_dfcfc2_to_leung_dfcfc2_pin_3.analoggym_action_space_v1",
                mode="tt-only",
                steps=1,
                seed=None,
                output_path=root / "export.json",
            )

            self.assertEqual(export["schema_version"], "grpo_export_contract.v1")
            self.assertEqual(export["circuit_id"], "amp_dfcfc2")
            self.assertEqual(export["pcs_design_id"], "leung_dfcfc2_pin_3")
            self.assertEqual(
                export["action_parameter_names"],
                ["W_M0", "L_M0", "M_M0", "W_M12", "L_M12", "M_M12"],
            )
            self.assertEqual(export["candidate_count"], 1)
            candidate = export["candidates"][0]
            self.assertEqual(candidate["candidate_id"], "grpo_amp_dfcfc2_20260821-010203_tt_0001")
            self.assertEqual(candidate["action_real"], [1.0, 1.0, 4, 2.0, 2.5, 227])
            self.assertEqual(candidate["sizing"]["M_M12"], 227)
            self.assertEqual(candidate["sizing"]["W_M0"], 1.0)
            self.assertEqual(candidate["pre_layout_metrics"]["dcgain"], 101.0)
            self.assertTrue((root / "export.json").exists())

    def test_rejects_candidate_without_actions(self):
        from tools.analog_harness.ml.grpo_export_contract import validate_grpo_export

        bad_export = {
            "schema_version": "grpo_export_contract.v1",
            "source_repo": "repo",
            "source_commit": "unknown",
            "circuit_id": "amp_dfcfc2",
            "pcs_design_id": "leung_dfcfc2_pin_3",
            "action_space_contract_id": "contract",
            "action_parameter_names": ["W_M0"],
            "run_id": "run",
            "mode": "tt-only",
            "steps": 1,
            "candidate_count": 1,
            "candidates": [{"candidate_id": "missing_actions"}],
        }

        with self.assertRaises(ValueError) as ctx:
            validate_grpo_export(bad_export)
        self.assertIn("action_normalized", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
