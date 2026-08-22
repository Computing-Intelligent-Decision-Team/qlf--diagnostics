"""Validate multi-candidate sizing manifests and prepare PCS replay inputs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


MANIFEST_SCHEMA_VERSION = "analog_harness.sizing_candidate_manifest.v1"
SOURCE_STATE_SCHEMA_VERSION = "analog_harness.sizing_source_state.v1"
BATCH_SCHEMA_VERSION = "analog_harness.batch_replay_manifest.v1"
L0_CLOSURE_LEVEL = "L0_ingest_contract_checked"


class SizingManifestError(ValueError):
    """Raised when a sizing candidate manifest violates the replay contract."""


def load_and_validate_manifest(manifest_or_path: dict[str, Any] | Path, *, repo_root: Path | None = None) -> dict[str, Any]:
    """Load and validate a multi-candidate sizing manifest."""

    repo_root = (repo_root or Path(".")).resolve()
    manifest = _load_manifest(manifest_or_path)
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise SizingManifestError(f"schema_version must be {MANIFEST_SCHEMA_VERSION}")
    design_id = _required_str(manifest, "design_id")
    _required_str(manifest, "family_id")
    config_path = _resolve_path(_required_str(manifest, "config"), repo_root)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    allowed_variables = _sizing_variables(config)
    default_values = _default_sizing_values(allowed_variables)
    candidates = manifest.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise SizingManifestError("manifest must contain at least one candidate")

    seen_ids: set[str] = set()
    normalized_candidates = []
    for index, candidate in enumerate(candidates):
        normalized = _validate_candidate(
            candidate,
            index=index,
            design_id=design_id,
            allowed_variables=allowed_variables,
            default_values=default_values,
        )
        if normalized["candidate_id"] in seen_ids:
            raise SizingManifestError(f"duplicate candidate_id: {normalized['candidate_id']}")
        seen_ids.add(normalized["candidate_id"])
        normalized_candidates.append(normalized)

    expected_flow = _expected_flow(manifest.get("expected_flow", {}))
    return {
        **manifest,
        "config": str(config_path),
        "top_cell": manifest.get("top_cell") or config.get("top_cell") or design_id,
        "expected_flow": expected_flow,
        "candidates": normalized_candidates,
        "validation": {
            "status": "pass",
            "candidate_count": len(normalized_candidates),
            "sizing_variable_count": len(allowed_variables),
            "complete_sizing_count": len(default_values),
            "config_sha256": _sha256_file(config_path),
        },
    }


def prepare_sizing_candidate_replay(manifest_path: Path, *, output_dir: Path, repo_root: Path | None = None) -> dict[str, Any]:
    """Validate a manifest and write source states plus a batch replay manifest."""

    repo_root = (repo_root or Path(".")).resolve()
    manifest = load_and_validate_manifest(manifest_path, repo_root=repo_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    source_state_dir = output_dir / "source_states"
    source_state_dir.mkdir(parents=True, exist_ok=True)

    source_records = []
    for candidate in manifest["candidates"]:
        state = _source_state(manifest, candidate)
        state_path = source_state_dir / f"{candidate['candidate_id']}.source_state.json"
        state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        source_records.append(
            {
                "candidate_id": candidate["candidate_id"],
                "source_state": str(state_path),
                "source_state_sha256": _sha256_file(state_path),
            }
        )

    batch_manifest = _batch_replay_manifest(manifest, source_records)
    batch_path = output_dir / "batch_replay_manifest.json"
    batch_path.write_text(json.dumps(batch_manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

    manifest_copy_path = output_dir / "validated_sizing_manifest.json"
    manifest_copy_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    csv_path = output_dir / "candidate_replay_jobs.csv"
    _write_jobs_csv(batch_manifest["jobs"], csv_path)
    readme_path = output_dir / "README.md"
    readme_path.write_text(_render_readme(manifest, batch_manifest), encoding="utf-8")
    return {
        "status": "pass",
        "schema_version": "analog_harness.sizing_candidate_replay_preparation.v1",
        "counts": {
            "candidates": len(manifest["candidates"]),
            "source_states": len(source_records),
            "batch_jobs": len(batch_manifest["jobs"]),
        },
        "outputs": {
            "validated_manifest": str(manifest_copy_path),
            "source_state_dir": str(source_state_dir),
            "batch_replay_manifest": str(batch_path),
            "candidate_replay_jobs_csv": str(csv_path),
            "markdown": str(readme_path),
        },
    }


def _source_state(manifest: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    sizing = candidate["sizing"]
    provenance = dict(candidate.get("provenance", {}))
    validation = dict(manifest.get("validation", {}))
    ingest_metrics = {
        "closure_level": L0_CLOSURE_LEVEL,
        "source_type": candidate["source_type"],
        "family_id": manifest["family_id"],
        "source_candidate_id": candidate["candidate_id"],
        "parent_candidate_id": candidate.get("parent_candidate_id"),
        "target_design_id": manifest["design_id"],
        "top_cell": candidate.get("top_cell") or manifest.get("top_cell") or manifest["design_id"],
        "mapping_contract": provenance.get("mapping_contract"),
        "action_space_contract_id": candidate.get("action_space_contract_id") or manifest.get("action_space_contract_id"),
        "manifest_schema_version": manifest["schema_version"],
        "source_state_schema_version": SOURCE_STATE_SCHEMA_VERSION,
        "config_sha256": validation.get("config_sha256"),
        "provided_sizing_count": int(sizing.get("provided_sizing_count", len(sizing["values"]))),
        "complete_sizing_count": len(sizing["values"]),
        "action_name_count": len(sizing.get("action_names", [])),
    }
    return {
        "schema_version": SOURCE_STATE_SCHEMA_VERSION,
        "candidate_id": candidate["candidate_id"],
        "design_id": manifest["design_id"],
        "top_cell": candidate.get("top_cell") or manifest.get("top_cell") or manifest["design_id"],
        "closure_level": L0_CLOSURE_LEVEL,
        "values": dict(sizing["values"]),
        "action_normalized": candidate.get("action_normalized"),
        "optimizer_metadata": {
            "source_type": candidate["source_type"],
            "family_id": manifest["family_id"],
            "parent_candidate_id": candidate.get("parent_candidate_id"),
            "sizing_units": dict(sizing["units"]),
            "action_names": list(sizing.get("action_names", [])),
            "action_vector": list(sizing.get("action_vector", [])),
            "provided_sizing_count": int(sizing.get("provided_sizing_count", len(sizing["values"]))),
            "complete_sizing_count": len(sizing["values"]),
            "provenance": provenance,
            "action_space_contract_id": candidate.get("action_space_contract_id") or manifest.get("action_space_contract_id"),
            "manifest_schema_version": manifest["schema_version"],
        },
        "evidence": [
            {
                "stage": "ingest_contract_check",
                "status": "pass",
                "metrics": ingest_metrics,
            }
        ],
    }


def _batch_replay_manifest(manifest: dict[str, Any], source_records: list[dict[str, Any]]) -> dict[str, Any]:
    skip_sim = not bool(manifest["expected_flow"].get("run_post_sim", False))
    jobs = []
    for record in source_records:
        command = [
            "python3",
            "-m",
            "tools.analog_harness.cli",
            "promote-source-candidate",
            "--config",
            manifest["config"],
            "--source-state",
            record["source_state"],
            "--no-knowledge-archive",
        ]
        if skip_sim:
            command.append("--skip-sim")
        jobs.append(
            {
                "candidate_id": record["candidate_id"],
                "design_id": manifest["design_id"],
                "family_id": manifest["family_id"],
                "source_state": record["source_state"],
                "source_state_sha256": record["source_state_sha256"],
                "expected_flow": dict(manifest["expected_flow"]),
                "command": command,
            }
        )
    return {
        "schema_version": BATCH_SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "design_id": manifest["design_id"],
        "family_id": manifest["family_id"],
        "config": manifest["config"],
        "jobs": jobs,
        "notes": [
            "Commands prepare replay through the existing PCS promote-source-candidate path.",
            "If run_post_sim=false, --skip-sim is used so layout/DRC/LVS/PEX can be collected without simulation.",
        ],
    }


def _validate_candidate(
    candidate: dict[str, Any],
    *,
    index: int,
    design_id: str,
    allowed_variables: dict[str, dict[str, Any]],
    default_values: dict[str, float | int],
) -> dict[str, Any]:
    if not isinstance(candidate, dict):
        raise SizingManifestError(f"candidate[{index}] must be a mapping")
    candidate_id = _required_str(candidate, "candidate_id", prefix=f"candidate[{index}]")
    source_type = _required_str(candidate, "source_type", prefix=f"candidate[{index}]")
    sizing = candidate.get("sizing")
    if not isinstance(sizing, dict):
        raise SizingManifestError(f"candidate {candidate_id}: sizing must be a mapping")
    values = sizing.get("values")
    units = sizing.get("units")
    if not isinstance(values, dict) or not values:
        raise SizingManifestError(f"candidate {candidate_id}: sizing.values must be non-empty")
    if not isinstance(units, dict):
        raise SizingManifestError(f"candidate {candidate_id}: sizing.units must be a mapping")
    for name, value in values.items():
        if name not in allowed_variables:
            raise SizingManifestError(f"candidate {candidate_id}: unknown sizing variable {name!r}")
        if name not in units:
            raise SizingManifestError(f"candidate {candidate_id}: missing unit for sizing variable {name!r}")
        _validate_value(candidate_id, name, value, allowed_variables[name])
    action_names = list(sizing.get("action_names") or values.keys())
    action_vector = list(sizing.get("action_vector") or [values[name] for name in action_names])
    if len(action_names) != len(action_vector):
        raise SizingManifestError(f"candidate {candidate_id}: action_names/action_vector length mismatch")
    for name in action_names:
        if name not in values:
            raise SizingManifestError(f"candidate {candidate_id}: action name {name!r} missing from sizing.values")
    complete_values = dict(default_values)
    complete_values.update(values)
    complete_units = _default_units(allowed_variables)
    complete_units.update(units)
    return {
        **candidate,
        "design_id": candidate.get("design_id", design_id),
        "sizing": {
            **sizing,
            "values": complete_values,
            "units": complete_units,
            "action_names": action_names,
            "action_vector": action_vector,
            "provided_sizing_count": len(values),
        },
    }


def _validate_value(candidate_id: str, name: str, value: Any, spec: dict[str, Any]) -> None:
    if not isinstance(value, (int, float)):
        raise SizingManifestError(f"candidate {candidate_id}: sizing variable {name!r} must be numeric")
    numeric = float(value)
    if "min" in spec and numeric < float(spec["min"]):
        raise SizingManifestError(f"candidate {candidate_id}: sizing variable {name!r} below min")
    if "max" in spec and numeric > float(spec["max"]):
        raise SizingManifestError(f"candidate {candidate_id}: sizing variable {name!r} above max")
    if spec.get("integer") and int(value) != numeric:
        raise SizingManifestError(f"candidate {candidate_id}: sizing variable {name!r} must be integer")


def _sizing_variables(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    variables = config.get("sizing_variables")
    if not isinstance(variables, list) or not variables:
        raise SizingManifestError("config has no sizing_variables")
    result = {}
    for variable in variables:
        if isinstance(variable, dict) and variable.get("name"):
            result[str(variable["name"])] = variable
    return result


def _default_sizing_values(variables: dict[str, dict[str, Any]]) -> dict[str, float | int]:
    defaults: dict[str, float | int] = {}
    for name, spec in variables.items():
        if "init" in spec:
            value = spec["init"]
        elif "min" in spec and "max" in spec:
            value = (float(spec["min"]) + float(spec["max"])) / 2.0
        elif "min" in spec:
            value = spec["min"]
        else:
            raise SizingManifestError(f"config sizing variable {name!r} has no init/default")
        if spec.get("integer"):
            value = int(value)
        defaults[name] = value
    return defaults


def _default_units(variables: dict[str, dict[str, Any]]) -> dict[str, str]:
    units = {}
    for name, spec in variables.items():
        if spec.get("integer"):
            units[name] = "count"
        else:
            units[name] = str(spec.get("unit") or "scalar")
    return units


def _expected_flow(raw: Any) -> dict[str, bool]:
    flow = raw if isinstance(raw, dict) else {}
    return {
        "run_layout": bool(flow.get("run_layout", True)),
        "run_drc": bool(flow.get("run_drc", True)),
        "run_lvs": bool(flow.get("run_lvs", True)),
        "run_pex": bool(flow.get("run_pex", True)),
        "run_post_sim": bool(flow.get("run_post_sim", False)),
    }


def _required_str(mapping: dict[str, Any], key: str, *, prefix: str = "manifest") -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SizingManifestError(f"{prefix}: missing required string field {key!r}")
    return value.strip()


def _load_manifest(manifest_or_path: dict[str, Any] | Path) -> dict[str, Any]:
    if isinstance(manifest_or_path, dict):
        return dict(manifest_or_path)
    text = manifest_or_path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise SizingManifestError("manifest file must contain a mapping")
    return data


def _resolve_path(raw: str, repo_root: Path) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return repo_root / path


def _write_jobs_csv(jobs: list[dict[str, Any]], path: Path) -> None:
    fields = ["candidate_id", "design_id", "family_id", "source_state", "source_state_sha256", "command"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for job in jobs:
            writer.writerow({**{field: job.get(field) for field in fields}, "command": " ".join(job["command"])})


def _render_readme(manifest: dict[str, Any], batch_manifest: dict[str, Any]) -> str:
    lines = [
        "# Sizing candidate replay preparation",
        "",
        f"- schema_version: `{MANIFEST_SCHEMA_VERSION}`",
        f"- design_id: `{manifest['design_id']}`",
        f"- family_id: `{manifest['family_id']}`",
        f"- candidates: {len(manifest['candidates'])}",
        "",
        "| candidate_id | source_state | replay command |",
        "|---|---|---|",
    ]
    for job in batch_manifest["jobs"]:
        lines.append(f"| {job['candidate_id']} | `{job['source_state']}` | `{' '.join(job['command'])}` |")
    lines.extend(["", "Run these jobs to collect layout/DRC/LVS/PEX with the existing PCS flow.", ""])
    return "\n".join(lines)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--repo-root", default=Path("."), type=Path)
    args = parser.parse_args()
    summary = prepare_sizing_candidate_replay(args.manifest, output_dir=args.output_dir, repo_root=args.repo_root)
    print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
