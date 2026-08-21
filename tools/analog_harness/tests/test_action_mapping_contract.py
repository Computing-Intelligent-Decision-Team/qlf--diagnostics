import json
import tempfile
import unittest
from pathlib import Path

import yaml


class TestActionMappingContract(unittest.TestCase):
    def test_maps_export_candidates_with_yaml_contract(self):
        from tools.analog_harness.ml.action_mapping_contract import map_grpo_export_to_pcs_jsonl

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            export_path = root / "export.json"
            mapping_path = root / "mapping.yaml"
            output_path = root / "pcs_manifest_input.jsonl"

            export_path.write_text(
                json.dumps(
                    {
                        "schema_version": "grpo_export_contract.v1",
                        "source_repo": "repo",
                        "source_commit": "commit",
                        "circuit_id": "amp_dfcfc2",
                        "pcs_design_id": "leung_dfcfc2_pin_3",
                        "action_space_contract_id": "contract",
                        "action_parameter_names": ["W_M0", "L_M0", "M_M0", "I_Ib"],
                        "run_id": "run",
                        "mode": "tt-only",
                        "steps": 1,
                        "candidate_count": 1,
                        "candidates": [
                            {
                                "candidate_id": "cand_1",
                                "provenance_kind": "fresh_local_grpo_smoke",
                                "action_normalized": [0.0, 0.0, 0.0, 0.0],
                                "action_real": [1.2, 0.8, 7, 2e-6],
                                "sizing": {"W_M0": 1.2, "L_M0": 0.8, "M_M0": 7, "I_Ib": 2e-6},
                                "reward": -0.1,
                                "pm_feasible": True,
                                "pm_violation": 0.0,
                                "evaluation_source": "tt",
                                "pre_layout_metrics": {"dcgain": 100.0},
                            }
                        ],
                    }
                )
            )
            mapping_path.write_text(
                yaml.safe_dump(
                    {
                        "schema_version": "analog_harness.action_mapping_contract.v1",
                        "contract_id": "amp_dfcfc2_to_leung_dfcfc2_pin_3.v1",
                        "source_circuit_id": "amp_dfcfc2",
                        "target_pcs_design_id": "leung_dfcfc2_pin_3",
                        "variables": {
                            "W_M0": {"pcs_name": "mosfet_0_8_w_biascm_pmos", "unit": "u"},
                            "L_M0": {"pcs_name": "mosfet_0_8_l_biascm_pmos", "unit": "u"},
                            "M_M0": {"pcs_name": "mosfet_0_8_m_biascm_pmos", "unit": "count", "integer": True},
                            "I_Ib": {
                                "pcs_name": "current_0_bias",
                                "unit": "u",
                                "scale": 1000000.0,
                            },
                        },
                    },
                    sort_keys=False,
                )
            )

            summary = map_grpo_export_to_pcs_jsonl(
                export_path=export_path,
                mapping_path=mapping_path,
                output_path=output_path,
            )

            self.assertEqual(summary["mapped_candidates"], 1)
            record = json.loads(output_path.read_text().strip())
            self.assertEqual(record["candidate_id"], "cand_1")
            self.assertEqual(record["action_names"], ["W_M0", "L_M0", "M_M0", "I_Ib"])
            self.assertEqual(record["action_real"], [1.2, 0.8, 7, 2e-06])
            self.assertEqual(record["sizing"]["values"]["mosfet_0_8_m_biascm_pmos"], 7)
            self.assertEqual(record["sizing"]["values"]["current_0_bias"], 2.0)
            self.assertEqual(record["sizing"]["units"]["current_0_bias"], "u")
            self.assertEqual(record["performance"]["dcgain"], 100.0)

    def test_rejects_missing_mapping_variable(self):
        from tools.analog_harness.ml.action_mapping_contract import map_grpo_export_to_pcs_jsonl

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            export_path = root / "export.json"
            mapping_path = root / "mapping.yaml"
            export_path.write_text(
                json.dumps(
                    {
                        "schema_version": "grpo_export_contract.v1",
                        "source_repo": "repo",
                        "source_commit": "commit",
                        "circuit_id": "amp_dfcfc2",
                        "pcs_design_id": "leung_dfcfc2_pin_3",
                        "action_space_contract_id": "contract",
                        "action_parameter_names": ["W_M0", "L_M0"],
                        "run_id": "run",
                        "mode": "tt-only",
                        "steps": 1,
                        "candidate_count": 1,
                        "candidates": [
                            {
                                "candidate_id": "cand_1",
                                "provenance_kind": "fresh_local_grpo_smoke",
                                "action_normalized": [0.0, 0.0],
                                "action_real": [1.2, 0.8],
                                "sizing": {"W_M0": 1.2, "L_M0": 0.8},
                                "reward": -0.1,
                                "pre_layout_metrics": {},
                            }
                        ],
                    }
                )
            )
            mapping_path.write_text(
                yaml.safe_dump(
                    {
                        "schema_version": "analog_harness.action_mapping_contract.v1",
                        "contract_id": "incomplete",
                        "source_circuit_id": "amp_dfcfc2",
                        "target_pcs_design_id": "leung_dfcfc2_pin_3",
                        "variables": {"W_M0": {"pcs_name": "w0", "unit": "u"}},
                    }
                )
            )

            with self.assertRaises(ValueError) as ctx:
                map_grpo_export_to_pcs_jsonl(
                    export_path=export_path,
                    mapping_path=mapping_path,
                    output_path=root / "out.jsonl",
                )
            self.assertIn("L_M0", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
