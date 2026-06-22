from __future__ import annotations

from pathlib import Path
from typing import Any


def _merge_status_counts(target: dict[str, int], source: dict[str, int]) -> None:
    for status, count in source.items():
        target[status] = target.get(status, 0) + count


def verify_artifact_path(path_text: str, repo_root: Path | None = None) -> dict:
    repo_root = repo_root or Path.cwd()
    normalized = path_text.replace("\\", "/")
    is_windows_absolute = ":" in normalized[:3]

    path = Path(path_text)
    try:
        if path.exists():
            return {"path": path_text, "status": "present", "portable": not is_windows_absolute}
    except OSError:
        return {
            "path": path_text,
            "status": "missing",
            "portable": False,
            "reason": "invalid_path_text",
        }

    repo_path = repo_root / normalized
    try:
        if repo_path.exists():
            return {"path": path_text, "status": "present", "portable": not is_windows_absolute}
    except OSError:
        return {
            "path": path_text,
            "status": "missing",
            "portable": False,
            "reason": "invalid_path_text",
        }

    if is_windows_absolute:
        return {
            "path": path_text,
            "status": "not_portable",
            "portable": False,
            "reason": "windows_absolute_path",
        }

    if normalized.startswith("generated/"):
        return {"path": path_text, "status": "generated_only_reference", "portable": False}

    return {"path": path_text, "status": "missing", "portable": False}


def verify_artifact_map(
    artifacts: dict[str, Any], repo_root: Path | None = None
) -> dict:
    reports = {}
    status_counts: dict[str, int] = {}

    for name, path_text in artifacts.items():
        report = verify_artifact_path(str(path_text), repo_root=repo_root)
        reports[name] = report
        status = report["status"]
        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        "artifact_count": len(reports),
        "status_counts": status_counts,
        "artifacts": reports,
    }


def verify_evidence_packets(
    packets: list[dict[str, Any]], repo_root: Path | None = None
) -> dict:
    stage_reports = {}
    status_counts: dict[str, int] = {}
    artifact_count = 0

    for index, packet in enumerate(packets):
        stage = packet.get("stage") or f"packet_{index}"
        report = verify_artifact_map(packet.get("artifacts") or {}, repo_root=repo_root)
        stage_reports[stage] = report
        artifact_count += report["artifact_count"]
        _merge_status_counts(status_counts, report["status_counts"])

    return {
        "packet_count": len(packets),
        "artifact_count": artifact_count,
        "status_counts": status_counts,
        "stage_reports": stage_reports,
    }


def verify_state_artifacts(state: dict[str, Any], repo_root: Path | None = None) -> dict:
    report = verify_evidence_packets(state.get("evidence") or [], repo_root=repo_root)
    return {"candidate_id": state.get("candidate_id"), **report}
