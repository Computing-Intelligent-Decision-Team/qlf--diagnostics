#!/usr/bin/env python3
"""Generate the opt-in Anaroute GDS export map for Native Sky130 Export Phase 1.5."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - depends on deployment environment.
    yaml = None


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = REPO_ROOT / "generated/sky130PDK_trial/sky130_gds_export_map.yaml"
DEFAULT_OUTPUT = REPO_ROOT / "generated/sky130PDK_native_trial/sky130_anaroute_gds_export.map"
DEFAULT_REPORT = REPO_ROOT / "docs/sky130_adapter/native_sky130_gds_export_map.md"

PHASE15_LAYERS = [
    "NW",
    "OD",
    "PO",
    "PP",
    "NP",
    "CO",
    "M1",
    "VIA1",
    "M2",
    "VIA2",
    "M3",
    "VIA3",
    "M4",
    "VIA4",
    "M5",
    "VIA5",
    "M6",
]


@dataclass(frozen=True)
class ExportMapRow:
    magical_layer: str
    input_layer: int
    input_datatype: int
    output_layer: int
    output_datatype: int
    name: str
    risk: str


def parse_int(value: Any, field: str, layer_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{layer_name}: {field} is not an integer: {value!r}") from exc


def load_rows(input_yaml: Path) -> list[ExportMapRow]:
    if yaml is None:
        raise RuntimeError("PyYAML is required to read the Sky130 export map YAML")
    data = yaml.safe_load(input_yaml.read_text(encoding="utf-8")) or {}
    by_name = {entry.get("magical_layer"): entry for entry in data.get("layers", [])}

    rows: list[ExportMapRow] = []
    missing: list[str] = []
    skipped: list[str] = []
    for layer_name in PHASE15_LAYERS:
        entry = by_name.get(layer_name)
        if entry is None:
            missing.append(layer_name)
            continue
        if entry.get("status") != "confirmed":
            skipped.append(f"{layer_name}: status={entry.get('status')}")
            continue
        rows.append(
            ExportMapRow(
                magical_layer=layer_name,
                input_layer=parse_int(entry.get("magical_internal_number"), "magical_internal_number", layer_name),
                input_datatype=0,
                output_layer=parse_int(entry.get("sky130_gds_layer"), "sky130_gds_layer", layer_name),
                output_datatype=parse_int(entry.get("sky130_datatype"), "sky130_datatype", layer_name),
                name=str(entry.get("sky130_layer_name") or layer_name),
                risk=str(entry.get("risk") or ""),
            )
        )

    if missing:
        raise ValueError(f"Missing required Phase 1.5 layers in export map: {', '.join(missing)}")
    if skipped:
        raise ValueError(f"Required Phase 1.5 layers are not confirmed: {', '.join(skipped)}")
    return rows


def write_map(path: Path, rows: list[ExportMapRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# MAGICAL Native Sky130 Export Phase 1.5",
        "# input_layer input_datatype output_layer output_datatype name",
    ]
    for row in rows:
        lines.append(
            f"{row.input_layer} {row.input_datatype} "
            f"{row.output_layer} {row.output_datatype} {row.name}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_report(path: Path, input_yaml: Path, output_map: Path, rows: list[ExportMapRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Native Sky130 GDS Export Map",
        "",
        "## Summary",
        "",
        f"- Source YAML: `{input_yaml}`",
        f"- Anaroute map: `{output_map}`",
        "- Scope: confirmed drawing/well/implant/contact/via mappings only.",
        "- Phase 1.5 adds NW/PP/NP to remove known Magic GDS-read unknown layers from the native inverter trial.",
        "- Excluded in Phase 1.5: STDPIN, label layers, pin-purpose layers, markers without confirmed need, and TBD layers.",
        "",
        "## Export Rows",
        "",
        "| MAGICAL layer | input layer | input datatype | Sky130 layer/datatype | Sky130 name |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row.magical_layer} | {row.input_layer} | {row.input_datatype} | "
            f"{row.output_layer}/{row.output_datatype} | {row.name} |"
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- The C++ writer reads this file only when `MAGICAL_GDS_EXPORT_MAP` is set.",
            "- Rows not listed here remain unchanged and are reported by the writer-side export-map report.",
            "- Text records are intentionally left unchanged in Phase 1 because native pin label and pin-purpose export is a separate step.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-yaml", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-map", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        input_yaml = args.input_yaml.resolve()
        output_map = args.output_map.resolve()
        report = args.report.resolve()
        if not input_yaml.is_file():
            raise FileNotFoundError(input_yaml)
        rows = load_rows(input_yaml)
        write_map(output_map, rows)
        write_report(report, input_yaml, output_map, rows)
        print(f"Wrote Anaroute GDS export map: {output_map}")
        print(f"Wrote report: {report}")
        print(f"Rows: {len(rows)}")
        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
