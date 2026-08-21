"""YAML-driven action mapping from GRPO export vectors to PCS manifest JSONL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

import yaml

from tools.analog_harness.ml.grpo_export_contract import validate_grpo_export


SCHEMA_VERSION = "analog_harness.action_mapping_contract.v1"


def load_action_mapping_contract(path: Path) -> Dict[str, Any]:
    data = yaml.safe_load(path.read_text()) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a mapping")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"{path} schema_version must be {SCHEMA_VERSION}")
    for key in ("contract_id", "source_circuit_id", "target_pcs_design_id"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError(f"{path} missing required string field {key}")
    variables = data.get("variables")
    if not isinstance(variables, dict) or not variables:
        raise ValueError(f"{path} variables must be a non-empty mapping")
    for source_name, spec in variables.items():
        if not isinstance(spec, dict):
            raise ValueError(f"{path} variable {source_name!r} must be a mapping")
        if not isinstance(spec.get("pcs_name"), str) or not spec["pcs_name"].strip():
            raise ValueError(f"{path} variable {source_name!r} missing pcs_name")
        if not isinstance(spec.get("unit"), str) or not spec["unit"].strip():
            raise ValueError(f"{path} variable {source_name!r} missing unit")
    return data


def _mapped_value(raw_value: Any, spec: Dict[str, Any]) -> Any:
    value = float(raw_value)
    if "scale" in spec:
        value *= float(spec["scale"])
    if bool(spec.get("integer")):
        return int(round(value))
    return value


def _map_candidate(export: Dict[str, Any], mapping: Dict[str, Any], candidate: Dict[str, Any]) -> Dict[str, Any]:
    action_names = list(export["action_parameter_names"])
    action_real = list(candidate["action_real"])
    variables = mapping["variables"]
    missing = [name for name in action_names if name not in variables]
    if missing:
        raise ValueError(f"mapping {mapping['contract_id']} missing source variables: {', '.join(missing)}")

    values: Dict[str, Any] = {}
    units: Dict[str, str] = {}
    mapped_action_names = []
    mapped_action_vector = []
    for source_name, raw_value in zip(action_names, action_real):
        spec = variables[source_name]
        pcs_name = spec["pcs_name"]
        mapped = _mapped_value(raw_value, spec)
        values[pcs_name] = mapped
        units[pcs_name] = spec["unit"]
        mapped_action_names.append(pcs_name)
        mapped_action_vector.append(mapped)

    return {
        "candidate_id": candidate["candidate_id"],
        "source_type": "grpo_export",
        "parent_candidate_id": candidate["candidate_id"],
        "action_space_contract_id": export["action_space_contract_id"],
        "action_mapping_contract_id": mapping["contract_id"],
        "action_names": action_names,
        "action_normalized": candidate["action_normalized"],
        "action_real": action_real,
        "sizing": {
            "values": values,
            "units": units,
            "action_names": mapped_action_names,
            "action_vector": mapped_action_vector,
        },
        "provenance": {
            "generator": "action_mapping_contract",
            "mapping_contract": mapping["contract_id"],
            "original_candidate_id": candidate["candidate_id"],
            "original_circuit": export["circuit_id"],
            "target_design_id": export["pcs_design_id"],
            "action_space_contract_id": export["action_space_contract_id"],
            "grpo_reward": candidate.get("reward"),
            "grpo_training_reward": candidate.get("reward"),
            "grpo_pm_feasible": candidate.get("pm_feasible"),
            "grpo_pm_violation": candidate.get("pm_violation"),
            "grpo_evaluation_source": candidate.get("evaluation_source"),
            "grpo_source": {
                "run_id": export["run_id"],
                "source_repo": export["source_repo"],
                "source_commit": export["source_commit"],
                "provenance_kind": candidate.get("provenance_kind"),
            },
            "grpo_performance": candidate.get("pre_layout_metrics", {}),
        },
        "performance": candidate.get("pre_layout_metrics", {}),
    }


def map_grpo_export_to_pcs_jsonl(*, export_path: Path, mapping_path: Path, output_path: Path) -> Dict[str, Any]:
    export = json.loads(Path(export_path).read_text())
    validate_grpo_export(export)
    mapping = load_action_mapping_contract(Path(mapping_path))
    if mapping["source_circuit_id"] != export["circuit_id"]:
        raise ValueError(
            f"mapping source {mapping['source_circuit_id']} does not match export circuit {export['circuit_id']}"
        )
    if mapping["target_pcs_design_id"] != export["pcs_design_id"]:
        raise ValueError(
            f"mapping target {mapping['target_pcs_design_id']} does not match export PCS design {export['pcs_design_id']}"
        )
    records = [_map_candidate(export, mapping, candidate) for candidate in export["candidates"]]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records))
    return {
        "status": "ok",
        "mapping_contract_id": mapping["contract_id"],
        "mapped_candidates": len(records),
        "output": str(output_path),
    }


def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", required=True, type=Path)
    parser.add_argument("--mapping", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse_args(argv)
    summary = map_grpo_export_to_pcs_jsonl(
        export_path=args.export,
        mapping_path=args.mapping,
        output_path=args.output,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
