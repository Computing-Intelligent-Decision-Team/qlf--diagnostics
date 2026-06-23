#!/usr/bin/env python3
"""AnalogGym-Opt smoke test: mock batch → import → validate stubs.

Does NOT run AnalogGym-Opt or any model training.
Validates only the importer contract defined in
docs/analoggym_opt_data_request.md.
"""

import json
import tempfile
from pathlib import Path

from analoggym_importer import (
    AnalogGymCandidateStub,
    import_candidate,
    import_batch,
    validate_candidate_dir,
)


def create_mock_batch(root: Path, num_candidates: int = 3) -> Path:
    """Create a minimal mock AnalogGym-Opt batch for smoke testing."""
    circuit_dir = root / "circuit_SMCNR_SE_2st_AMP"
    for i in range(1, num_candidates + 1):
        cand_dir = circuit_dir / f"cand_{i:04d}"
        cand_dir.mkdir(parents=True)

        candidate = {
            "candidate_id": f"cand_{i:04d}",
            "circuit": "SMCNR_SE_2st_AMP",
        }
        (cand_dir / "candidate.json").write_text(json.dumps(candidate))

        sizing = {"xm1": {"w": 1.5, "l": 10.0}, "xm4": {"w": 1.48, "l": 10.0}}
        (cand_dir / "sizing.json").write_text(json.dumps(sizing))

        (cand_dir / "source.spice").write_text(
            ".subckt SMCNR_SE_2st_AMP vdda gnda vin vip ibias vout\n"
            ".ends\n"
        )

        pre_sim = {"GBW": 18.3e6, "dcgain": 24.7, "Power": 5.6e-8}
        (cand_dir / "pre_sim_metrics.json").write_text(json.dumps(pre_sim))

    manifest = {
        "batch_id": f"smoke_test_{root.name}",
        "circuit": "SMCNR_SE_2st_AMP",
        "candidate_count": num_candidates,
    }
    (root / "batch_manifest.json").write_text(json.dumps(manifest))
    return root


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        batch_root = create_mock_batch(root, num_candidates=3)

        print("=== Validate candidate dirs ===")
        circuit_dir = batch_root / "circuit_SMCNR_SE_2st_AMP"
        for cand_dir in sorted(circuit_dir.iterdir()):
            if not cand_dir.is_dir():
                continue
            issues = validate_candidate_dir(cand_dir)
            status = "OK" if not issues else f"Issues: {issues}"
            print(f"  {cand_dir.name}: {status}")

        print("\n=== Import batch ===")
        stubs, info = import_batch(batch_root)
        print(f"  Batch: {info['batch_id']}")
        print(f"  Candidates: {len(stubs)}")
        assert len(stubs) == 3, f"Expected 3 candidates, got {len(stubs)}"

        for stub in stubs:
            print(f"  {stub.candidate_id}: circuit={stub.circuit}, "
                  f"pre_sim_metrics={len(stub.pre_sim_metrics)} keys, "
                  f"trust_assigned={stub.trust_assigned}")

        print("\n=== Export stubs ===")
        out = root / "smoke_test_stubs.jsonl"
        from analoggym_importer import export_stubs_jsonl
        export_stubs_jsonl(stubs, out)
        with open(out) as f:
            lines = f.readlines()
        print(f"  Wrote {len(lines)} lines to {out}")
        for line in lines:
            obj = json.loads(line)
            assert "candidate_id" in obj
            assert obj["trust_assigned"] is False
            print(f"  {obj['candidate_id']}: trust_assigned={obj['trust_assigned']}")

        print("\n=== All smoke tests passed ===")


if __name__ == "__main__":
    main()
