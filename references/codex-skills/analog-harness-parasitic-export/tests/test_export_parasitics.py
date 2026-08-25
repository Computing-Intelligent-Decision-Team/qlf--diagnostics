import importlib.util
import json
import tarfile
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "export_parasitics.py"
SPEC = importlib.util.spec_from_file_location("export_parasitics", SCRIPT)
export_parasitics = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(export_parasitics)


class ExportParasiticsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "generated" / "analog_harness"
        self.root.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def make_candidate(
        self,
        name="run_001",
        *,
        drc_count=0,
        lvs_match="yes",
        with_lineage=True,
        with_pex=True,
        pex_text="C1 out 0 2.5f\nR1 out n1 12.0\n",
        performance_status="fail",
        timestamp="2026-08-24T08:00:00Z",
    ):
        candidate = self.root / "batch" / "runs" / name / "cand_0001"
        (candidate / "case").mkdir(parents=True)
        (candidate / "layout").mkdir()
        source = candidate / "case" / "design.sp"
        source.write_text("M1 out in 0 0 nfet W=1u L=0.15u\n", encoding="utf-8")
        raw_pex = candidate / "layout" / "design_extracted.raw.spice"
        if with_pex:
            raw_pex.write_text(pex_text, encoding="utf-8")

        state = {
            "candidate_id": "cand_0001",
            "design_id": "design",
            "closure_level": "L6_post_layout_pvt",
            "action_normalized": [0.1, -0.2] if with_lineage else [],
            "artifacts": {"netlist": str(source)} if with_lineage else {},
            "evidence": [
                {
                    "stage": "layout_verification",
                    "status": "pass" if drc_count == 0 and lvs_match == "yes" else "fail",
                    "timestamp": timestamp,
                    "verification_scope": "mos_only_projection",
                    "artifacts": {"raw_extracted_netlist": str(raw_pex)},
                    "metrics": {
                        "drc_count": drc_count,
                        "lvs_match": lvs_match,
                        "pex_caps": 1,
                    },
                },
                {
                    "stage": "pvt_sim",
                    "status": performance_status,
                    "timestamp": timestamp,
                    "metrics": {"phase_margin": -20.0, "reward": -1.0},
                },
            ],
        }
        (candidate / "state.json").write_text(json.dumps(state), encoding="utf-8")
        return candidate

    def evaluate(self, candidate):
        return export_parasitics.evaluate_candidate(
            candidate,
            since=datetime(2026, 8, 18, tzinfo=timezone.utc),
            until=datetime(2026, 8, 25, tzinfo=timezone.utc),
        )

    def test_performance_failure_does_not_reject_trusted_parasitics(self):
        result = self.evaluate(self.make_candidate(performance_status="fail"))
        self.assertTrue(result.trusted)
        self.assertEqual(result.reasons, [])
        self.assertEqual(result.parasitic_cap_count, 1)
        self.assertEqual(result.parasitic_res_count, 1)

    def test_drc_failure_is_rejected(self):
        result = self.evaluate(self.make_candidate(drc_count=3))
        self.assertFalse(result.trusted)
        self.assertIn("drc_not_pass", result.reasons)

    def test_lvs_failure_is_rejected(self):
        result = self.evaluate(self.make_candidate(lvs_match="no"))
        self.assertFalse(result.trusted)
        self.assertIn("connectivity_lvs_not_pass", result.reasons)

    def test_missing_sizing_lineage_is_rejected(self):
        result = self.evaluate(self.make_candidate(with_lineage=False))
        self.assertFalse(result.trusted)
        self.assertIn("sizing_lineage_unproven", result.reasons)

    def test_missing_or_unparseable_raw_pex_is_rejected(self):
        missing = self.evaluate(self.make_candidate("missing", with_pex=False))
        invalid = self.evaluate(self.make_candidate("invalid", pex_text="* empty PEX\n"))
        self.assertIn("raw_pex_missing_or_unparseable", missing.reasons)
        self.assertIn("raw_pex_missing_or_unparseable", invalid.reasons)

    def test_outside_time_window_is_not_selected(self):
        result = self.evaluate(
            self.make_candidate(timestamp="2026-08-10T08:00:00Z")
        )
        self.assertFalse(result.in_window)
        self.assertFalse(result.trusted)
        self.assertIn("outside_time_window", result.reasons)

    def test_export_writes_manifests_checksums_and_archive(self):
        trusted = self.make_candidate("trusted")
        self.make_candidate("bad_lvs", lvs_match="no")
        output = Path(self.tmp.name) / "export"

        summary = export_parasitics.export_dataset(
            roots=[self.root],
            output_dir=output,
            since=datetime(2026, 8, 18, tzinfo=timezone.utc),
            until=datetime(2026, 8, 25, tzinfo=timezone.utc),
            create_archive=True,
        )

        self.assertEqual(summary["trusted_count"], 1)
        self.assertEqual(summary["rejected_count"], 1)
        self.assertTrue((output / "MANIFEST.json").is_file())
        self.assertTrue((output / "candidates.csv").is_file())
        self.assertTrue((output / "rejected_candidates.csv").is_file())
        self.assertTrue((output / "duplicate_groups.json").is_file())
        self.assertTrue((output / "README.md").is_file())
        self.assertTrue((output / "SHA256SUMS").is_file())
        copied = list((output / "trusted_candidates").rglob("state.json"))
        self.assertEqual(len(copied), 1)
        self.assertNotEqual(copied[0].resolve(), (trusted / "state.json").resolve())
        archive = Path(summary["archive_path"])
        self.assertTrue(archive.is_file())
        with tarfile.open(archive, "r:gz") as bundle:
            names = bundle.getnames()
        self.assertTrue(any(name.endswith("MANIFEST.json") for name in names))


if __name__ == "__main__":
    unittest.main()
