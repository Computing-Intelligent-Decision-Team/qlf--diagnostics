"""Live-only run service for the PCS-Harness workflow application."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable


class UnsupportedClosureError(ValueError):
    """The parsed input is not admitted to the verified recording workflow."""


class ActiveRunError(RuntimeError):
    """A recording workflow is already active."""


@dataclass
class _Run:
    run_id: str
    run_root: Path
    events_path: Path
    parse_id: str
    started_at: str
    process: Any
    command: list[str]


class RunService:
    """Validate the verified OTA input and supervise one live subprocess."""

    ALLOWED_SUFFIXES = {".sp", ".spice", ".cir"}
    MAX_NETLIST_BYTES = 2 * 1024 * 1024
    DISPLAY_NAMES = {
        "ota": "运算跨导放大器（OTA）",
        "two_stage_amplifier": "两级放大器",
        "analoggym_amplifier": "AnalogGym 放大器",
        "inverter": "反相器",
        "current_mirror": "电流镜",
    }

    def __init__(
        self,
        *,
        pcs_root: Path,
        runs_root: Path,
        verified_netlist: Path,
        verified_profile: Path,
        boundary_selection: Path | None = None,
        launcher: Callable[..., Any] = subprocess.Popen,
        python_executable: Path = Path(sys.executable),
        poll_interval: float = 0.25,
    ) -> None:
        self.pcs_root = Path(pcs_root).resolve()
        self.runs_root = Path(runs_root).resolve()
        self.verified_netlist = Path(verified_netlist).resolve()
        self.verified_profile = Path(verified_profile).resolve()
        self.boundary_selection = Path(
            boundary_selection or (self.runs_root.parent / "boundary_scan" / "selection.json")
        ).resolve()
        self.launcher = launcher
        self.python_executable = Path(python_executable).resolve()
        self.poll_interval = poll_interval
        self._parses: dict[str, dict[str, Any]] = {}
        self._runs: dict[str, _Run] = {}
        self._lock = threading.Lock()

    def circuit_types(self) -> list[dict[str, Any]]:
        configs_dir = self.pcs_root / "tools/analog_harness/configs"
        by_kind: dict[str, list[str]] = {}
        for config in sorted(configs_dir.glob("*.yaml")):
            fields = self._yaml_header(config)
            kind = fields.get("circuit_kind")
            if kind:
                by_kind.setdefault(kind, []).append(fields.get("design_id", config.stem))
        return [
            {
                "id": kind,
                "name": self.DISPLAY_NAMES.get(kind, kind.replace("_", " ").title()),
                "supported": True,
                "demo_ready": kind == "ota" and self.verified_netlist.is_file() and self.verified_profile.is_file(),
                "design_profiles": sorted(set(profiles)),
            }
            for kind, profiles in sorted(by_kind.items(), key=lambda item: (item[0] != "ota", item[0]))
        ]

    def parse_netlist(self, *, circuit_type: str, filename: str, content: str) -> dict[str, Any]:
        registry = {item["id"]: item for item in self.circuit_types()}
        if circuit_type not in registry:
            raise ValueError(f"unsupported circuit type: {circuit_type}")
        if Path(filename).suffix.casefold() not in self.ALLOWED_SUFFIXES:
            raise ValueError("netlist filename must end in .sp, .spice, or .cir")
        raw = content.encode("utf-8")
        if not raw or len(raw) > self.MAX_NETLIST_BYTES:
            raise ValueError("netlist must be non-empty and at most 2 MiB")
        parsed = self._parse_spice(content)
        input_sha = hashlib.sha256(raw).hexdigest()
        verified_sha = self.sha256(self.verified_netlist)
        profile_sha = self.sha256(self.verified_profile)
        if not registry[circuit_type]["demo_ready"]:
            code = "circuit_type_not_demo_ready"
        elif input_sha != verified_sha:
            code = "verified_input_hash_mismatch"
        elif parsed["top_cell"].casefold() != "ota_core":
            code = "verified_top_cell_mismatch"
        else:
            code = "verified_ota_ready"
        ready = code == "verified_ota_ready"
        parse_id = f"parse_{uuid.uuid4().hex}"
        result = {
            "parse_id": parse_id,
            "circuit_type": circuit_type,
            "filename": Path(filename).name,
            "netlist": {**parsed, "sha256": input_sha, "size_bytes": len(raw)},
            "preflight": {"ready": ready, "code": code},
            "binding": {
                "design_id": "ota_core" if ready else None,
                "profile_path": str(self.verified_profile),
                "profile_sha256": profile_sha,
                "verified_netlist_sha256": verified_sha,
            },
        }
        self._parses[parse_id] = result
        return result

    def start_run(self, parse_id: str) -> dict[str, Any]:
        parsed = self._parses.get(parse_id)
        if parsed is None:
            raise KeyError(f"unknown parse_id: {parse_id}")
        if not parsed["preflight"]["ready"]:
            raise UnsupportedClosureError(parsed["preflight"]["code"])
        with self._lock:
            if any(self._status(run) == "running" for run in self._runs.values()):
                raise ActiveRunError("one PCS-Harness recording run is already active")
            now = datetime.now(timezone.utc)
            run_id = f"run_{now.strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"
            run_root = self.runs_root / run_id
            run_root.mkdir(parents=True, exist_ok=False)
            evidence_dir = run_root / "evidence"
            evidence_dir.mkdir()
            runtime_profile = self._write_runtime_profile(run_root)
            events_path = evidence_dir / "workflow_events.jsonl"
            command = [
                str(self.python_executable),
                "-m",
                "tools.analog_harness.cli",
                "workflow-run",
                "--config",
                str(runtime_profile),
                "--selection",
                str(self.boundary_selection),
                "--run-root",
                str(run_root),
            ]
            env = self._explicit_environment(run_root, run_id, events_path)
            stdout_path = evidence_dir / "harness.stdout.log"
            stderr_path = evidence_dir / "harness.stderr.log"
            with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
                process = self.launcher(
                    command,
                    cwd=str(self.pcs_root),
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=stdout,
                    stderr=stderr,
                    start_new_session=True,
                )
            run = _Run(
                run_id=run_id,
                run_root=run_root,
                events_path=events_path,
                parse_id=parse_id,
                started_at=now.isoformat().replace("+00:00", "Z"),
                process=process,
                command=command,
            )
            self._runs[run_id] = run
            self._write_run_metadata(run)
            return self.run_status(run_id)

    def run_status(self, run_id: str) -> dict[str, Any]:
        run = self._require_run(run_id)
        events = self._events_after(run, 0)
        return {
            "run_id": run.run_id,
            "status": self._status(run),
            "returncode": run.process.poll(),
            "pid": getattr(run.process, "pid", None),
            "started_at": run.started_at,
            "run_root": str(run.run_root),
            "events_path": str(run.events_path),
            "last_sequence": events[-1]["sequence"] if events else 0,
        }

    def event_stream(
        self, run_id: str, *, after_sequence: int = 0, follow: bool = True
    ) -> Iterable[str]:
        run = self._require_run(run_id)
        cursor = after_sequence
        while True:
            events = self._events_after(run, cursor)
            for event in events:
                sequence = event["sequence"]
                yield f"id: {sequence}\nevent: {event['event_type']}\ndata: {json.dumps(event, separators=(',', ':'))}\n\n"
                cursor = sequence
            if not follow or self._status(run) != "running":
                break
            if not events:
                yield ": keep-alive\n\n"
            time.sleep(self.poll_interval)

    def resolve_artifact(self, run_id: str, artifact_id: str) -> Path:
        run = self._require_run(run_id)
        for event in self._events_after(run, 0):
            for ref in event.get("artifact_refs") or []:
                if ref.get("artifact_id") != artifact_id:
                    continue
                relative_path = ref.get("relative_path")
                if not isinstance(relative_path, str):
                    break
                candidate = (run.run_root / relative_path).resolve()
                if not candidate.is_relative_to(run.run_root):
                    raise FileNotFoundError(artifact_id)
                if not candidate.is_file():
                    raise FileNotFoundError(artifact_id)
                if ref.get("sha256") != self.sha256(candidate):
                    raise IOError(f"artifact hash mismatch: {artifact_id}")
                return candidate
        raise FileNotFoundError(artifact_id)

    @staticmethod
    def sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with Path(path).open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _yaml_header(path: Path) -> dict[str, str]:
        fields: dict[str, str] = {}
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            match = re.match(r"^(design_id|top_cell|circuit_kind):\s*([^#]+?)\s*$", line)
            if match:
                fields[match.group(1)] = match.group(2).strip(' "\'')
        return fields

    @staticmethod
    def _parse_spice(content: str) -> dict[str, Any]:
        match = re.search(r"(?im)^\s*\.?subckt\s+(\S+)\s*(.*?)\s*$", content)
        if not match:
            raise ValueError("SPICE netlist has no .subckt/subckt declaration")
        top_cell = match.group(1)
        ports = match.group(2).split()
        device_counts: dict[str, int] = {}
        in_top = False
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if re.match(r"(?i)^\.?subckt\s+", line):
                in_top = line.split()[1].casefold() == top_cell.casefold()
                continue
            if in_top and re.match(r"(?i)^\.?ends(?:\s|$)", line):
                break
            if not in_top or not line or line.startswith(("*", ".", "+")):
                continue
            designator = line[0].upper()
            if designator.isalpha():
                device_counts[designator] = device_counts.get(designator, 0) + 1
        return {"top_cell": top_cell, "ports": ports, "device_counts": device_counts}

    def _write_runtime_profile(self, run_root: Path) -> Path:
        text = self.verified_profile.read_text(encoding="utf-8")
        replacement = f"\\g<1>{run_root}"
        updated, count = re.subn(r"(?m)^(\s*runs_dir:\s*).+$", replacement, text, count=1)
        if count == 0:
            updated += f"\n# API run-root override\nworkflow_run_root: {run_root}\n"
        updated += (
            "\n# Frozen source-profile provenance\n"
            f'workflow_source_profile_sha256: "{self.sha256(self.verified_profile)}"\n'
        )
        path = run_root / "runtime_profile.yaml"
        path.write_text(updated, encoding="utf-8")
        return path

    def _explicit_environment(self, run_root: Path, run_id: str, events_path: Path) -> dict[str, str]:
        allowed = ("PATH", "LD_LIBRARY_PATH", "PYTHONPATH", "SKYWATER130_HOME", "PDK_ROOT", "MAGIC_RCFILE")
        env = {key: os.environ[key] for key in allowed if key in os.environ}
        env.update(
            {
                "PYTHONUNBUFFERED": "1",
                "PYTHONHASHSEED": "0",
                "PCS_WORKFLOW_RUN_ID": run_id,
                "PCS_WORKFLOW_RUN_ROOT": str(run_root),
                "PCS_WORKFLOW_EVENTS_PATH": str(events_path),
                "ANALOG_HARNESS_RUNS_DIR": str(run_root),
            }
        )
        return env

    def _events_after(self, run: _Run, sequence: int) -> list[dict[str, Any]]:
        if sequence < 0:
            raise ValueError("event cursor must be non-negative")
        if not run.events_path.is_file():
            return []
        events: list[dict[str, Any]] = []
        previous = 0
        data = run.events_path.read_bytes()
        lines = data.splitlines(keepends=True)
        for index, raw_line in enumerate(lines):
            if not raw_line.strip():
                continue
            try:
                event = json.loads(raw_line)
            except json.JSONDecodeError:
                if index == len(lines) - 1 and not raw_line.endswith(b"\n"):
                    break
                raise
            event_sequence = event.get("sequence")
            if not isinstance(event_sequence, int) or event_sequence != previous + 1:
                raise ValueError(f"non-contiguous workflow event sequence at {event_sequence!r}")
            if event.get("run_id") != run.run_id:
                raise ValueError("workflow event run_id mismatch")
            previous = event_sequence
            if event_sequence > sequence:
                events.append(event)
        return events

    def _status(self, run: _Run) -> str:
        returncode = run.process.poll()
        if returncode is None:
            return "running"
        return "completed" if returncode == 0 else "failed"

    def _require_run(self, run_id: str) -> _Run:
        try:
            return self._runs[run_id]
        except KeyError as exc:
            raise KeyError(f"unknown run_id: {run_id}") from exc

    def _write_run_metadata(self, run: _Run) -> None:
        payload = {
            "run_id": run.run_id,
            "parse_id": run.parse_id,
            "started_at": run.started_at,
            "command": run.command,
            "events_path": str(run.events_path),
        }
        (run.run_root / "run.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
