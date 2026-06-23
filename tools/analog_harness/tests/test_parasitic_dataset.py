#!/usr/bin/env python3
"""Tests for parasitic_dataset.py v0.

Run: python3 -m pytest tools/analog_harness/tests/test_parasitic_dataset.py -v
  or: python3 tools/analog_harness/tests/test_parasitic_dataset.py
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.analog_harness.ml.parasitic_dataset import (
    ParasiticEdge,
    ParasiticSample,
    SAMPLE_REGISTRY,
    build_dataset,
    build_sample,
    parse_extracted_spice,
    extract_basic_graph_features,
)


class TestParasiticEdge(unittest.TestCase):
    def test_edge_creation(self):
        e = ParasiticEdge(src="vout", dst="gnda", cap_ff=35.87)
        self.assertEqual(e.src, "vout")
        self.assertEqual(e.dst, "gnda")
        self.assertAlmostEqual(e.cap_ff, 35.87)

    def test_edge_dict(self):
        e = ParasiticEdge(src="vout", dst="gnda", cap_ff=1.5)
        d = e.__dict__ if hasattr(e, '__dict__') else {"src": e.src, "dst": e.dst, "cap_ff": e.cap_ff}
        self.assertEqual(d["src"], "vout")


class TestParasiticSample(unittest.TestCase):
    def test_sample_defaults(self):
        s = ParasiticSample(
            sample_id="test",
            circuit="TEST",
            candidate_id="cand_0",
            lvs_status="PASS",
            trust_scope="verified",
            usable_for_supervised_positive_training=True,
            pex_caps=0,
            pex_total_cap_ff=0.0,
        )
        self.assertEqual(s.sample_id, "test")
        self.assertEqual(s.pex_caps, 0)
        self.assertTrue(s.usable_for_supervised_positive_training)

    def test_sample_to_dict(self):
        s = ParasiticSample(
            sample_id="test", circuit="T", candidate_id="c0",
            lvs_status="PASS", trust_scope="v",
            usable_for_supervised_positive_training=True,
            pex_caps=2, pex_total_cap_ff=3.0,
            parasitic_edges=[ParasiticEdge("a", "b", 1.0), ParasiticEdge("c", "d", 2.0)],
            per_node_cap_ff={"a": 1.0, "b": 1.0, "c": 2.0, "d": 2.0},
        )
        d = s.to_dict()
        self.assertEqual(d["sample_id"], "test")
        self.assertEqual(len(d["parasitic_edges"]), 2)


class TestParseExtractedSpice(unittest.TestCase):
    def test_parse_cap_line(self):
        # Create a minimal SPICE with caps
        spice_content = """* test
C0 vout gnda 35.8705f
C1 ibias vdda 6.97853f
C2 a_2100_n30# gnda 6.57175f
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.spice', delete=False) as f:
            f.write(spice_content)
            tmp = f.name

        try:
            edges, per_node, total = parse_extracted_spice(tmp)
            self.assertEqual(len(edges), 3)
            self.assertAlmostEqual(total, 35.8705 + 6.97853 + 6.57175, places=2)
            self.assertIn("vout", per_node)
            self.assertIn("gnda", per_node)
        finally:
            Path(tmp).unlink()

    def test_empty_file(self):
        edges, per_node, total = parse_extracted_spice("/nonexistent/path.spice")
        self.assertEqual(len(edges), 0)
        self.assertEqual(total, 0.0)

    def test_parse_pico_suffix_and_floating_comment_as_ff(self):
        spice_content = """* test
C11 a_830_5820# vout 0.33238p
C86 m5_6884_60# vdda 3.17475f $ **FLOATING
C13 vinn a_905_1720# 4.05e-21
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.spice', delete=False) as f:
            f.write(spice_content)
            tmp = f.name

        try:
            edges, per_node, total = parse_extracted_spice(tmp)
            self.assertEqual(len(edges), 3)
            self.assertAlmostEqual(edges[0].cap_ff, 332.38)
            self.assertAlmostEqual(edges[1].cap_ff, 3.17475)
            self.assertAlmostEqual(total, 332.38 + 3.17475 + 4.05e-6, places=5)
            self.assertAlmostEqual(per_node["vout"], 332.38)
        finally:
            Path(tmp).unlink()


class TestExtractFeatures(unittest.TestCase):
    def test_features_from_spice(self):
        spice = """* test
.subckt test vout gnda
X0 vout gnda gnda gnda sky130_fd_pr__nfet_01v8 w=1 l=1
X1 vout gnda vdda vdda sky130_fd_pr__pfet_01v8 w=1 l=1
.ends
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.spice', delete=False) as f:
            f.write(spice)
            tmp = f.name
        try:
            feats = extract_basic_graph_features(tmp)
            self.assertEqual(feats["nmos_count"], 1)
            self.assertEqual(feats["pmos_count"], 1)
            self.assertEqual(feats["mos_count"], 2)
        finally:
            Path(tmp).unlink()


class TestSampleRegistry(unittest.TestCase):
    def test_registry_has_required_fields(self):
        required = ["sample_id", "circuit", "candidate_id", "lvs_status",
                    "trust_scope", "usable_for_supervised_positive_training"]
        for entry in SAMPLE_REGISTRY:
            for field in required:
                self.assertIn(field, entry, f"Missing {field} in {entry['sample_id']}")

    def test_smcnr_is_only_positive(self):
        for entry in SAMPLE_REGISTRY:
            if entry["usable_for_supervised_positive_training"]:
                self.assertIn("smcnr", entry["sample_id"].lower(),
                              f"Only SMCNR should be training-positive, got {entry['sample_id']}")
                self.assertEqual(entry["lvs_status"], "PASS")

    def test_fan_smc_and_dfcfc2_are_failure_only(self):
        for entry in SAMPLE_REGISTRY:
            if "fan_smc" in entry["sample_id"].lower() or "dfcfc2" in entry["sample_id"].lower():
                self.assertFalse(entry["usable_for_supervised_positive_training"],
                                 f"{entry['sample_id']} must not be training-positive")
                self.assertEqual(entry["lvs_status"], "FAIL")

    def test_all_spice_paths_exist(self):
        for entry in SAMPLE_REGISTRY:
            if "raw_spice_path" in entry:
                path = Path(entry["raw_spice_path"])
                self.assertTrue(path.exists(),
                                f"SPICE path missing for {entry['sample_id']}: {path}")


class TestBuildDataset(unittest.TestCase):
    def test_build_all_samples(self):
        samples = build_dataset()
        self.assertEqual(len(samples), len(SAMPLE_REGISTRY))
        for s in samples:
            self.assertIsInstance(s, ParasiticSample)
            self.assertIsInstance(s.sample_id, str)

    def test_smcnr_has_parasitic_data(self):
        samples = build_dataset()
        smcnr = [s for s in samples if "smcnr" in s.sample_id]
        self.assertEqual(len(smcnr), 1)
        self.assertGreater(smcnr[0].pex_caps, 0, "SMCNR should have parasitic caps")
        self.assertGreater(smcnr[0].pex_total_cap_ff, 0.0)
        self.assertTrue(smcnr[0].usable_for_supervised_positive_training)

    def test_fan_smc_not_training_safe(self):
        samples = build_dataset()
        for s in samples:
            if "fan_smc" in s.sample_id:
                self.assertFalse(s.usable_for_supervised_positive_training)

    def test_write_jsonl(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            tmp = f.name
        try:
            build_dataset(tmp)
            with open(tmp) as f:
                lines = f.readlines()
            self.assertEqual(len(lines), len(SAMPLE_REGISTRY))
            for line in lines:
                obj = json.loads(line)
                self.assertIn("sample_id", obj)
                self.assertIn("lvs_status", obj)
                self.assertIn("usable_for_parasitic_modeling", obj)
                self.assertIn("usable_only_as_failure_case", obj)
                self.assertIn("provenance_note", obj)
                self.assertIn("pex_caps", obj)
                self.assertIn("parasitic_edges", obj)
        finally:
            Path(tmp).unlink()

    def test_dfcfc2_mim_proxy_matches_pex_summary(self):
        samples = build_dataset()
        dfcfc2 = [s for s in samples if s.sample_id == "dfcfc2_mim_proxy"][0]
        self.assertEqual(dfcfc2.pex_caps, 103)
        self.assertAlmostEqual(dfcfc2.pex_total_cap_ff, 865.01, places=2)
        self.assertFalse(dfcfc2.usable_for_supervised_positive_training)


class TestSchemaValidator(unittest.TestCase):
    REQUIRED = [
        "sample_id", "circuit", "candidate_id", "lvs_status", "trust_scope",
        "usable_for_supervised_positive_training", "usable_for_parasitic_modeling",
        "usable_only_as_failure_case", "pex_caps", "pex_total_cap_ff",
        "parasitic_edges", "per_node_cap_ff", "graph_features",
        "source_artifacts", "provenance_note",
    ]

    @staticmethod
    def _jsonl_path():
        return Path(__file__).resolve().parents[3] / "generated" / "parasitic_modeling" / "dataset_v0.jsonl"

    def test_generated_jsonl_has_all_required_fields(self):
        jsonl = self._jsonl_path()
        self.assertTrue(jsonl.exists(), f"Dataset not found at {jsonl}")
        with open(jsonl) as f:
            for i, line in enumerate(f, 1):
                obj = json.loads(line)
                for field in self.REQUIRED:
                    self.assertIn(field, obj,
                                  f"Line {i} ({obj.get('sample_id','?')}): missing required field '{field}'")

    def test_smcnr_is_only_positive_in_generated_jsonl(self):
        jsonl = self._jsonl_path()
        with open(jsonl) as f:
            for line in f:
                obj = json.loads(line)
                if obj["usable_for_supervised_positive_training"]:
                    self.assertIn("smcnr", obj["sample_id"].lower(),
                                  f"Only SMCNR should be positive, got {obj['sample_id']}")
                    self.assertEqual(obj["lvs_status"], "PASS")

    def test_no_line_is_empty_or_unparseable(self):
        jsonl = self._jsonl_path()
        with open(jsonl) as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                self.assertTrue(line, f"Line {i} is empty")
                obj = json.loads(line)
                self.assertIsInstance(obj, dict, f"Line {i} is not a JSON object")


if __name__ == "__main__":
    unittest.main()
