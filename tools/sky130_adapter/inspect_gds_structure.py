#!/usr/bin/env python3
"""Inspect GDS structure for Sky130 passive-aware LVS diagnostics."""

from __future__ import annotations

import argparse
import json
import struct
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from prepare_lvs_netlists import SourcePassive, parse_source_passives


ELEMENT_STARTS = {
    0x08: "BOUNDARY",
    0x09: "PATH",
    0x0A: "SREF",
    0x0B: "AREF",
    0x0C: "TEXT",
}


@dataclass
class GdsElement:
    element_type: str
    layer: int | None = None
    datatype: int | None = None
    texttype: int | None = None
    sname: str | None = None
    string: str | None = None
    xy: list[tuple[int, int]] = field(default_factory=list)


@dataclass
class GdsCell:
    name: str
    element_counts: Counter[str] = field(default_factory=Counter)
    layer_counts: Counter[str] = field(default_factory=Counter)
    refs: list[GdsElement] = field(default_factory=list)
    texts: list[GdsElement] = field(default_factory=list)
    bbox: list[int] | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect a GDS file for passive-aware LVS debug evidence.")
    parser.add_argument("--gds", type=Path, required=True, help="Top GDS to inspect.")
    parser.add_argument("--report", type=Path, required=True, help="Markdown report path.")
    parser.add_argument("--summary-json", type=Path, help="Machine-readable JSON summary path.")
    parser.add_argument("--source-netlist", type=Path, help="Source SPICE netlist with passive instances.")
    parser.add_argument("--case-dir", type=Path, help="Case directory containing generated per-instance GDS files.")
    parser.add_argument("--top-cell", default="", help="Top-cell prefix used for generated passive GDS names.")
    parser.add_argument("--max-texts", type=int, default=40, help="Maximum text labels to list in the report.")
    return parser.parse_args()


def _decode_ascii(payload: bytes) -> str:
    return payload.rstrip(b"\0").decode("ascii", errors="replace")


def _decode_int2(payload: bytes) -> int | None:
    if len(payload) < 2:
        return None
    return struct.unpack(">h", payload[:2])[0]


def _decode_xy(payload: bytes) -> list[tuple[int, int]]:
    points: list[tuple[int, int]] = []
    for offset in range(0, len(payload), 8):
        if offset + 8 <= len(payload):
            points.append(struct.unpack(">ii", payload[offset : offset + 8]))
    return points


def parse_gds(path: Path) -> dict[str, GdsCell]:
    data = path.read_bytes()
    offset = 0
    current_cell: GdsCell | None = None
    current_element: GdsElement | None = None
    cells: dict[str, GdsCell] = {}
    while offset + 4 <= len(data):
        record_len, record_type, _data_type = struct.unpack(">HBB", data[offset : offset + 4])
        if record_len < 4 or offset + record_len > len(data):
            break
        payload = data[offset + 4 : offset + record_len]
        offset += record_len

        if record_type == 0x06:
            name = _decode_ascii(payload)
            current_cell = GdsCell(name=name)
            cells[name] = current_cell
            continue
        if record_type == 0x07:
            current_cell = None
            continue
        if record_type in ELEMENT_STARTS:
            current_element = GdsElement(element_type=ELEMENT_STARTS[record_type])
            continue
        if current_element is None:
            continue
        if record_type == 0x0D:
            current_element.layer = _decode_int2(payload)
        elif record_type == 0x0E:
            current_element.datatype = _decode_int2(payload)
        elif record_type == 0x12:
            current_element.sname = _decode_ascii(payload)
        elif record_type == 0x16:
            current_element.texttype = _decode_int2(payload)
        elif record_type == 0x19:
            current_element.string = _decode_ascii(payload)
        elif record_type == 0x10:
            current_element.xy = _decode_xy(payload)
        elif record_type == 0x11:
            if current_cell is not None:
                _add_element(current_cell, current_element)
            current_element = None
    return cells


def _add_element(cell: GdsCell, element: GdsElement) -> None:
    cell.element_counts[element.element_type] += 1
    for x, y in element.xy:
        if cell.bbox is None:
            cell.bbox = [x, y, x, y]
        else:
            cell.bbox[0] = min(cell.bbox[0], x)
            cell.bbox[1] = min(cell.bbox[1], y)
            cell.bbox[2] = max(cell.bbox[2], x)
            cell.bbox[3] = max(cell.bbox[3], y)
    if element.layer is not None:
        datatype = element.texttype if element.element_type == "TEXT" else element.datatype
        cell.layer_counts[f"{element.layer}/{datatype}/{element.element_type}"] += 1
    if element.element_type in {"SREF", "AREF"}:
        cell.refs.append(element)
    if element.element_type == "TEXT":
        cell.texts.append(element)


def source_passives_from_path(path: Path | None) -> list[SourcePassive]:
    if path is None or not path.is_file():
        return []
    return parse_source_passives(path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True))


def raw_token_presence(path: Path, tokens: list[str]) -> dict[str, bool]:
    data = path.read_bytes()
    return {token: data.find(token.encode("ascii", errors="ignore")) >= 0 for token in tokens}


def generated_passive_gds(case_dir: Path | None, top_cell: str, source_passives: list[SourcePassive]) -> dict[str, Path]:
    if case_dir is None or not case_dir.is_dir() or not top_cell:
        return {}
    gds_dir = case_dir / "gds"
    if not gds_dir.is_dir():
        return {}
    found: dict[str, Path] = {}
    for passive in source_passives:
        path = gds_dir / f"{top_cell}_{passive.instance}.gds"
        if path.is_file():
            found[passive.instance] = path
    return found


def summarize_gds(path: Path, cells: dict[str, GdsCell]) -> dict[str, Any]:
    text_count = sum(len(cell.texts) for cell in cells.values())
    ref_count = sum(len(cell.refs) for cell in cells.values())
    layer_count = sum(len(cell.layer_counts) for cell in cells.values())
    return {
        "path": str(path),
        "cell_count": len(cells),
        "text_count": text_count,
        "ref_count": ref_count,
        "unique_layer_records": layer_count,
        "cells": [
            {
                "name": cell.name,
                "bbox": cell.bbox,
                "refs": len(cell.refs),
                "texts": len(cell.texts),
                "text_labels": [
                    {
                        "string": text.string,
                        "layer": text.layer,
                        "texttype": text.texttype,
                        "xy": [list(point) for point in text.xy],
                    }
                    for text in cell.texts
                ],
                "element_counts": dict(sorted(cell.element_counts.items())),
                "layer_counts": dict(sorted(cell.layer_counts.items())),
            }
            for cell in cells.values()
        ],
    }


def build_summary(
    *,
    top_gds: Path,
    source_netlist: Path | None,
    case_dir: Path | None,
    top_cell: str,
) -> dict[str, Any]:
    top_cells = parse_gds(top_gds)
    source_passives = source_passives_from_path(source_netlist)
    passive_names = [passive.instance for passive in source_passives]
    passive_terminals = sorted({terminal for passive in source_passives for terminal in passive.terminals})
    source_name_presence = raw_token_presence(top_gds, passive_names)
    source_terminal_presence = raw_token_presence(top_gds, passive_terminals)
    generated = generated_passive_gds(case_dir, top_cell, source_passives)
    generated_summaries: dict[str, Any] = {}
    for instance, path in sorted(generated.items()):
        generated_summaries[instance] = summarize_gds(path, parse_gds(path))
    top_summary = summarize_gds(top_gds, top_cells)
    return {
        "top_gds": top_summary,
        "source_netlist": str(source_netlist) if source_netlist else None,
        "source_passive_count": len(source_passives),
        "source_passive_instances": [
            {
                "instance": passive.instance,
                "model": passive.model,
                "terminals": list(passive.terminals),
            }
            for passive in source_passives
        ],
        "source_passive_instance_names_present": source_name_presence,
        "source_passive_terminal_names_present": source_terminal_presence,
        "source_passive_instance_names_present_count": sum(1 for present in source_name_presence.values() if present),
        "source_passive_terminal_names_present_count": sum(1 for present in source_terminal_presence.values() if present),
        "generated_passive_gds_present_count": len(generated),
        "generated_passive_gds": generated_summaries,
    }


def _fmt_bool(value: bool) -> str:
    return "yes" if value else "no"


def write_report(path: Path, summary: dict[str, Any], max_texts: int) -> None:
    top = summary["top_gds"]
    lines = [
        "# GDS Structure Diagnostic",
        "",
        "## Summary",
        "",
        f"- Top GDS: `{top['path']}`",
        f"- Top GDS cells: {top['cell_count']}",
        f"- Top GDS SREF/AREF count: {top['ref_count']}",
        f"- Top GDS text labels: {top['text_count']}",
        f"- Source passive devices: {summary['source_passive_count']}",
        f"- Source passive instance names present in top GDS: {summary['source_passive_instance_names_present_count']}",
        f"- Source passive terminal names present in top GDS: {summary['source_passive_terminal_names_present_count']}",
        f"- Generated passive GDS files found: {summary['generated_passive_gds_present_count']}",
        "",
        "## Source Passive Name Presence",
        "",
    ]
    if summary["source_passive_instances"]:
        lines.extend(["| instance | model | terminals | instance name in top GDS | terminals in top GDS |", "| --- | --- | --- | --- | --- |"])
        instance_presence = summary["source_passive_instance_names_present"]
        terminal_presence = summary["source_passive_terminal_names_present"]
        for passive in summary["source_passive_instances"]:
            terminals = passive["terminals"]
            present_terms = [terminal for terminal in terminals if terminal_presence.get(terminal)]
            lines.append(
                f"| `{passive['instance']}` | `{passive['model']}` | `{' '.join(terminals)}` | "
                f"{_fmt_bool(instance_presence.get(passive['instance'], False))} | "
                f"`{' '.join(present_terms) if present_terms else 'none'}` |"
            )
    else:
        lines.append("- none")

    lines.extend(["", "## Top GDS Cells", ""])
    if top["cells"]:
        lines.extend(["| cell | refs | texts | element counts |", "| --- | ---: | ---: | --- |"])
        for cell in top["cells"]:
            counts = ", ".join(f"{key}:{value}" for key, value in cell["element_counts"].items())
            lines.append(f"| `{cell['name']}` | {cell['refs']} | {cell['texts']} | `{counts or 'none'}` |")
    else:
        lines.append("- none")

    lines.extend(["", "## Top GDS Text Labels", ""])
    label_rows = _top_text_rows(summary)
    if label_rows:
        lines.extend(["| cell | label | layer/texttype | xy |", "| --- | --- | --- | --- |"])
        for row in label_rows[:max_texts]:
            lines.append(f"| `{row['cell']}` | `{row['label']}` | `{row['layer']}` | `{row['xy']}` |")
        if len(label_rows) > max_texts:
            lines.append(f"| ... | ... | ... | {len(label_rows) - max_texts} more |")
    else:
        lines.append("- none")

    lines.extend(["", "## Generated Passive GDS Files", ""])
    generated = summary["generated_passive_gds"]
    if generated:
        lines.extend(["| instance | path | cells | refs | texts |", "| --- | --- | ---: | ---: | ---: |"])
        for instance, item in generated.items():
            lines.append(
                f"| `{instance}` | `{item['path']}` | {item['cell_count']} | {item['ref_count']} | {item['text_count']} |"
            )
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This diagnostic checks whether the GDS still carries source passive instance or terminal names.",
            "If the top GDS is flattened and the generated passive GDS files have no port text labels, source-instance passive LVS cannot be proven from netlist extraction alone.",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _top_text_rows(summary: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    top_path = Path(summary["top_gds"]["path"])
    for cell in parse_gds(top_path).values():
        for text in cell.texts:
            first_xy = text.xy[0] if text.xy else ("", "")
            rows.append(
                {
                    "cell": cell.name,
                    "label": text.string or "",
                    "layer": f"{text.layer}/{text.texttype}",
                    "xy": f"{first_xy[0]},{first_xy[1]}",
                }
            )
    return rows


def main() -> int:
    args = parse_args()
    top_gds = args.gds.resolve()
    if not top_gds.is_file():
        raise FileNotFoundError(top_gds)
    report = args.report.resolve()
    report.parent.mkdir(parents=True, exist_ok=True)
    summary = build_summary(
        top_gds=top_gds,
        source_netlist=args.source_netlist.resolve() if args.source_netlist else None,
        case_dir=args.case_dir.resolve() if args.case_dir else None,
        top_cell=args.top_cell,
    )
    write_report(report, summary, args.max_texts)
    if args.summary_json:
        summary_json = args.summary_json.resolve()
        summary_json.parent.mkdir(parents=True, exist_ok=True)
        summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"report={report}")
    if args.summary_json:
        print(f"summary_json={args.summary_json.resolve()}")
    print(f"top_gds_text_count={summary['top_gds']['text_count']}")
    print(f"top_gds_ref_count={summary['top_gds']['ref_count']}")
    print(f"source_passive_instance_names_present={summary['source_passive_instance_names_present_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
