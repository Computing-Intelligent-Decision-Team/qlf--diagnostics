#!/usr/bin/env python3
"""Export physically trustworthy AnalogHarness parasitic-label candidates."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
import re
import shutil
import tarfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


PASS_VALUES = {"yes", "pass", "passed", "match", "matched", "true", "1"}
SKIP_NAMES = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".cache"}
SKIP_SUFFIXES = {".lock", ".sock", ".socket", ".lic"}
PEX_PATTERNS = (
    "*extracted.raw.spice",
    "*extracted*.pex.spice",
    "*raw_pex*.spice",
    "*.dspf",
    "*.spef",
)


class CandidateResult:
    def __init__(self, **values: Any) -> None:
        self.__dict__.update(values)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        text += "T00:00:00+00:00"
    elif text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def newest_evidence_time(state: dict[str, Any], state_path: Path) -> datetime:
    timestamps = [
        parse_time(item.get("timestamp"))
        for item in state.get("evidence", [])
        if isinstance(item, dict)
    ]
    valid = [value for value in timestamps if value is not None]
    if valid:
        return max(valid)
    return datetime.fromtimestamp(state_path.stat().st_mtime, tz=timezone.utc)


def _value_present(value: Any) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, (str, list, tuple, dict, set)):
        return bool(value)
    return True


def _contains_sizing_payload(value: Any, key_hint: str = "") -> bool:
    sizing_key = any(token in key_hint.lower() for token in ("action", "sizing", "assignment"))
    if sizing_key and _value_present(value):
        return True
    if isinstance(value, dict):
        return any(_contains_sizing_payload(child, str(key)) for key, child in value.items())
    return False


def _resolve_artifact(candidate: Path, raw_value: Any) -> Path | None:
    if not isinstance(raw_value, str) or not raw_value.strip():
        return None
    declared = Path(raw_value)
    choices = [declared]
    if not declared.is_absolute():
        choices.append(candidate / declared)
    choices.append(candidate / declared.name)
    for choice in choices:
        if choice.is_file():
            return choice.resolve()
    matches = [path for path in candidate.rglob(declared.name) if path.is_file()]
    return matches[0].resolve() if matches else None


def _find_source_netlist(candidate: Path, state: dict[str, Any]) -> Path | None:
    declared = state.get("artifacts", {}).get("netlist")
    found = _resolve_artifact(candidate, declared)
    if found:
        return found
    for pattern in ("case/*.sp", "case/*.spice", "case/*.cir"):
        matches = sorted(candidate.glob(pattern))
        if matches:
            return matches[0].resolve()
    return None


def _layout_evidence(state: dict[str, Any]) -> dict[str, Any] | None:
    matches = [
        item
        for item in state.get("evidence", [])
        if isinstance(item, dict) and item.get("stage") == "layout_verification"
    ]
    if not matches:
        return None
    return matches[-1]


def _metric(evidence: dict[str, Any], name: str) -> Any:
    for container_name in ("metrics", "physical_feedback"):
        container = evidence.get(container_name, {})
        if isinstance(container, dict) and name in container:
            return container[name]
    return None


def _find_raw_pex(candidate: Path, evidence: dict[str, Any] | None) -> Path | None:
    if evidence:
        artifacts = evidence.get("artifacts", {})
        for key in ("raw_extracted_netlist", "raw_pex", "pex_netlist", "extracted_netlist"):
            found = _resolve_artifact(candidate, artifacts.get(key) if isinstance(artifacts, dict) else None)
            if found:
                return found
    for pattern in PEX_PATTERNS:
        for path in sorted(candidate.rglob(pattern)):
            relative = path.relative_to(candidate).as_posix().lower()
            if path.is_file() and "/sim/" not in f"/{relative}":
                return path.resolve()
    return None


def parse_pex(path: Path | None) -> tuple[int, int]:
    if path is None or not path.is_file() or path.stat().st_size == 0:
        return 0, 0
    caps = 0
    resistors = 0
    try:
        with path.open("r", encoding="utf-8", errors="replace") as stream:
            for raw_line in stream:
                line = raw_line.strip()
                if not line or line[0] in "*.;+":
                    continue
                first = line[0].upper()
                if first == "C" and len(line.split()) >= 4:
                    caps += 1
                elif first == "R" and len(line.split()) >= 4:
                    resistors += 1
    except OSError:
        return 0, 0
    return caps, resistors


def evaluate_candidate(candidate: Path, since: datetime, until: datetime) -> CandidateResult:
    candidate = candidate.resolve()
    state_path = candidate / "state.json"
    reasons: list[str] = []
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return CandidateResult(
            candidate_dir=str(candidate), candidate_id=candidate.name, design_id=None,
            closure_level=None, completion_time=None, in_window=False, trusted=False,
            reasons=["state_json_missing_or_invalid"], drc_pass=False, lvs_pass=False,
            lineage_pass=False, raw_pex_path=None, raw_pex_sha256=None,
            source_netlist_path=None, source_netlist_sha256=None,
            verification_scope=None, parasitic_cap_count=0, parasitic_res_count=0,
            identity_sha256=None,
        )

    completed = newest_evidence_time(state, state_path)
    in_window = since <= completed <= until
    if not in_window:
        reasons.append("outside_time_window")

    closure = str(state.get("closure_level", ""))
    if not closure.upper().startswith("L6"):
        reasons.append("not_marked_l6")

    layout = _layout_evidence(state)
    drc_value = _metric(layout, "drc_count") if layout else None
    drc_pass = isinstance(drc_value, (int, float)) and not isinstance(drc_value, bool) and drc_value == 0
    if not drc_pass:
        reasons.append("drc_not_pass")

    lvs_value = _metric(layout, "lvs_match") if layout else None
    lvs_pass = str(lvs_value).strip().lower() in PASS_VALUES
    if not lvs_pass:
        reasons.append("connectivity_lvs_not_pass")

    source_netlist = _find_source_netlist(candidate, state)
    sizing_present = _contains_sizing_payload(state)
    if not sizing_present:
        for config in sorted((candidate / "case").glob("*.json")) if (candidate / "case").is_dir() else []:
            try:
                if _contains_sizing_payload(json.loads(config.read_text(encoding="utf-8"))):
                    sizing_present = True
                    break
            except (OSError, json.JSONDecodeError):
                continue
    lineage_pass = sizing_present and source_netlist is not None
    if not lineage_pass:
        reasons.append("sizing_lineage_unproven")

    raw_pex = _find_raw_pex(candidate, layout)
    cap_count, res_count = parse_pex(raw_pex)
    if raw_pex is None or cap_count + res_count == 0:
        reasons.append("raw_pex_missing_or_unparseable")

    verification_scope = None
    if layout:
        verification_scope = layout.get("verification_scope")
        if not verification_scope:
            feedback = layout.get("physical_feedback", {})
            if isinstance(feedback, dict):
                verification_scope = feedback.get("verification_scope")

    raw_hash = sha256_file(raw_pex) if raw_pex and raw_pex.is_file() else None
    source_hash = sha256_file(source_netlist) if source_netlist else None
    identity_hash = None
    if raw_hash and source_hash:
        identity_hash = hashlib.sha256(f"{source_hash}:{raw_hash}".encode()).hexdigest()

    return CandidateResult(
        candidate_dir=str(candidate),
        candidate_id=state.get("candidate_id", candidate.name),
        design_id=state.get("design_id"),
        closure_level=state.get("closure_level"),
        completion_time=completed.isoformat().replace("+00:00", "Z"),
        in_window=in_window,
        trusted=not reasons,
        reasons=reasons,
        drc_pass=drc_pass,
        lvs_pass=lvs_pass,
        lineage_pass=lineage_pass,
        raw_pex_path=str(raw_pex) if raw_pex else None,
        raw_pex_sha256=raw_hash,
        source_netlist_path=str(source_netlist) if source_netlist else None,
        source_netlist_sha256=source_hash,
        verification_scope=verification_scope,
        parasitic_cap_count=cap_count,
        parasitic_res_count=res_count,
        identity_sha256=identity_hash,
    )


def discover_candidates(roots: Iterable[Path]) -> list[Path]:
    candidates: set[Path] = set()
    for root in roots:
        root = root.expanduser().resolve()
        if not root.exists():
            continue
        if root.is_file() and root.name == "state.json":
            candidates.add(root.parent)
        elif (root / "state.json").is_file():
            candidates.add(root)
        else:
            candidates.update(path.parent for path in root.rglob("state.json"))
    return sorted(candidates)


def _safe_ignore(directory: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    base = Path(directory)
    for name in names:
        path = base / name
        lower = name.lower()
        if (
            name in SKIP_NAMES
            or path.is_symlink()
            or path.suffix.lower() in SKIP_SUFFIXES
            or any(token in lower for token in ("credential", "private_key", "secret_key"))
        ):
            ignored.add(name)
    return ignored


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "candidate_id", "design_id", "closure_level", "completion_time", "trusted",
        "reasons", "drc_pass", "lvs_pass", "lineage_pass", "verification_scope",
        "parasitic_cap_count", "parasitic_res_count", "raw_pex_sha256",
        "source_netlist_sha256", "candidate_dir",
    ]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            normalized = dict(row)
            normalized["reasons"] = ";".join(row.get("reasons", []))
            writer.writerow(normalized)


def _write_checksums(output_dir: Path) -> None:
    entries = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS":
            entries.append(f"{sha256_file(path)}  {path.relative_to(output_dir).as_posix()}")
    (output_dir / "SHA256SUMS").write_text("\n".join(entries) + "\n", encoding="utf-8")


def _make_archive(output_dir: Path) -> Path:
    archive = output_dir.parent / f"{output_dir.name}.tar.gz"
    with archive.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as bundle:
                paths = [output_dir] + sorted(output_dir.rglob("*"))
                for path in paths:
                    arcname = Path(output_dir.name) / path.relative_to(output_dir)
                    info = bundle.gettarinfo(str(path), arcname.as_posix())
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.mtime = 0
                    if info.isfile():
                        with path.open("rb") as stream:
                            bundle.addfile(info, stream)
                    else:
                        bundle.addfile(info)
    return archive


def export_dataset(
    roots: list[Path],
    output_dir: Path,
    since: datetime,
    until: datetime,
    create_archive: bool = True,
) -> dict[str, Any]:
    output_dir = output_dir.expanduser().resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"refusing non-empty output directory: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    trusted_dir = output_dir / "trusted_candidates"
    trusted_dir.mkdir()

    candidates = discover_candidates(roots)
    results = [evaluate_candidate(candidate, since, until) for candidate in candidates]
    selected = [result for result in results if result.in_window]
    trusted = [result for result in selected if result.trusted]
    rejected = [result for result in selected if not result.trusted]

    root_paths = [root.expanduser().resolve() for root in roots]
    for index, result in enumerate(trusted):
        source = Path(result.candidate_dir)
        root_index = next((i for i, root in enumerate(root_paths) if source == root or root in source.parents), 0)
        try:
            relative = source.relative_to(root_paths[root_index])
        except ValueError:
            relative = Path(f"candidate_{index:04d}")
        destination = trusted_dir / f"root_{root_index:02d}" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, destination, ignore=_safe_ignore)

    rows = [result.to_dict() for result in selected]
    trusted_rows = [result.to_dict() for result in trusted]
    rejected_rows = [result.to_dict() for result in rejected]
    duplicate_map: dict[str, list[str]] = {}
    for row in trusted_rows:
        identity = row.get("identity_sha256")
        if identity:
            duplicate_map.setdefault(identity, []).append(row["candidate_dir"])
    duplicate_groups = [
        {"identity_sha256": identity, "candidate_dirs": paths}
        for identity, paths in sorted(duplicate_map.items()) if len(paths) > 1
    ]

    manifest = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "window": {
            "since": since.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "until": until.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
        "roots": [str(root) for root in root_paths],
        "trust_contract": {
            "required": ["sizing_lineage", "drc_pass", "connectivity_lvs_pass", "parseable_raw_pex"],
            "observation_only": ["pm", "reward", "pre_layout_sim", "pvt", "post_layout_performance"],
        },
        "counts": {
            "discovered": len(results), "in_window": len(selected),
            "trusted": len(trusted), "rejected": len(rejected),
        },
        "candidates": rows,
    }
    (output_dir / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    _write_csv(output_dir / "candidates.csv", trusted_rows)
    _write_csv(output_dir / "rejected_candidates.csv", rejected_rows)
    (output_dir / "duplicate_groups.json").write_text(
        json.dumps(duplicate_groups, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (output_dir / "README.md").write_text(
        "# AnalogHarness trusted parasitic export\n\n"
        f"- Window (UTC): `{manifest['window']['since']}` to `{manifest['window']['until']}`\n"
        f"- Trusted: **{len(trusted)}**\n- Rejected: **{len(rejected)}**\n\n"
        "Trusted candidates independently satisfy sizing lineage, DRC PASS, connectivity LVS PASS, "
        "and a parseable raw PEX netlist. PM, reward, pre-layout simulation, PVT, and post-layout "
        "performance are observation-only. `mos_only_projection` is connectivity evidence only, not "
        "property-level or native-passive signoff. Rejected candidates are listed but not copied.\n",
        encoding="utf-8",
    )
    _write_checksums(output_dir)
    archive = _make_archive(output_dir) if create_archive else None
    return {
        "output_dir": str(output_dir),
        "archive_path": str(archive) if archive else None,
        "archive_sha256": sha256_file(archive) if archive else None,
        "discovered_count": len(results),
        "in_window_count": len(selected),
        "trusted_count": len(trusted),
        "rejected_count": len(rejected),
    }


def default_roots(cwd: Path) -> list[Path]:
    roots = []
    direct = cwd / "generated" / "analog_harness"
    if direct.is_dir():
        roots.append(direct)
    references = cwd / "references"
    if references.is_dir():
        roots.extend(path for path in references.glob("*/generated/analog_harness") if path.is_dir())
    senior = Path("/home/ruannai/projects/AnalogHarness/generated/analog_harness")
    if senior.is_dir():
        roots.append(senior)
    unique = []
    for root in roots:
        resolved = root.resolve()
        if resolved not in unique:
            unique.append(resolved)
    return unique


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", action="append", type=Path, help="candidate root; repeatable")
    parser.add_argument("--output", type=Path, required=True, help="new or empty export directory")
    parser.add_argument("--since", help="UTC ISO-8601 lower bound; default is --days ago")
    parser.add_argument("--until", help="UTC ISO-8601 upper bound; default is now")
    parser.add_argument("--days", type=float, default=7.0, help="lookback when --since is omitted")
    parser.add_argument("--no-archive", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    until = parse_time(args.until) if args.until else datetime.now(timezone.utc)
    since = parse_time(args.since) if args.since else until - timedelta(days=args.days)
    if since is None or until is None or since > until:
        raise SystemExit("invalid time window")
    roots = args.root or default_roots(Path.cwd())
    if not roots:
        raise SystemExit("no AnalogHarness roots found; pass --root")
    summary = export_dataset(roots, args.output, since, until, not args.no_archive)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
