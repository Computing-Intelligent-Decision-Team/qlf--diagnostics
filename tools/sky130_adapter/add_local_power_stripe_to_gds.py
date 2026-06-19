#!/usr/bin/env python3
"""Inject a post-route local power stripe into a Sky130 GDS."""

from __future__ import annotations

import argparse
import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from strip_passive_geometry_from_gds import Element, iter_gds_units


@dataclass(frozen=True)
class StripeSegment:
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def center(self) -> tuple[int, int]:
        return (int(round((self.x1 + self.x2) / 2.0)), int(round((self.y1 + self.y2) / 2.0)))

    def as_list(self) -> list[int]:
        return [self.x1, self.y1, self.x2, self.y2]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add post-route local power stripe geometry and labels to GDS.")
    parser.add_argument("--input-gds", type=Path, required=True)
    parser.add_argument("--output-gds", type=Path, required=True)
    parser.add_argument("--cell", required=True)
    parser.add_argument("--net", default="vdda")
    parser.add_argument("--box", required=True, help="Stripe box as x1,y1,x2,y2 in GDS DBU.")
    parser.add_argument("--exclude-x", default="", help="Comma-separated x1:x2 intervals to remove.")
    parser.add_argument("--auto-exclude-same-layer-crossings", action="store_true")
    parser.add_argument("--auto-exclude-margin-dbu", type=int, default=100)
    parser.add_argument("--min-segment-width-dbu", type=int, default=100)
    parser.add_argument("--drawing-layer", type=int, default=72)
    parser.add_argument("--drawing-datatype", type=int, default=20)
    parser.add_argument("--pin-layer", type=int, default=72)
    parser.add_argument("--pin-datatype", type=int, default=16)
    parser.add_argument("--label-layer", type=int, default=72)
    parser.add_argument("--label-texttype", type=int, default=5)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    return parser.parse_args()


def gds_record(record_type: int, data_type: int, payload: bytes = b"") -> bytes:
    length = 4 + len(payload)
    if length % 2:
        raise ValueError(f"GDS record length must be even, got {length}")
    return struct.pack(">HBB", length, record_type, data_type) + payload


def int2_record(record_type: int, value: int) -> bytes:
    return gds_record(record_type, 0x02, struct.pack(">h", value))


def xy_record(points: list[tuple[int, int]]) -> bytes:
    flat: list[int] = []
    for x, y in points:
        flat.extend([x, y])
    return gds_record(0x10, 0x03, struct.pack(f">{len(flat)}l", *flat))


def string_record(value: str) -> bytes:
    payload = value.encode("ascii")
    if len(payload) % 2:
        payload += b"\0"
    return gds_record(0x19, 0x06, payload)


def boundary_element(layer: int, datatype: int, segment: StripeSegment) -> bytes:
    points = [
        (segment.x1, segment.y1),
        (segment.x1, segment.y2),
        (segment.x2, segment.y2),
        (segment.x2, segment.y1),
        (segment.x1, segment.y1),
    ]
    return b"".join(
        [
            gds_record(0x08, 0x00),
            int2_record(0x0D, layer),
            int2_record(0x0E, datatype),
            xy_record(points),
            gds_record(0x11, 0x00),
        ]
    )


def text_element(layer: int, texttype: int, x: int, y: int, label: str) -> bytes:
    return b"".join(
        [
            gds_record(0x0C, 0x00),
            int2_record(0x0D, layer),
            int2_record(0x16, texttype),
            xy_record([(x, y)]),
            string_record(label),
            gds_record(0x11, 0x00),
        ]
    )


def parse_box(value: str) -> tuple[int, int, int, int]:
    parts = [part.strip() for part in value.replace(":", ",").split(",") if part.strip()]
    if len(parts) != 4:
        raise ValueError("--box must contain four integers: x1,y1,x2,y2")
    x1, y1, x2, y2 = [int(part) for part in parts]
    xlo, xhi = sorted((x1, x2))
    ylo, yhi = sorted((y1, y2))
    return xlo, ylo, xhi, yhi


def parse_intervals(value: str) -> list[tuple[int, int]]:
    intervals: list[tuple[int, int]] = []
    for token in value.replace(";", ",").split(","):
        token = token.strip()
        if not token:
            continue
        parts = token.split(":", 1) if ":" in token else token.split()
        if len(parts) != 2:
            raise ValueError(f"invalid exclude interval: {token}")
        left, right = sorted((int(parts[0]), int(parts[1])))
        intervals.append((left, right))
    return intervals


def read_string(payload: bytes) -> str:
    return payload.rstrip(b"\0").decode("ascii", errors="replace")


def find_cell_endstr_offset(data: bytes, cell_name: str) -> int:
    offset = 0
    current_cell = ""
    in_target = False
    fallback: int | None = None
    while offset + 4 <= len(data):
        record_len, record_type, _data_type = struct.unpack(">HBB", data[offset : offset + 4])
        if record_len < 4 or offset + record_len > len(data):
            break
        payload = data[offset + 4 : offset + record_len]
        if record_type == 0x06:
            current_cell = read_string(payload)
            in_target = current_cell == cell_name
        elif record_type == 0x07:
            fallback = offset
            if in_target:
                return offset
            current_cell = ""
            in_target = False
        offset += record_len
    if fallback is not None:
        return fallback
    raise ValueError("No ENDSTR record found in input GDS")


def overlaps(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return not (ax2 <= bx1 or bx2 <= ax1 or ay2 <= by1 or by2 <= ay1)


def auto_exclude_intervals(
    *,
    input_gds: Path,
    stripe_box: tuple[int, int, int, int],
    layer: int,
    datatype: int,
    margin: int,
) -> list[dict[str, Any]]:
    intervals: list[dict[str, Any]] = []
    for unit in iter_gds_units(input_gds.read_bytes()):
        if not isinstance(unit, Element):
            continue
        bbox = unit.bbox
        if bbox is None:
            continue
        if unit.element_type != "BOUNDARY" or unit.layer != layer or unit.purpose_datatype != datatype:
            continue
        candidate = (bbox.x1, bbox.y1, bbox.x2, bbox.y2)
        if not overlaps(stripe_box, candidate):
            continue
        intervals.append(
            {
                "interval": [bbox.x1 - margin, bbox.x2 + margin],
                "source_bbox": bbox.as_list(),
                "layer_key": unit.layer_key,
            }
        )
    return intervals


def split_segments(
    *,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    intervals: list[tuple[int, int]],
    min_width: int,
) -> list[StripeSegment]:
    clipped: list[tuple[int, int]] = []
    for left, right in sorted(intervals):
        left = max(left, x1)
        right = min(right, x2)
        if right <= left:
            continue
        if clipped and left <= clipped[-1][1]:
            clipped[-1] = (clipped[-1][0], max(clipped[-1][1], right))
        else:
            clipped.append((left, right))
    segments: list[StripeSegment] = []
    cursor = x1
    for left, right in clipped:
        if left - cursor >= min_width:
            segments.append(StripeSegment(cursor, y1, left, y2))
        cursor = max(cursor, right)
    if x2 - cursor >= min_width:
        segments.append(StripeSegment(cursor, y1, x2, y2))
    return segments


def write_gds(*, input_gds: Path, output_gds: Path, cell: str, net: str, segments: list[StripeSegment], args: argparse.Namespace) -> None:
    data = input_gds.read_bytes()
    insert_offset = find_cell_endstr_offset(data, cell)
    inserted: list[bytes] = []
    for segment in segments:
        inserted.append(boundary_element(args.drawing_layer, args.drawing_datatype, segment))
        inserted.append(boundary_element(args.pin_layer, args.pin_datatype, segment))
        cx, cy = segment.center
        inserted.append(text_element(args.label_layer, args.label_texttype, cx, cy, net))
    output_gds.parent.mkdir(parents=True, exist_ok=True)
    output_gds.write_bytes(data[:insert_offset] + b"".join(inserted) + data[insert_offset:])


def render_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Local Power Stripe Injection",
        "",
        f"- Input GDS: `{summary['input_gds']}`",
        f"- Output GDS: `{summary['output_gds']}`",
        f"- Cell: `{summary['cell']}`",
        f"- Net: `{summary['net']}`",
        f"- Requested box: `{summary['requested_box']}`",
        f"- Segments inserted: {len(summary['segments'])}",
        "",
        "## Segments",
        "",
        "| Index | Box |",
        "| --- | --- |",
    ]
    for index, segment in enumerate(summary["segments"]):
        lines.append(f"| {index} | `{segment}` |")
    lines.extend(
        [
            "",
            "## Exclusions",
            "",
            f"- Manual intervals: `{summary['manual_exclude_intervals']}`",
            f"- Auto same-layer crossings: {len(summary['auto_exclude_intervals'])}",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    input_gds = args.input_gds.resolve()
    output_gds = args.output_gds.resolve()
    stripe_box = parse_box(args.box)
    manual = parse_intervals(args.exclude_x)
    auto: list[dict[str, Any]] = []
    if args.auto_exclude_same_layer_crossings:
        auto = auto_exclude_intervals(
            input_gds=input_gds,
            stripe_box=stripe_box,
            layer=args.drawing_layer,
            datatype=args.drawing_datatype,
            margin=max(0, args.auto_exclude_margin_dbu),
        )
    intervals = manual + [tuple(item["interval"]) for item in auto]
    segments = split_segments(
        x1=stripe_box[0],
        y1=stripe_box[1],
        x2=stripe_box[2],
        y2=stripe_box[3],
        intervals=intervals,
        min_width=max(1, args.min_segment_width_dbu),
    )
    if not segments:
        raise RuntimeError("No local power stripe segments remain after exclusions.")
    write_gds(input_gds=input_gds, output_gds=output_gds, cell=args.cell, net=args.net, segments=segments, args=args)
    summary = {
        "input_gds": str(input_gds),
        "output_gds": str(output_gds),
        "cell": args.cell,
        "net": args.net,
        "requested_box": list(stripe_box),
        "segments": [segment.as_list() for segment in segments],
        "manual_exclude_intervals": [list(interval) for interval in manual],
        "auto_exclude_intervals": auto,
        "drawing_layer": args.drawing_layer,
        "drawing_datatype": args.drawing_datatype,
        "pin_layer": args.pin_layer,
        "pin_datatype": args.pin_datatype,
        "label_layer": args.label_layer,
        "label_texttype": args.label_texttype,
    }
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_report(summary), encoding="utf-8")
    print(f"output_gds={output_gds}")
    print(f"segments={len(segments)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
