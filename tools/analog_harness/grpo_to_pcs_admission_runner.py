"""Reproducible GRPO-to-PCS admission batch runner.

This module turns the previously manual sequence

``prepare-sizing-replay -> per-candidate config -> promote-source-candidate
-> admission summary``

into one resumable terminal entry point.  It intentionally keeps the existing
PCS closure path as the source of truth; the runner only prepares isolated
per-candidate configs, invokes the existing CLI, and summarizes produced
evidence.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from tools.analog_harness.parasitic_raw_spice_graph_edges import parse_raw_spice_capacitor_edges
from tools.analog_harness.sizing_candidate_manifest import prepare_sizing_candidate_replay


SCHEMA_VERSION = "grpo_to_pcs_admission_runner.v1"
SUMMARY_SCHEMA_VERSION = "grpo_to_pcs_admission_summary.v1"
TIMEOUT_RETURN_CODE = 124


@dataclass(frozen=True)
class CandidateRunPlan:
    """One candidate's isolated replay command."""

    candidate_id: str
    config_path: Path
    source_state_path: Path
    run_dir: Path
    command: list[str]

    def to_json(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "config_path": str(self.config_path),
            "source_state_path": str(self.source_state_path),
            "run_dir": str(self.run_dir),
            "command": self.command,
        }


def load_batch_replay_manifest(path: Path) -> dict[str, Any]:
    """Load a prepared PCS batch replay manifest."""

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"batch replay manifest must be a JSON object: {path}")
    for key in ("config", "design_id", "family_id", "jobs"):
        if key not in data:
            raise ValueError(f"batch replay manifest missing {key!r}: {path}")
    if not isinstance(data["jobs"], list) or not data["jobs"]:
        raise ValueError(f"batch replay manifest must contain at least one job: {path}")
    return data


def prepare_candidate_configs(
    batch_manifest: dict[str, Any],
    *,
    output_dir: Path,
    repo_root: Path | None = None,
) -> list[CandidateRunPlan]:
    """Write per-candidate config files with isolated ``paths.runs_dir``."""

    repo_root = (repo_root or Path.cwd()).resolve()
    output_dir = output_dir.resolve()
    base_config_path = _resolve_path(Path(str(batch_manifest["config"])), repo_root)
    base_config = yaml.safe_load(base_config_path.read_text(encoding="utf-8"))
    if not isinstance(base_config, dict):
        raise ValueError(f"base config must contain a mapping: {base_config_path}")

    configs_dir = output_dir / "configs"
    runs_root = output_dir / "runs"
    configs_dir.mkdir(parents=True, exist_ok=True)
    runs_root.mkdir(parents=True, exist_ok=True)

    plans: list[CandidateRunPlan] = []
    for job in batch_manifest["jobs"]:
        candidate_id = str(job["candidate_id"])
        candidate_config = dict(base_config)
        candidate_config["paths"] = dict(base_config.get("paths", {}))
        run_dir = (runs_root / candidate_id).resolve()
        candidate_config["paths"]["runs_dir"] = str(run_dir)
        config_path = (configs_dir / f"{candidate_id}.yaml").resolve()
        config_path.write_text(yaml.safe_dump(candidate_config, sort_keys=False), encoding="utf-8")
        source_state = _resolve_path(Path(str(job["source_state"])), repo_root)
        command = [
            "python3",
            "-m",
            "tools.analog_harness.cli",
            "promote-source-candidate",
            "--config",
            str(config_path),
            "--source-state",
            str(source_state),
            "--no-knowledge-archive",
        ]
        if _job_skips_sim(job):
            command.append("--skip-sim")
        plans.append(
            CandidateRunPlan(
                candidate_id=candidate_id,
                config_path=config_path,
                source_state_path=source_state,
                run_dir=run_dir,
                command=command,
            )
        )
    return plans


def run_admission_batch(
    *,
    batch_replay_manifest: Path,
    output_dir: Path,
    timeout_s: int = 1800,
    kill_after_s: int = 60,
    resume: bool = False,
    dry_run: bool = False,
    limit: int | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Run a prepared batch replay manifest through the existing PCS CLI."""

    repo_root = (repo_root or Path.cwd()).resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    batch_manifest = load_batch_replay_manifest(batch_replay_manifest)
    plans = prepare_candidate_configs(batch_manifest, output_dir=output_dir, repo_root=repo_root)
    if limit is not None:
        plans = plans[: max(0, int(limit))]

    run_plan = {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "batch_replay_manifest": str(batch_replay_manifest),
        "output_dir": str(output_dir),
        "timeout_s": int(timeout_s),
        "kill_after_s": int(kill_after_s),
        "dry_run": bool(dry_run),
        "resume": bool(resume),
        "jobs": [plan.to_json() for plan in plans],
    }
    (output_dir / "run_plan.json").write_text(
        json.dumps(run_plan, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if dry_run:
        progress = _progress("dry_run", len(plans), 0, {})
        _write_json(output_dir / "promotion_progress.json", progress)
        return progress

    logs_dir = output_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    results_path = output_dir / "promotion_results.jsonl"
    existing = _load_existing_results(results_path) if resume else {}
    results = [existing[cid] for cid in sorted(existing)]
    completed = len(existing)

    with results_path.open("a", encoding="utf-8") as result_handle:
        for plan in plans:
            if resume and plan.candidate_id in existing:
                continue
            result = _run_one_plan(
                plan,
                timeout_s=timeout_s,
                kill_after_s=kill_after_s,
                logs_dir=logs_dir,
                cwd=repo_root,
            )
            result_handle.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
            result_handle.flush()
            results.append(result)
            completed += 1
            _write_json(
                output_dir / "promotion_progress.json",
                _progress("running", len(plans), completed, _returncode_counts(results)),
            )

    progress = _progress("finished", len(plans), completed, _returncode_counts(results))
    _write_json(output_dir / "promotion_progress.json", progress)
    source_state_dir = _infer_source_state_dir(batch_manifest)
    summary = build_admission_summary(
        output_dir=output_dir,
        batch_manifest=batch_manifest,
        source_state_dir=source_state_dir,
        timeout_s=timeout_s,
        kill_after_s=kill_after_s,
    )
    write_admission_outputs(summary, output_dir)
    return progress


def build_admission_summary(
    *,
    output_dir: Path,
    batch_manifest: dict[str, Any],
    source_state_dir: Path,
    timeout_s: int,
    kill_after_s: int,
) -> dict[str, Any]:
    """Summarize PCS admission evidence produced by a batch run."""

    output_dir = output_dir.resolve()
    results = _load_results_list(output_dir / "promotion_results.jsonl")
    result_by_id = {str(row["candidate_id"]): row for row in results}
    records = []
    for job in batch_manifest["jobs"]:
        candidate_id = str(job["candidate_id"])
        result = result_by_id.get(candidate_id, {"candidate_id": candidate_id, "returncode": None, "summary": None})
        source_state_path = _resolve_source_state_for_job(job, source_state_dir)
        state = _load_json_or_empty(source_state_path)
        values = state.get("values", {}) if isinstance(state.get("values"), dict) else {}
        run_dir = output_dir / "runs" / candidate_id
        raw_paths = sorted(run_dir.glob("cand_*/layout/*_extracted.raw.spice"))
        raw_path = raw_paths[0] if raw_paths else None
        parsed = None
        if raw_path:
            parsed = parse_raw_spice_capacitor_edges(raw_path, design_id=str(batch_manifest["design_id"]), candidate_id=candidate_id)
        summary = result.get("summary") if isinstance(result.get("summary"), dict) else {}
        closure = summary.get("best_closure_level") or _load_closure_from_run_summary(run_dir)
        returncode = result.get("returncode")
        admission_status, failure_stage = _admission_status(returncode, closure, raw_path)
        layout_summary = _parse_layout_summary(run_dir)
        record = {
            "action_space_contract_id": _action_space_contract_id(state),
            "admission_status": admission_status,
            "best_closure_level": closure,
            "candidate_id": candidate_id,
            "design_id": str(batch_manifest["design_id"]),
            "failure_stage": failure_stage or layout_summary.get("FAILED_STAGE"),
            "l0_status": "replayable" if source_state_path.exists() else "missing_source_state",
            "m12_m": _first_number(
                values.get("mosfet_12_1_m_gmf2_pmos"),
                values.get("M_M12"),
                job.get("m12_m"),
            ),
            "m_c0": _first_number(values.get("capacitor_0"), values.get("M_C0"), job.get("m_c0")),
            "m_c1": _first_number(values.get("capacitor_1"), values.get("M_C1"), job.get("m_c1")),
            "performance_feasible": summary.get("best_performance_feasible"),
            "pex_cap_count": parsed["summary"]["edge_count_all"] if parsed else _int_or_none(layout_summary.get("PEX_CAPS")),
            "pex_summary_path": str(raw_path.parent / "pex_summary.md") if raw_path and (raw_path.parent / "pex_summary.md").exists() else None,
            "pex_total_cap_ff": parsed["summary"]["total_cap_ff"] if parsed else _float_from_text(layout_summary.get("PEX_TOTAL_CAP_FF")),
            "raw_pex_path": str(raw_path) if raw_path else None,
            "raw_spice_sha256": parsed["summary"]["raw_spice_sha256"] if parsed else None,
            "returncode": returncode,
            "source_family": str(batch_manifest["family_id"]),
            "source_run_dir": str(run_dir),
            "source_state_path": str(source_state_path),
            "timeout_policy": f"timeout --kill-after={kill_after_s}s {timeout_s}s" if returncode == TIMEOUT_RETURN_CODE else None,
            "default_training_inclusion": admission_status == "admitted_raw_pex_graph",
        }
        records.append(record)
    counts = _admission_counts(records)
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "batch_id": str(batch_manifest.get("family_id") or "unknown_batch"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "design_id": str(batch_manifest["design_id"]),
        "source_family": str(batch_manifest["family_id"]),
        "config": str(batch_manifest["config"]),
        "timeout_policy": {
            "per_candidate_timeout_s": int(timeout_s),
            "kill_after_s": int(kill_after_s),
            "admission_handling": "timeout samples are retained as simulation_timeout_or_hang labels and excluded from default graph training",
        },
        "counts": counts,
        "admission_status_counts": {
            key: counts[key]
            for key in (
                "l6_admitted_raw_pex_graph",
                "raw_pex_available_not_l6",
                "physical_closure_failed_no_raw_pex",
                "simulation_timeout_or_hang",
            )
        },
        "records": records,
    }


def write_admission_outputs(summary: dict[str, Any], output_dir: Path) -> dict[str, str]:
    """Write standard admission summary and label files."""

    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "admission_summary": output_dir / "admission_summary.json",
        "admitted_graphs": output_dir / "admitted_graphs.jsonl",
        "failure_labels": output_dir / "physical_closure_failure_labels.jsonl",
        "timeout_labels": output_dir / "timeout_labels.jsonl",
        "raw_pex_available_not_l6": output_dir / "raw_pex_available_not_l6.jsonl",
    }
    _write_json(outputs["admission_summary"], summary)
    _write_jsonl(outputs["admitted_graphs"], [r for r in summary["records"] if r["admission_status"] == "admitted_raw_pex_graph"])
    _write_jsonl(outputs["failure_labels"], [r for r in summary["records"] if r["admission_status"] != "admitted_raw_pex_graph"])
    _write_jsonl(outputs["timeout_labels"], [r for r in summary["records"] if r["admission_status"] == "simulation_timeout_or_hang"])
    _write_jsonl(outputs["raw_pex_available_not_l6"], [r for r in summary["records"] if r["admission_status"] == "raw_pex_available_not_l6"])
    _write_csv(output_dir / "admission_table.csv", summary["records"])
    return {key: str(value) for key, value in outputs.items()}


def prepare_replay_from_sizing_manifest(
    *,
    sizing_manifest: Path,
    output_dir: Path,
    repo_root: Path | None = None,
) -> Path:
    """Run L0 sizing replay preparation and return the batch manifest path."""

    replay_dir = output_dir / "l0_replay_preparation"
    prepare_sizing_candidate_replay(sizing_manifest, output_dir=replay_dir, repo_root=repo_root)
    return replay_dir / "batch_replay_manifest.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--sizing-manifest", type=Path, help="L0 sizing manifest accepted by prepare-sizing-replay.")
    src.add_argument("--batch-replay-manifest", type=Path, help="Prepared batch_replay_manifest.json.")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--timeout-s", type=int, default=1800)
    parser.add_argument("--kill-after-s", type=int, default=60)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path.cwd().resolve()
    output_dir = args.output_dir.resolve()
    batch_manifest = args.batch_replay_manifest
    if args.sizing_manifest:
        batch_manifest = prepare_replay_from_sizing_manifest(
            sizing_manifest=args.sizing_manifest,
            output_dir=output_dir,
            repo_root=repo_root,
        )
    assert batch_manifest is not None
    result = run_admission_batch(
        batch_replay_manifest=batch_manifest,
        output_dir=output_dir,
        timeout_s=args.timeout_s,
        kill_after_s=args.kill_after_s,
        resume=bool(args.resume),
        dry_run=bool(args.dry_run),
        limit=args.limit,
        repo_root=repo_root,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


def _run_one_plan(
    plan: CandidateRunPlan,
    *,
    timeout_s: int,
    kill_after_s: int,
    logs_dir: Path,
    cwd: Path,
) -> dict[str, Any]:
    wrapped = ["timeout", f"--kill-after={int(kill_after_s)}s", f"{int(timeout_s)}s", *plan.command]
    completed = subprocess.run(wrapped, cwd=cwd, text=True, capture_output=True, check=False)
    stdout_path = logs_dir / f"{plan.candidate_id}.stdout.json"
    stderr_path = logs_dir / f"{plan.candidate_id}.stderr.log"
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    summary = _parse_stdout_summary(completed.stdout)
    return {
        "candidate_id": plan.candidate_id,
        "returncode": completed.returncode,
        "command": wrapped,
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
        "stderr_tail": "\n".join(completed.stderr.splitlines()[-20:]),
        "summary": summary,
    }


def _admission_status(returncode: Any, closure: str | None, raw_path: Path | None) -> tuple[str, str | None]:
    if returncode == TIMEOUT_RETURN_CODE:
        return "simulation_timeout_or_hang", "simulation_timeout_or_hang"
    if closure == "L6_post_layout_pvt" and raw_path:
        return "admitted_raw_pex_graph", None
    if raw_path:
        return "raw_pex_available_not_l6", "post_layout_or_lvs_not_l6"
    return "physical_closure_failed", "magical_place_route"


def _admission_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "candidates": len(records),
        "l0_replayable": sum(1 for r in records if r["l0_status"] == "replayable"),
        "l6_admitted_raw_pex_graph": sum(1 for r in records if r["admission_status"] == "admitted_raw_pex_graph"),
        "raw_pex_available_not_l6": sum(1 for r in records if r["admission_status"] == "raw_pex_available_not_l6"),
        "physical_closure_failed_no_raw_pex": sum(1 for r in records if r["admission_status"] == "physical_closure_failed"),
        "simulation_timeout_or_hang": sum(1 for r in records if r["admission_status"] == "simulation_timeout_or_hang"),
        "default_training_included": sum(1 for r in records if r["default_training_inclusion"]),
        "default_training_excluded": sum(1 for r in records if not r["default_training_inclusion"]),
    }


def _resolve_path(path: Path, repo_root: Path) -> Path:
    return path if path.is_absolute() else (repo_root / path).resolve()


def _job_skips_sim(job: dict[str, Any]) -> bool:
    flow = job.get("expected_flow")
    return isinstance(flow, dict) and not bool(flow.get("run_post_sim", True))


def _progress(status: str, total: int, completed: int, returncodes: dict[str, int]) -> dict[str, Any]:
    return {
        "schema_version": "grpo_to_pcs_admission_runner.progress.v1",
        "status": status,
        "total": total,
        "completed": completed,
        "returncodes": returncodes,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _returncode_counts(results: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for result in results:
        key = str(result.get("returncode"))
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _load_existing_results(path: Path) -> dict[str, dict[str, Any]]:
    return {str(row["candidate_id"]): row for row in _load_results_list(path)}


def _load_results_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _parse_stdout_summary(stdout: str) -> dict[str, Any] | None:
    text = stdout.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _infer_source_state_dir(batch_manifest: dict[str, Any]) -> Path:
    first = Path(str(batch_manifest["jobs"][0]["source_state"]))
    return first.parent


def _resolve_source_state_for_job(job: dict[str, Any], source_state_dir: Path) -> Path:
    source = Path(str(job.get("source_state", "")))
    if source.exists():
        return source
    candidate = source_state_dir / f"{job['candidate_id']}.source_state.json"
    return candidate


def _load_json_or_empty(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _load_closure_from_run_summary(run_dir: Path) -> str | None:
    summary_path = run_dir / "summary.json"
    if not summary_path.exists():
        return None
    data = _load_json_or_empty(summary_path)
    closure = data.get("best_closure_level")
    return str(closure) if closure else None


def _parse_layout_summary(run_dir: Path) -> dict[str, str]:
    summaries = sorted(run_dir.glob("cand_*/layout/summary.md"))
    if not summaries:
        return {}
    fields: dict[str, str] = {}
    for line in summaries[0].read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("|") or line.count("|") < 3:
            continue
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(parts) >= 2 and parts[0] and parts[0] not in {"Field", "---"}:
            fields[parts[0]] = parts[1]
    return fields


def _first_number(*values: Any) -> float | int | None:
    for value in values:
        if value is None or isinstance(value, bool):
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if number.is_integer():
            return int(number)
        return number
    return None


def _int_or_none(value: Any) -> int | None:
    number = _first_number(value)
    return int(number) if number is not None else None


def _float_from_text(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).replace("fF", "").strip()
    try:
        return float(text)
    except ValueError:
        return None


def _action_space_contract_id(state: dict[str, Any]) -> str | None:
    meta = state.get("optimizer_metadata")
    if not isinstance(meta, dict):
        return None
    if meta.get("action_space_contract_id"):
        return str(meta["action_space_contract_id"])
    provenance = meta.get("provenance")
    if isinstance(provenance, dict) and provenance.get("action_space_contract_id"):
        return str(provenance["action_space_contract_id"])
    return None


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
