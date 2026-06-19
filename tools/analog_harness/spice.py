"""SPICE netlist compilation for sizing candidates."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from .config import HarnessConfig
from .legalizer import SizingLegalizer
from .models import CompiledCandidate


PARAM_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


def format_spice_value(value: float | int, unit: str = "") -> str:
    if isinstance(value, int) or float(value).is_integer():
        rendered = str(int(round(float(value))))
    else:
        rendered = f"{float(value):.8g}"
    return f"{rendered}{unit}"


class SpiceCandidateCompiler:
    """Writes candidate-specific netlist/config inputs for MAGICAL/Sky130."""

    def __init__(self, config: HarnessConfig, legalizer: SizingLegalizer):
        self.config = config
        self.legalizer = legalizer

    def compile(
        self,
        candidate_id: str,
        values: dict[str, float | int],
        action_normalized: list[float],
    ) -> CompiledCandidate:
        candidate_dir = self.config.run_dir / candidate_id
        case_dir = candidate_dir / "case"
        out_dir = candidate_dir / "layout"
        artifacts_dir = candidate_dir / "artifacts"
        case_dir.mkdir(parents=True, exist_ok=True)
        out_dir.mkdir(parents=True, exist_ok=True)
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        assignments = self.legalizer.device_assignments(values)
        param_units = self.legalizer.param_units()
        netlist_path = case_dir / f"{self.config.top_cell}_{candidate_id}.sp"
        config_path = case_dir / f"{self.config.design_id}_{candidate_id}.json"

        source_text = self.config.source_netlist.read_text(encoding="utf-8")
        netlist_path.write_text(
            rewrite_instance_params(source_text, assignments, param_units),
            encoding="utf-8",
        )
        self._write_candidate_config(config_path, netlist_path)
        return CompiledCandidate(
            candidate_id=candidate_id,
            candidate_dir=candidate_dir,
            case_dir=case_dir,
            out_dir=out_dir,
            netlist_path=netlist_path,
            config_path=config_path,
            action_normalized=list(action_normalized),
            values=dict(values),
            assignments=assignments,
        )

    def _write_candidate_config(self, output: Path, netlist_path: Path) -> None:
        source_config = self.config.source_config
        data = json.loads(source_config.read_text(encoding="utf-8"))
        data["hspice_netlist"] = netlist_path.name
        data["resultDir"] = "./"
        for key in ("techfile", "simple_tech_file", "lef"):
            if key in data and data[key]:
                resolved = _resolve_source_config_path(source_config, str(data[key]))
                data[key] = os.path.relpath(resolved, output.parent).replace(os.sep, "/")
        data.setdefault("connectivityLvsProjection", "mos_only")
        output.write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")


def _resolve_source_config_path(config_path: Path, raw_value: str) -> Path:
    path = Path(raw_value)
    if path.is_absolute():
        return path.resolve()
    return (config_path.parent / path).resolve()


def rewrite_instance_params(
    netlist_text: str,
    assignments: dict[str, dict[str, Any]],
    param_units: dict[tuple[str, str], str] | None = None,
) -> str:
    units = param_units or {}
    lines: list[str] = []
    for line in netlist_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("*"):
            lines.append(line)
            continue
        tokens = stripped.split()
        instance = tokens[0].lower()
        if instance not in assignments:
            lines.append(line)
            continue
        updated = _rewrite_tokens(tokens, instance, assignments[instance], units)
        prefix = line[: len(line) - len(line.lstrip())]
        lines.append(prefix + " ".join(updated))
    return "\n".join(lines) + "\n"


def _rewrite_tokens(
    tokens: list[str],
    instance: str,
    values: dict[str, Any],
    units: dict[tuple[str, str], str],
) -> list[str]:
    remaining = {key.lower(): value for key, value in values.items()}
    rendered: list[str] = []
    for token in tokens:
        match = PARAM_RE.match(token)
        if not match:
            rendered.append(token)
            continue
        param = match.group(1).lower()
        if param in remaining:
            value = remaining.pop(param)
            rendered.append(f"{param}={format_spice_value(value, units.get((instance, param), ''))}")
        else:
            rendered.append(token)
    for param, value in remaining.items():
        rendered.append(f"{param}={format_spice_value(value, units.get((instance, param), ''))}")
    return rendered
