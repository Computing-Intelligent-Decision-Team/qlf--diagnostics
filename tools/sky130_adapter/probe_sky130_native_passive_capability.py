#!/usr/bin/env python3
"""Probe whether source passives can be recognized as native Sky130 LVS devices.

This is a static PDK/source-netlist capability check.  It intentionally does
not claim that an existing GDS passes native passive LVS; it reports whether
the source passive model names are directly supported by the local Magic and
Netgen Sky130 setup files, and which native Sky130 primitives are plausible
retargets when they are not.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from prepare_lvs_netlists import SourcePassive, parse_source_passives  # noqa: E402


MAGIC_DEVICE_RE = re.compile(r"^\s*device\s+\S+\s+(?P<model>sky130_fd_pr__[A-Za-z0-9_]+)\b")
NETGEN_DEVICE_RE = re.compile(r"^\s*lappend\s+devices\s+(?P<model>[A-Za-z0-9_]+)\b")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe native Sky130 passive model support for a source netlist."
    )
    parser.add_argument("--source-netlist", type=Path, required=True)
    parser.add_argument("--sky130a", required=True, help="sky130A PDK root. May be a WSL POSIX path.")
    parser.add_argument("--repo-root", type=Path, help="Repository root used to check MAGICAL device_generator sources.")
    parser.add_argument("--wsl-distro", help="WSL distro to use when --sky130a is a POSIX path on Windows.")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    parser.add_argument(
        "--require-native-source-support",
        action="store_true",
        help="Exit non-zero when current source models are not directly supported by Magic and Netgen.",
    )
    return parser.parse_args()


def _join_pdk_path(sky130a: str, suffix: str) -> str:
    normalized = sky130a.replace("\\", "/").rstrip("/")
    if normalized.startswith("/") and not re.match(r"^[A-Za-z]:/", normalized):
        return f"{normalized}/{suffix}"
    return str(Path(sky130a) / Path(*suffix.split("/")))


def _read_text(path_text: str, *, wsl_distro: str | None = None) -> tuple[str | None, str | None]:
    path = Path(path_text)
    if path.is_file():
        return path.read_text(encoding="utf-8", errors="replace"), None
    normalized = path_text.replace("\\", "/")
    if wsl_distro and normalized.startswith("/") and shutil.which("wsl"):
        cmd = ["wsl", "-d", wsl_distro, "--", "cat", normalized]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode == 0:
            return result.stdout, None
        return None, (result.stderr or result.stdout or "").strip()
    return None, f"file not found: {path_text}"


def parse_magic_supported_models(text: str) -> set[str]:
    models: set[str] = set()
    for line in text.splitlines():
        match = MAGIC_DEVICE_RE.match(line)
        if match:
            models.add(match.group("model"))
    return models


def parse_netgen_supported_models(text: str) -> set[str]:
    models: set[str] = set()
    for line in text.splitlines():
        match = NETGEN_DEVICE_RE.match(line)
        if match:
            model = match.group("model")
            if model.startswith("sky130_fd_pr__"):
                models.add(model)
    return models


def passive_kind(model: str) -> str:
    lowered = model.lower()
    if lowered.startswith("r") or "res" in lowered:
        return "resistor"
    if lowered.startswith("c") or "cap" in lowered:
        return "capacitor"
    return "unknown"


def native_passive_model_kind(model: str) -> str:
    lowered = model.lower()
    if "__res_" in lowered:
        return "resistor"
    if "__cap_" in lowered:
        return "capacitor"
    return "unknown"


def native_alternatives(kind: str, supported_models: set[str]) -> list[str]:
    if kind == "resistor":
        preferred = [
            "sky130_fd_pr__res_xhigh_po",
            "sky130_fd_pr__res_xhigh_po_0p35",
            "sky130_fd_pr__res_xhigh_po_0p69",
            "sky130_fd_pr__res_xhigh_po_1p41",
            "sky130_fd_pr__res_xhigh_po_2p85",
            "sky130_fd_pr__res_xhigh_po_5p73",
            "sky130_fd_pr__res_generic_po",
        ]
        return [model for model in preferred if model in supported_models] + [
            model
            for model in sorted(supported_models)
            if "res_" in model and model not in preferred
        ]
    if kind == "capacitor":
        preferred = [
            "sky130_fd_pr__cap_mim_m3_1",
            "sky130_fd_pr__cap_mim_m3_2",
        ]
        return [model for model in preferred if model in supported_models] + [
            model
            for model in sorted(supported_models)
            if "cap_" in model and model not in preferred
        ]
    return []


def _device_generation_status(repo_root: Path | None) -> dict[str, Any]:
    if repo_root is None:
        return {
            "checked": False,
            "can_patch_current_generator_source": None,
            "missing_files": [],
        }
    candidates = [
        (
            repo_root / "device_generation" / "device_generation" / "Resistor.py",
            repo_root / "device_generation" / "device_generation" / "Capacitor.py",
        ),
        (
            repo_root / "device_generation" / "Resistor.py",
            repo_root / "device_generation" / "Capacitor.py",
        ),
    ]
    required = next(
        (list(group) for group in candidates if all(path.is_file() for path in group)),
        list(candidates[0]),
    )
    missing = [str(path) for path in required if not path.is_file()]
    return {
        "checked": True,
        "can_patch_current_generator_source": not missing,
        "missing_files": missing,
        "recognized_layout_generator_files": [str(path) for path in required if path.is_file()],
    }


def build_summary(
    *,
    source_netlist: Path,
    sky130a: str,
    repo_root: Path | None = None,
    wsl_distro: str | None = None,
) -> dict[str, Any]:
    source_text = source_netlist.read_text(encoding="utf-8", errors="replace")
    source_passives = parse_source_passives(source_text.splitlines())

    magic_tech = _join_pdk_path(sky130a, "libs.tech/magic/sky130A.tech")
    netgen_setup = _join_pdk_path(sky130a, "libs.tech/netgen/sky130A_setup.tcl")
    magic_text, magic_error = _read_text(magic_tech, wsl_distro=wsl_distro)
    netgen_text, netgen_error = _read_text(netgen_setup, wsl_distro=wsl_distro)

    magic_models = parse_magic_supported_models(magic_text or "")
    netgen_models = parse_netgen_supported_models(netgen_text or "")
    magic_passive_models = {
        model for model in magic_models if native_passive_model_kind(model) in {"resistor", "capacitor"}
    }
    netgen_passive_models = {
        model for model in netgen_models if native_passive_model_kind(model) in {"resistor", "capacitor"}
    }
    supported_native_models = {
        model
        for model in magic_passive_models & netgen_passive_models
        if native_passive_model_kind(model) in {"resistor", "capacitor"}
    }
    supported_native_lower = {model.lower() for model in supported_native_models}

    source_entries: list[dict[str, Any]] = []
    model_retarget: dict[str, list[str]] = {}
    for passive in source_passives:
        kind = passive_kind(passive.model)
        direct = passive.model.lower() in supported_native_lower
        alternatives = [] if direct else native_alternatives(kind, supported_native_models)
        if not direct:
            model_retarget.setdefault(passive.model, alternatives)
        source_entries.append(
            {
                "instance": passive.instance,
                "model": passive.model,
                "terminals": list(passive.terminals),
                "kind": kind,
                "direct_magic_and_netgen_support": direct,
                "native_retarget_candidates": alternatives,
                "status": "native_source_model_supported" if direct else "source_model_requires_native_retarget",
            }
        )

    unique_source_models = sorted({passive.model for passive in source_passives})
    unsupported = sorted(
        {
            passive.model
            for passive in source_passives
            if passive.model.lower() not in supported_native_lower
        }
    )
    all_unsupported_have_retarget = all(bool(model_retarget.get(model)) for model in unsupported)
    source_native_pass = not unsupported and not magic_error and not netgen_error

    return {
        "schema_version": "sky130_native_passive_capability.v1",
        "source_netlist": str(source_netlist),
        "sky130a": sky130a,
        "magic_tech": magic_tech,
        "netgen_setup": netgen_setup,
        "magic_tech_read_error": magic_error,
        "netgen_setup_read_error": netgen_error,
        "source_passive_count": len(source_passives),
        "source_passive_models": unique_source_models,
        "source_passives": source_entries,
        "magic_native_passive_model_count": len(magic_passive_models),
        "netgen_native_passive_model_count": len(netgen_passive_models),
        "supported_native_passive_models": sorted(supported_native_models),
        "source_model_native_status": "pass" if source_native_pass else "fail",
        "direct_source_model_support": source_native_pass,
        "unsupported_source_models": unsupported,
        "native_retarget_available": bool(unsupported) and all_unsupported_have_retarget,
        "native_retarget_map": model_retarget,
        "native_retarget_requires_source_model_change": bool(unsupported),
        "native_retarget_requires_geometry_replacement": bool(unsupported),
        "native_retarget_not_layer_remap": bool(unsupported),
        "can_fix_current_gds_by_layer_remap_only": False if unsupported else None,
        "recommended_action": (
            "retarget source models and generated passive geometry to supported Sky130 primitives"
            if unsupported and all_unsupported_have_retarget
            else "current source passive models are directly supported"
            if source_native_pass
            else "install or point to a Sky130 PDK with Magic and Netgen passive support"
        ),
        "device_generation_source_status": _device_generation_status(repo_root),
    }


def write_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Sky130 Native Passive Capability Probe",
        "",
        f"- Source netlist: `{summary.get('source_netlist')}`",
        f"- Sky130A: `{summary.get('sky130a')}`",
        f"- Source passive models: `{summary.get('source_passive_models')}`",
        f"- Source model native status: `{summary.get('source_model_native_status')}`",
        f"- Direct source model support: `{summary.get('direct_source_model_support')}`",
        f"- Unsupported source models: `{summary.get('unsupported_source_models')}`",
        f"- Native retarget available: `{summary.get('native_retarget_available')}`",
        f"- Requires source model change: `{summary.get('native_retarget_requires_source_model_change')}`",
        f"- Requires geometry replacement: `{summary.get('native_retarget_requires_geometry_replacement')}`",
        f"- Layer remap alone sufficient: `{summary.get('can_fix_current_gds_by_layer_remap_only')}`",
        f"- Recommended action: `{summary.get('recommended_action')}`",
        "",
        "## Source Passives",
        "",
        "| Instance | Model | Kind | Direct Native Support | Retarget Candidates |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in summary.get("source_passives", []):
        candidates = ", ".join(item.get("native_retarget_candidates") or [])
        lines.append(
            "| {instance} | {model} | {kind} | {direct} | {candidates} |".format(
                instance=item.get("instance"),
                model=item.get("model"),
                kind=item.get("kind"),
                direct=item.get("direct_magic_and_netgen_support"),
                candidates=candidates or "-",
            )
        )
    lines.extend(
        [
            "",
            "## Native Primitive Support",
            "",
            f"- Magic supported passive models: `{summary.get('magic_native_passive_model_count')}`",
            f"- Netgen supported passive models: `{summary.get('netgen_native_passive_model_count')}`",
            f"- Intersection used for retargeting: `{summary.get('supported_native_passive_models')}`",
            "",
            "## Generator Source Check",
            "",
            f"- Status: `{summary.get('device_generation_source_status')}`",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    summary = build_summary(
        source_netlist=args.source_netlist,
        sky130a=args.sky130a,
        repo_root=args.repo_root,
        wsl_distro=args.wsl_distro,
    )
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(args.report, summary)
    print(f"source_model_native_status={summary['source_model_native_status']}")
    print(f"native_retarget_available={summary['native_retarget_available']}")
    if args.require_native_source_support and summary["source_model_native_status"] != "pass":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
