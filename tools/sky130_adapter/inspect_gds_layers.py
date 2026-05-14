#!/usr/bin/env python3
"""Inspect GDS layer/datatype pairs from MAGICAL trial output.

The parser intentionally reads only the GDSII records needed for layer summary:
LAYER plus DATATYPE/TEXTTYPE/NODETYPE/BOXTYPE. This keeps the script usable in
minimal environments where gdspy/gdstk are not installed.
"""

from __future__ import annotations

import argparse
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - depends on local environment.
    yaml = None


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GDS = REPO_ROOT / "examples/inverter_sky130_try/inverter_core.route.gds"
DEFAULT_EXPORT_MAP = REPO_ROOT / "generated/sky130PDK_trial/sky130_gds_export_map.yaml"
DEFAULT_REPORT = REPO_ROOT / "docs/sky130_adapter/trial_gds_layer_report.md"

ELEMENT_RECORDS = {
    0x08: "BOUNDARY",
    0x09: "PATH",
    0x0A: "SREF",
    0x0B: "AREF",
    0x0C: "TEXT",
    0x15: "NODE",
    0x2D: "BOX",
}

LAYER_RECORD = 0x0D
DATATYPE_RECORDS = {
    0x0E: "DATATYPE",
    0x16: "TEXTTYPE",
    0x2A: "NODETYPE",
    0x2E: "BOXTYPE",
}
ENDEL_RECORD = 0x11


@dataclass(frozen=True)
class GdsLayerUse:
    layer: int
    datatype: int
    element_type: str
    datatype_record: str


def read_int2(payload: bytes) -> int:
    if len(payload) < 2:
        raise ValueError("GDS int2 record payload is too short")
    return struct.unpack(">h", payload[:2])[0]


def inspect_gds(path: Path) -> set[GdsLayerUse]:
    data = path.read_bytes()
    offset = 0
    current_element = ""
    current_layer: int | None = None
    uses: set[GdsLayerUse] = set()

    while offset < len(data):
        if offset + 4 > len(data):
            raise ValueError(f"Truncated GDS record header at byte {offset}")
        record_len, record_type, _data_type = struct.unpack(">HBB", data[offset : offset + 4])
        if record_len < 4:
            raise ValueError(f"Invalid GDS record length {record_len} at byte {offset}")
        payload = data[offset + 4 : offset + record_len]

        if record_type in ELEMENT_RECORDS:
            current_element = ELEMENT_RECORDS[record_type]
            current_layer = None
        elif record_type == LAYER_RECORD:
            current_layer = read_int2(payload)
        elif record_type in DATATYPE_RECORDS and current_layer is not None:
            uses.add(
                GdsLayerUse(
                    layer=current_layer,
                    datatype=read_int2(payload),
                    element_type=current_element or "UNKNOWN",
                    datatype_record=DATATYPE_RECORDS[record_type],
                )
            )
        elif record_type == ENDEL_RECORD:
            current_element = ""
            current_layer = None

        offset += record_len

    return uses


def load_export_map(path: Path) -> dict[int, list[dict[str, Any]]]:
    if not path.is_file() or yaml is None:
        return {}
    with path.open("r", encoding="utf-8") as fp:
        data = yaml.safe_load(fp) or {}

    by_internal: dict[int, list[dict[str, Any]]] = {}
    for entry in data.get("layers", []):
        internal = entry.get("magical_internal_number")
        if isinstance(internal, int):
            by_internal.setdefault(internal, []).append(entry)
    return by_internal


def format_mapping(entries: list[dict[str, Any]]) -> str:
    if not entries:
        return "not listed in export map"
    parts: list[str] = []
    for entry in entries:
        if entry.get("status") == "confirmed":
            parts.append(
                f"{entry.get('magical_layer')} -> {entry.get('sky130_layer_name')} "
                f"{entry.get('sky130_gds_layer')}/{entry.get('sky130_datatype')}"
            )
        else:
            parts.append(f"{entry.get('magical_layer')} -> TBD")
    return "; ".join(parts)


def status_for(entries: list[dict[str, Any]]) -> str:
    if not entries:
        return "not_mapped"
    if any(entry.get("status") == "confirmed" for entry in entries):
        return "confirmed_target"
    return "tbd"


def generate_report(
    gds_path: Path,
    export_map_path: Path,
    uses: set[GdsLayerUse],
    export_by_internal: dict[int, list[dict[str, Any]]],
) -> str:
    sorted_uses = sorted(uses, key=lambda item: (item.layer, item.datatype, item.element_type))
    confirmed_count = sum(
        1 for use in sorted_uses if status_for(export_by_internal.get(use.layer, [])) == "confirmed_target"
    )
    tbd_count = sum(1 for use in sorted_uses if status_for(export_by_internal.get(use.layer, [])) == "tbd")
    unmapped_count = sum(
        1 for use in sorted_uses if status_for(export_by_internal.get(use.layer, [])) == "not_mapped"
    )

    lines = [
        "# Trial GDS Layer Report",
        "",
        "## Summary",
        "",
        f"- GDS file: `{gds_path}`",
        f"- Export map: `{export_map_path}`",
        f"- Unique layer/datatype pairs found: {len(sorted_uses)}",
        f"- Pairs with confirmed Sky130 export target: {confirmed_count}",
        f"- Pairs whose MAGICAL layer is still TBD: {tbd_count}",
        f"- Pairs not listed in export map: {unmapped_count}",
        "",
        "The current `generated/sky130PDK_trial` keeps MAGICAL/mock internal layer numbers in the PDK files so MAGICAL can parse them. Therefore the layer/datatype pairs below are the layers actually present in the trial GDS today, not final Sky130 DRC-clean layer/datatype output.",
        "",
        "## Observed GDS Layers",
        "",
        "| GDS layer | datatype | element type | datatype record | current interpretation | Sky130 export target | status |",
        "| ---: | ---: | --- | --- | --- | --- | --- |",
    ]

    for use in sorted_uses:
        entries = export_by_internal.get(use.layer, [])
        current = "MAGICAL internal/mock layer"
        lines.append(
            f"| {use.layer} | {use.datatype} | {use.element_type} | {use.datatype_record} | "
            f"{current} | {format_mapping(entries)} | {status_for(entries)} |"
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- `sky130_gds_export_map.yaml` is a target map for future GDS remapping or post-processing.",
            "- A `confirmed_target` row means the MAGICAL internal layer has a proposed Sky130 layer/datatype target.",
            "- A `tbd` row means the layer appears in the trial GDS but the Sky130 target is not yet confirmed.",
            "- This report does not claim the trial GDS is Sky130 DRC-clean.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect GDS layer/datatype pairs.")
    parser.add_argument("--gds", type=Path, default=DEFAULT_GDS, help="Input GDS file.")
    parser.add_argument("--export-map", type=Path, default=DEFAULT_EXPORT_MAP, help="Sky130 export map YAML.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT, help="Markdown report output.")
    parser.add_argument("--no-report", action="store_true", help="Only print the layer list.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    gds_path = args.gds.resolve()
    export_map_path = args.export_map.resolve()
    report_path = args.report.resolve()

    try:
        if not gds_path.is_file():
            raise FileNotFoundError(gds_path)
        uses = inspect_gds(gds_path)
        export_by_internal = load_export_map(export_map_path)

        print(f"GDS: {gds_path}")
        print("Observed layer/datatype pairs:")
        for use in sorted(uses, key=lambda item: (item.layer, item.datatype, item.element_type)):
            mapping = format_mapping(export_by_internal.get(use.layer, []))
            print(
                f"  {use.layer}/{use.datatype} "
                f"({use.element_type}, {use.datatype_record}) - {mapping}"
            )

        if not args.no_report:
            report = generate_report(gds_path, export_map_path, uses, export_by_internal)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(report, encoding="utf-8")
            print(f"\nReport written: {report_path}")
        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
