#!/usr/bin/env python3
"""AnalogGym-Opt batch importer for parasitic modeling dataset.

Reads a batch directory exported by AnalogGym-Opt per the contract in
docs/analoggym_opt_data_request.md, and produces candidate stubs that
can be ingested into the parasitic modeling dataset after AnalogHarness
DRC/LVS/PEX processing.

This importer does NOT assign trust labels. Trust labels are assigned
by AnalogHarness diagnostics after layout generation and extraction.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


@dataclass
class AnalogGymCandidateStub:
    """Pre-trust candidate from AnalogGym-Opt. No trust labels yet."""

    candidate_id: str
    circuit: str
    batch_id: str
    source_spice_path: str
    pre_sim_metrics: dict[str, float] = None
    sizing: dict[str, dict[str, float]] = None
    optimizer_metadata: dict[str, Any] = None
    trust_assigned: bool = False
    trust_source: str = "pending_analog_harness"

    def __post_init__(self):
        if self.pre_sim_metrics is None:
            self.pre_sim_metrics = {}
        if self.sizing is None:
            self.sizing = {}
        if self.optimizer_metadata is None:
            self.optimizer_metadata = {}

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_candidate_dir(candidate_dir: Path) -> list[str]:
    """Check a candidate directory has required files. Returns list of issues."""
    issues = []
    required = ["candidate.json", "sizing.json", "source.spice",
                "pre_sim_metrics.json"]
    for f in required:
        if not (candidate_dir / f).exists():
            issues.append(f"missing {f}")
    return issues


def read_batch_manifest(manifest_path: Path) -> dict[str, Any]:
    """Read a batch_manifest.json."""
    if not manifest_path.exists():
        return {}
    with open(manifest_path) as f:
        return json.load(f)


def import_candidate(candidate_dir: Path, batch_id: str) -> AnalogGymCandidateStub | None:
    """Import one candidate directory into a stub.

    Returns None if the directory is missing critical files.
    """
    candidate_dir = Path(candidate_dir)
    if not candidate_dir.is_dir():
        return None

    candidate_json = candidate_dir / "candidate.json"
    sizing_json = candidate_dir / "sizing.json"
    source_spice = candidate_dir / "source.spice"
    pre_sim_json = candidate_dir / "pre_sim_metrics.json"
    opt_meta_json = candidate_dir / "optimizer_metadata.json"

    if not candidate_json.exists():
        return None

    with open(candidate_json) as f:
        cand = json.load(f)

    sizing = {}
    if sizing_json.exists():
        with open(sizing_json) as f:
            sizing = json.load(f)

    pre_sim = {}
    if pre_sim_json.exists():
        with open(pre_sim_json) as f:
            pre_sim = json.load(f)

    opt_meta = {}
    if opt_meta_json.exists():
        with open(opt_meta_json) as f:
            opt_meta = json.load(f)

    return AnalogGymCandidateStub(
        candidate_id=cand.get("candidate_id", candidate_dir.name),
        circuit=cand.get("circuit", "unknown"),
        batch_id=batch_id,
        source_spice_path=str(source_spice.resolve()) if source_spice.exists() else "",
        pre_sim_metrics=pre_sim,
        sizing=sizing,
        optimizer_metadata=opt_meta,
    )


def import_batch(batch_root: Path) -> tuple[list[AnalogGymCandidateStub], dict[str, Any]]:
    """Import a full AnalogGym-Opt batch.

    Returns (stubs, manifest).
    """
    batch_root = Path(batch_root)
    manifest = read_batch_manifest(batch_root / "batch_manifest.json")
    batch_id = manifest.get("batch_id", batch_root.name)

    stubs: list[AnalogGymCandidateStub] = []
    issues: dict[str, list[str]] = {}

    for child in sorted(batch_root.iterdir()):
        if not child.is_dir():
            continue
        if child.name in ("logs", "batch_manifest.json"):
            continue
        # Look for circuit_<name> directories
        if child.name.startswith("circuit_"):
            for cand_dir in sorted(child.iterdir()):
                if not cand_dir.is_dir():
                    continue
                if cand_dir.name.startswith("cand_"):
                    stub = import_candidate(cand_dir, batch_id)
                    if stub:
                        stubs.append(stub)
                    else:
                        issues[str(cand_dir)] = ["import failed"]
        # Direct candidate directories
        elif child.name.startswith("cand_"):
            stub = import_candidate(child, batch_id)
            if stub:
                stubs.append(stub)
            else:
                issues[str(child)] = ["import failed"]

    return stubs, {"manifest": manifest, "issues": issues, "batch_id": batch_id}


def export_stubs_jsonl(stubs: list[AnalogGymCandidateStub], output_path: Path) -> None:
    """Write candidate stubs as JSONL (no trust labels)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        for s in stubs:
            f.write(json.dumps(s.to_dict()) + "\n")


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="AnalogGym-Opt batch importer for parasitic modeling"
    )
    parser.add_argument("--batch-root", type=Path, required=True,
                        help="Root of AnalogGym-Opt batch export")
    parser.add_argument("--output", type=Path, default=None,
                        help="Output JSONL path for candidate stubs")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()

    stubs, info = import_batch(args.batch_root)
    issues = info.get("issues", {})

    if args.summary:
        print(f"Batch: {info['batch_id']}")
        print(f"Candidates imported: {len(stubs)}")
        if issues:
            print(f"Issues: {len(issues)}")
        for s in stubs:
            print(f"  {s.candidate_id}: {s.circuit} | pre_sim metrics: {len(s.pre_sim_metrics)}")

    if args.output:
        export_stubs_jsonl(stubs, args.output)
        print(f"Stubs written to {args.output}")


if __name__ == "__main__":
    main()
