"""Convert AnalogGym-Opt GRPO smoke outputs into a versioned export contract.

This module is deliberately narrow: it records actions already produced by
AnalogGym-Opt. It does not train, resample, clip, or repair candidates.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import yaml


SCHEMA_VERSION = "grpo_export_contract.v1"


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    try:
        import numpy as np

        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, np.generic):
            return value.item()
    except Exception:
        pass
    return value


def _git_commit(repo: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"


def _action_parameter_names(circuit_config_path: Path) -> List[str]:
    config = yaml.safe_load(circuit_config_path.read_text()) or {}
    devices = config.get("device") or {}
    names: List[str] = []
    for device_name, device_config in devices.items():
        ranges = device_config.get("range") or {}
        for param_name in ranges.keys():
            names.append(f"{param_name}_{device_name}")
    return names


def _load_candidate_records(run_dir: Path) -> List[Tuple[str, Dict[str, Any]]]:
    sources = [
        ("recommended_candidates_tt", run_dir / "recommended_candidates_tt" / "recommended_candidates.json"),
        ("top_designs_tt", run_dir / "top_designs_tt" / "top_designs_summary.json"),
        ("best_pareto_archive", run_dir / "logs" / "best_pareto_archive_latest.json"),
        ("best_objective_records", run_dir / "logs" / "best_objective_records_latest.json"),
    ]
    records: List[Tuple[str, Dict[str, Any]]] = []
    for source_name, path in sources:
        if not path.exists():
            continue
        data = json.loads(path.read_text())
        if isinstance(data, dict):
            iterable: Iterable[Dict[str, Any]] = [
                {**value, "selection_metric": key}
                for key, value in data.items()
                if isinstance(value, dict)
            ]
        elif isinstance(data, list):
            iterable = [value for value in data if isinstance(value, dict)]
        else:
            iterable = []
        for record in iterable:
            records.append((source_name, record))
    return records


def _candidate_has_actions(record: Dict[str, Any]) -> bool:
    return record.get("action_normalized") is not None and record.get("action_real") is not None


def _build_sizing(action_real: Sequence[Any], parameter_names: Sequence[str]) -> Dict[str, Any]:
    if len(action_real) != len(parameter_names):
        raise ValueError(
            f"action_real length {len(action_real)} does not match action parameter count {len(parameter_names)}"
        )
    sizing: Dict[str, Any] = {}
    for name, value in zip(parameter_names, action_real):
        if name.startswith("M_"):
            sizing[name] = int(round(float(value)))
        else:
            sizing[name] = value
    return sizing


def validate_grpo_export(export: Dict[str, Any]) -> None:
    required_top = [
        "schema_version",
        "source_repo",
        "source_commit",
        "circuit_id",
        "pcs_design_id",
        "action_space_contract_id",
        "action_parameter_names",
        "run_id",
        "mode",
        "steps",
        "candidate_count",
        "candidates",
    ]
    for key in required_top:
        if key not in export:
            raise ValueError(f"GRPO export missing top-level field: {key}")
    if export["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"unsupported schema_version: {export['schema_version']}")
    candidates = export.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("GRPO export field candidates must be a list")
    if int(export.get("candidate_count", -1)) != len(candidates):
        raise ValueError("candidate_count does not match candidates length")
    action_parameter_names = export.get("action_parameter_names")
    if not isinstance(action_parameter_names, list) or not action_parameter_names:
        raise ValueError("action_parameter_names must be a non-empty list")

    required_candidate = [
        "candidate_id",
        "action_normalized",
        "action_real",
        "provenance_kind",
        "sizing",
        "reward",
        "pre_layout_metrics",
    ]
    for idx, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            raise ValueError(f"candidate #{idx} is not an object")
        for key in required_candidate:
            if key not in candidate:
                raise ValueError(f"candidate {candidate.get('candidate_id', idx)} missing field: {key}")
        if not isinstance(candidate["action_normalized"], list) or not candidate["action_normalized"]:
            raise ValueError(f"candidate {candidate['candidate_id']} action_normalized must be a non-empty list")
        if not isinstance(candidate["action_real"], list) or not candidate["action_real"]:
            raise ValueError(f"candidate {candidate['candidate_id']} action_real must be a non-empty list")
        if len(candidate["action_normalized"]) != len(candidate["action_real"]):
            raise ValueError(f"candidate {candidate['candidate_id']} action lengths differ")
        if len(candidate["action_real"]) != len(action_parameter_names):
            raise ValueError(f"candidate {candidate['candidate_id']} action length does not match action_parameter_names")
        if not isinstance(candidate["sizing"], dict) or not candidate["sizing"]:
            raise ValueError(f"candidate {candidate['candidate_id']} sizing must be a non-empty object")


def convert_analoggym_run_to_export(
    *,
    run_dir: Path,
    circuit_config_path: Path,
    source_repo: Path,
    circuit_id: str,
    pcs_design_id: str,
    action_space_contract_id: str,
    mode: str,
    steps: int,
    seed: Optional[int],
    output_path: Path,
) -> Dict[str, Any]:
    run_dir = Path(run_dir)
    parameter_names = _action_parameter_names(Path(circuit_config_path))
    run_id = run_dir.name
    candidates: List[Dict[str, Any]] = []
    skipped_without_actions = 0
    seen = set()

    for source_name, record in _load_candidate_records(run_dir):
        if not _candidate_has_actions(record):
            skipped_without_actions += 1
            continue
        action_normalized = _jsonable(record.get("action_normalized"))
        action_real = _jsonable(record.get("action_real"))
        key = json.dumps(action_real, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        candidate_index = len(candidates) + 1
        sizing = _build_sizing(action_real, parameter_names)
        candidates.append(
            {
                "candidate_id": f"{run_id}_tt_{candidate_index:04d}",
                "provenance_kind": "fresh_local_grpo_smoke",
                "source_file_group": source_name,
                "episode": record.get("circuit_spec"),
                "design_idx": record.get("design_idx"),
                "rank": int(record.get("rank", candidate_index)),
                "candidate_source": record.get("candidate_source", source_name),
                "evaluation_source": record.get("evaluation_source", "unknown"),
                "action_normalized": action_normalized,
                "action_real": action_real,
                "sizing": sizing,
                "reward": record.get("training_reward", record.get("reward")),
                "utility": record.get("utility"),
                "pm_feasible": record.get("pm_feasible"),
                "pm_violation": record.get("pm_violation"),
                "objective_rewards": _jsonable(record.get("objective_rewards", {})),
                "pre_layout_metrics": _jsonable(record.get("performance", record.get("raw_metric_summary", {}))),
            }
        )

    export = {
        "schema_version": SCHEMA_VERSION,
        "source_repo": str(Path(source_repo).resolve()),
        "source_commit": _git_commit(Path(source_repo)),
        "circuit_id": circuit_id,
        "pcs_design_id": pcs_design_id,
        "action_space_contract_id": action_space_contract_id,
        "action_parameter_names": parameter_names,
        "run_id": run_id,
        "run_dir": str(run_dir.resolve()),
        "mode": mode,
        "steps": int(steps),
        "seed": seed,
        "candidate_count": len(candidates),
        "skipped_records_without_actions": skipped_without_actions,
        "candidates": candidates,
    }
    validate_grpo_export(export)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(export, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return export


def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build/validate GRPO export contract files.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    build = sub.add_parser("build-from-analoggym-run")
    build.add_argument("--run-dir", required=True)
    build.add_argument("--circuit-config", required=True)
    build.add_argument("--source-repo", required=True)
    build.add_argument("--circuit-id", default="amp_dfcfc2")
    build.add_argument("--pcs-design-id", default="leung_dfcfc2_pin_3")
    build.add_argument(
        "--action-space-contract-id",
        default="amp_dfcfc2_to_leung_dfcfc2_pin_3.analoggym_action_space_v1",
    )
    build.add_argument("--mode", default="tt-only")
    build.add_argument("--steps", type=int, default=1)
    build.add_argument("--seed", type=int, default=None)
    build.add_argument("--output", required=True)

    validate = sub.add_parser("validate")
    validate.add_argument("export_json")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse_args(argv)
    if args.cmd == "validate":
        export = json.loads(Path(args.export_json).read_text())
        validate_grpo_export(export)
        print(json.dumps({"status": "ok", "candidate_count": len(export["candidates"])}, indent=2))
        return 0
    export = convert_analoggym_run_to_export(
        run_dir=Path(args.run_dir),
        circuit_config_path=Path(args.circuit_config),
        source_repo=Path(args.source_repo),
        circuit_id=args.circuit_id,
        pcs_design_id=args.pcs_design_id,
        action_space_contract_id=args.action_space_contract_id,
        mode=args.mode,
        steps=args.steps,
        seed=args.seed,
        output_path=Path(args.output),
    )
    print(
        json.dumps(
            {
                "status": "ok",
                "output": str(Path(args.output)),
                "candidate_count": export["candidate_count"],
                "skipped_records_without_actions": export["skipped_records_without_actions"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
