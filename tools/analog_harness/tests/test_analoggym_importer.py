#!/usr/bin/env python3
"""Tests for AnalogGym-Opt candidate stub importer."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.analog_harness.ml.analoggym_importer import (
    AnalogGymCandidateStub,
    export_stubs_jsonl,
    import_batch,
    validate_candidate_dir,
)


def write_candidate(root: Path, name: str = "cand_0001") -> Path:
    cand_dir = root / "circuit_SMCNR_SE_2st_AMP" / name
    cand_dir.mkdir(parents=True)
    (cand_dir / "candidate.json").write_text(json.dumps({
        "candidate_id": name,
        "circuit": "SMCNR_SE_2st_AMP",
    }))
    (cand_dir / "sizing.json").write_text(json.dumps({
        "xm1": {"w": 1.5, "l": 10.0},
    }))
    (cand_dir / "source.spice").write_text(
        ".subckt SMCNR_SE_2st_AMP vdda gnda vin vip ibias vout\n.ends\n"
    )
    (cand_dir / "pre_sim_metrics.json").write_text(json.dumps({
        "GBW": 18.3e6,
        "dcgain": 24.7,
    }))
    return cand_dir


class TestAnalogGymCandidateStub(unittest.TestCase):
    def test_candidate_stub_defaults_to_pending_trust(self):
        stub = AnalogGymCandidateStub(
            candidate_id="cand_0001",
            circuit="SMCNR_SE_2st_AMP",
            batch_id="batch_0",
            source_spice_path="source.spice",
        )

        self.assertFalse(stub.trust_assigned)
        self.assertEqual(stub.trust_source, "pending_analog_harness")
        self.assertEqual(stub.pre_sim_metrics, {})
        self.assertEqual(stub.sizing, {})
        self.assertEqual(stub.optimizer_metadata, {})


class TestImportBatch(unittest.TestCase):
    def test_import_batch_keeps_all_candidates_pre_trust(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "batch_manifest.json").write_text(json.dumps({
                "batch_id": "smoke_batch",
                "candidate_count": 3,
            }))
            for i in range(1, 4):
                write_candidate(root, f"cand_{i:04d}")

            stubs, info = import_batch(root)

        self.assertEqual(info["batch_id"], "smoke_batch")
        self.assertEqual(len(stubs), 3)
        self.assertTrue(all(s.circuit == "SMCNR_SE_2st_AMP" for s in stubs))
        self.assertTrue(all(s.trust_assigned is False for s in stubs))
        self.assertTrue(all(s.trust_source == "pending_analog_harness" for s in stubs))

    def test_validate_candidate_dir_reports_missing_required_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            cand_dir = Path(tmp) / "cand_0001"
            cand_dir.mkdir()
            (cand_dir / "candidate.json").write_text("{}")

            issues = validate_candidate_dir(cand_dir)

        self.assertIn("missing sizing.json", issues)
        self.assertIn("missing source.spice", issues)
        self.assertIn("missing pre_sim_metrics.json", issues)

    def test_export_stubs_jsonl_preserves_pending_trust_flag(self):
        stub = AnalogGymCandidateStub(
            candidate_id="cand_0001",
            circuit="SMCNR_SE_2st_AMP",
            batch_id="batch_0",
            source_spice_path="source.spice",
        )
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "stubs.jsonl"
            export_stubs_jsonl([stub], out)
            line = out.read_text().strip()

        obj = json.loads(line)
        self.assertEqual(obj["candidate_id"], "cand_0001")
        self.assertFalse(obj["trust_assigned"])
        self.assertEqual(obj["trust_source"], "pending_analog_harness")


if __name__ == "__main__":
    unittest.main()
