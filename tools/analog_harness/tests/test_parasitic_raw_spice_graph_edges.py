from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from tools.analog_harness.parasitic_raw_spice_graph_edges import (
    augment_dataset_with_raw_spice_edges,
    parse_raw_spice_capacitor_edges,
    read_raw_spice_manifest,
)


class ParasiticRawSpiceGraphEdgesTest(unittest.TestCase):
    def test_parses_raw_spice_capacitor_edges_with_units_and_power_flags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw_path = Path(tmp) / "toy.raw.spice"
            raw_path.write_text(
                "\n".join(
                    [
                        "* header",
                        ".subckt toy",
                        "X0 out in vdda vdda pfet",
                        "C0 out gnda 1.5f",
                        "C1 out net1 2p",
                        "C2 net1 gnda 0",
                        "+ continuation ignored",
                        ".ends",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = parse_raw_spice_capacitor_edges(
                raw_path,
                design_id="toy_amp",
                candidate_id="cand_0001",
            )

            self.assertEqual(result["summary"]["edge_count_all"], 3)
            self.assertEqual(result["summary"]["edge_count_positive"], 2)
            self.assertEqual(result["summary"]["edge_count_zero"], 1)
            self.assertAlmostEqual(result["summary"]["total_cap_ff"], 2001.5)
            self.assertEqual(result["summary"]["node_count"], 3)
            self.assertEqual(result["edges"][0]["node_1"], "out")
            self.assertEqual(result["edges"][0]["node_2"], "gnda")
            self.assertTrue(result["edges"][0]["is_power_edge"])
            self.assertAlmostEqual(result["edges"][1]["capacitance_ff"], 2000.0)
            self.assertTrue(result["edges"][2]["is_zero"])
            self.assertTrue(result["summary"]["raw_spice_sha256"])

    def test_reads_manifest_and_augments_summary_only_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            raw_path = tmp_path / "toy.raw.spice"
            raw_path.write_text("C0 out gnda 1f\nC1 out net1 2f\n", encoding="utf-8")
            manifest_path = tmp_path / "manifest.csv"
            with manifest_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["design_id", "candidate_id", "raw_spice_path"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "design_id": "toy_amp",
                        "candidate_id": "cand_0001",
                        "raw_spice_path": str(raw_path),
                    }
                )

            entries = read_raw_spice_manifest(manifest_path)
            dataset = {
                "counts": {"records": 1, "records_with_graph": 0, "summary_only_records": 1},
                "records": [
                    {
                        "design_id": "toy_amp",
                        "candidate_id": "cand_0001",
                        "graph": {"available": False},
                        "modeling_availability": {"pex_summary": "usable"},
                    }
                ],
                "graph_edges_by_design": {},
            }

            augmented = augment_dataset_with_raw_spice_edges(dataset, entries)

            self.assertEqual(augmented["counts"]["records_with_graph"], 1)
            self.assertEqual(augmented["counts"]["summary_only_records"], 0)
            self.assertEqual(augmented["counts"]["raw_spice_graph_records"], 1)
            self.assertIn("toy_amp", augmented["graph_edges_by_design"])
            self.assertEqual(len(augmented["graph_edges_by_design"]["toy_amp"]), 2)
            record = augmented["records"][0]
            self.assertTrue(record["graph"]["available"])
            self.assertEqual(record["graph"]["source_type"], "raw_spice_direct_capacitor_table")
            self.assertFalse(record["graph"]["needs_raw_spice_verification"])
            self.assertEqual(
                record["modeling_availability"]["capacitor_graph"],
                "usable_with_raw_spice_provenance",
            )


if __name__ == "__main__":
    unittest.main()
