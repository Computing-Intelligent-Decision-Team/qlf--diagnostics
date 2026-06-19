#!/usr/bin/env python3
"""Prepare a same-cell-name Sky130 native capacitor replacement candidate.

The output is a replacement *candidate* for a MAGICAL ``cfmom_2t`` cell.  It
generates a Sky130 MIM capacitor gencell using the original passive cell name
and approximate original bbox dimensions, then records the remaining bridge
and top-level merge work as explicit gates.  It does not overwrite the current
GDS.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare a native Sky130 cap replacement candidate.")
    parser.add_argument("--identity-summary", type=Path, required=True)
    parser.add_argument("--source-gds-structure-json", type=Path, required=True)
    parser.add_argument("--source-instance", default="xc0")
    parser.add_argument("--sky130a", required=True)
    parser.add_argument("--wsl-distro")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_identity_instance(identity: dict[str, Any], source_instance: str) -> dict[str, Any]:
    for item in identity.get("instances", []):
        if isinstance(item, dict) and item.get("source_instance") == source_instance:
            return item
    raise ValueError(f"source instance not found in identity summary: {source_instance}")


def source_cell_bbox(structure: dict[str, Any]) -> list[int]:
    cells = structure.get("top_gds", {}).get("cells", [])
    if not cells or not isinstance(cells[0], dict) or not cells[0].get("bbox"):
        raise ValueError("source GDS structure summary does not contain a top cell bbox")
    return [int(value) for value in cells[0]["bbox"]]


def cap_dimensions_from_bbox(bbox: list[int]) -> dict[str, float]:
    width_um = max(0.0, (bbox[2] - bbox[0]) / 1000.0)
    height_um = max(0.0, (bbox[3] - bbox[1]) / 1000.0)
    # Empirical offsets from the Sky130 MIM gencell probe: a w=10/l=10 cap
    # produced a 12.16um x 10.40um bbox.  Keep dimensions inside PDK limits.
    cap_w = min(30.0, max(2.0, width_um - 2.16))
    cap_l = min(30.0, max(2.0, height_um - 0.40))
    return {
        "source_bbox_width_um": width_um,
        "source_bbox_height_um": height_um,
        "replacement_cap_width_um": round(cap_w, 4),
        "replacement_cap_length_um": round(cap_l, 4),
    }


def run_gencell_probe(
    *,
    sky130a: str,
    wsl_distro: str | None,
    out_dir: Path,
    cell_name: str,
    width_um: float,
    length_um: float,
) -> dict[str, Any]:
    summary_json = out_dir / "native_cap_replacement_gencell_summary.json"
    report = out_dir / "native_cap_replacement_gencell_report.md"
    script = Path(__file__).with_name("probe_sky130_native_cap_gencell.py")
    cmd = [
        sys.executable,
        str(script),
        "--sky130a",
        sky130a,
        "--out-dir",
        str(out_dir),
        "--summary-json",
        str(summary_json),
        "--report",
        str(report),
        "--cell-name",
        cell_name,
        "--width-um",
        str(width_um),
        "--length-um",
        str(length_um),
    ]
    if wsl_distro:
        cmd.extend(["--wsl-distro", wsl_distro])
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    summary = load_json(summary_json) if summary_json.is_file() else {}
    return {
        "returncode": result.returncode,
        "stdout": result.stdout or "",
        "summary_json": str(summary_json),
        "report": str(report),
        "summary": summary,
    }


def build_summary(
    *,
    identity_summary: Path,
    source_gds_structure_json: Path,
    source_instance: str,
    sky130a: str,
    wsl_distro: str | None,
    out_dir: Path,
) -> dict[str, Any]:
    identity = load_json(identity_summary)
    structure = load_json(source_gds_structure_json)
    instance = find_identity_instance(identity, source_instance)
    bbox = source_cell_bbox(structure)
    dims = cap_dimensions_from_bbox(bbox)
    cell_name = str(instance.get("magical_instance") or source_instance)
    out_dir.mkdir(parents=True, exist_ok=True)
    gencell = run_gencell_probe(
        sky130a=sky130a,
        wsl_distro=wsl_distro,
        out_dir=out_dir,
        cell_name=cell_name,
        width_um=float(dims["replacement_cap_width_um"]),
        length_um=float(dims["replacement_cap_length_um"]),
    )
    gencell_summary = gencell.get("summary", {})
    terminals = [
        {
            "terminal": terminal.get("terminal"),
            "local_box": terminal.get("local_box"),
            "global_box": terminal.get("global_box"),
            "match_status": terminal.get("match_status"),
        }
        for terminal in instance.get("terminals", [])
        if isinstance(terminal, dict)
    ]
    return {
        "schema_version": "sky130_native_cap_replacement_candidate.v1",
        "status": "replacement_candidate_prepared"
        if gencell_summary.get("native_cap_gencell_extraction_status") == "pass"
        else "replacement_candidate_failed",
        "source_instance": source_instance,
        "source_model": instance.get("model"),
        "replacement_cell_name": cell_name,
        "source_cell_bbox": bbox,
        **dims,
        "source_terminals": terminals,
        "native_cap_gencell_extraction_status": gencell_summary.get(
            "native_cap_gencell_extraction_status"
        ),
        "native_cap_gencell_model": gencell_summary.get("model"),
        "native_cap_gencell_devices": gencell_summary.get("native_capacitor_devices"),
        "replacement_gds": gencell_summary.get("gds"),
        "replacement_spice": gencell_summary.get("spice"),
        "replacement_magic_log": gencell_summary.get("log"),
        "replacement_gencell_summary_json": gencell.get("summary_json"),
        "replacement_gencell_report": gencell.get("report"),
        "terminal_bridge_status": "not_implemented",
        "top_gds_merge_status": "not_implemented",
        "full_native_capacitor_lvs_ready": False,
        "remaining_gates": [
            "connect original MAGICAL xc0 route-pin boxes to generated MIM C1/C2 terminals",
            "replace xc0 cell in the full routed Sky130 GDS without disturbing MOS/resistor routing",
            "rerun Magic extraction and prove xc0 appears as sky130_fd_pr__cap_* in the full top netlist",
        ],
    }


def write_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Sky130 Native Capacitor Replacement Candidate",
        "",
        f"- Status: `{summary.get('status')}`",
        f"- Source instance: `{summary.get('source_instance')}`",
        f"- Source model: `{summary.get('source_model')}`",
        f"- Replacement cell: `{summary.get('replacement_cell_name')}`",
        f"- Native cap extraction: `{summary.get('native_cap_gencell_extraction_status')}`",
        f"- Replacement GDS: `{summary.get('replacement_gds')}`",
        f"- Replacement SPICE: `{summary.get('replacement_spice')}`",
        f"- Terminal bridge status: `{summary.get('terminal_bridge_status')}`",
        f"- Top GDS merge status: `{summary.get('top_gds_merge_status')}`",
        f"- Full native capacitor LVS ready: `{summary.get('full_native_capacitor_lvs_ready')}`",
        "",
        "## Remaining Gates",
        "",
    ]
    for gate in summary.get("remaining_gates", []):
        lines.append(f"- {gate}")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    summary = build_summary(
        identity_summary=args.identity_summary,
        source_gds_structure_json=args.source_gds_structure_json,
        source_instance=args.source_instance,
        sky130a=args.sky130a,
        wsl_distro=args.wsl_distro,
        out_dir=args.out_dir,
    )
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(args.report, summary)
    print(f"native_cap_replacement_status={summary['status']}")
    print(f"full_native_capacitor_lvs_ready={summary['full_native_capacitor_lvs_ready']}")
    return 0 if summary["status"] == "replacement_candidate_prepared" else 2


if __name__ == "__main__":
    raise SystemExit(main())
